import os
import sys
import uuid
import shutil
import subprocess
import threading
import time

from spotdl import Spotdl
from spotdl.types.song import Song, SongError
from spotdl.utils.spotify import SpotifyClient
from dotenv import load_dotenv
from pathlib import Path
from utils.ffmpeg_utils import setup_ffmpeg, verify_ffmpeg

from config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET

load_dotenv()

# Shared global spotdl client + lock
_spotdl_client = None
_spotdl_lock = threading.Lock()

# ============================================
# FFmpeg Setup (ADD THIS FIRST)
# ============================================

def setup_ffmpeg():
    """
    Setup FFmpeg for both local (Windows) and containerized (Linux) environments.
    Returns True if FFmpeg is available, False otherwise.
    """
    # Check if FFmpeg is already in PATH
    if shutil.which("ffmpeg"):
        print("✅ FFmpeg found in PATH")
        return True

    # Windows-specific setup
    if sys.platform == "win32":
        print("🔍 Searching for FFmpeg on Windows...")

        # Common Windows FFmpeg locations
        ffmpeg_paths = [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages"),
            r"C:\ffmpeg\bin",
            r"C:\Program Files\ffmpeg\bin",
            r"C:\Program Files (x86)\ffmpeg\bin",
        ]

        for base_path in ffmpeg_paths:
            if not os.path.exists(base_path):
                continue

            # Search for ffmpeg.exe
            if "WinGet" in base_path:
                for root, dirs, files in os.walk(base_path):
                    if "ffmpeg.exe" in files:
                        os.environ["PATH"] += os.pathsep + root
                        print(f"✅ Found FFmpeg at: {root}")
                        return True
            else:
                ffmpeg_exe = os.path.join(base_path, "ffmpeg.exe")
                if os.path.exists(ffmpeg_exe):
                    os.environ["PATH"] += os.pathsep + base_path
                    print(f"✅ Found FFmpeg at: {base_path}")
                    return True

        print("⚠️ FFmpeg not found on Windows. Install with: winget install ffmpeg")
        return False

    # Linux/Docker - should be installed via apt-get
    print("⚠️ FFmpeg not found in container. Add to Dockerfile: RUN apt-get install -y ffmpeg")
    return False

# ✅ Setup FFmpeg when module is imported
print("🔧 Setting up FFmpeg...")
_ffmpeg_available = setup_ffmpeg()


def get_spotdl_client():
    global _spotdl_client
    with _spotdl_lock:
        if _spotdl_client is None:
            _spotdl_client = Spotdl(
                client_id=SPOTIFY_CLIENT_ID,
                client_secret=SPOTIFY_CLIENT_SECRET,
                downloader_settings={}
            )
        return _spotdl_client


# ── Spotify API patch (fixes missing genres/label from Feb 2026 changes) ───────
@classmethod
def patched_from_url(cls, url: str) -> "Song":
    if "open.spotify.com" not in url or "track" not in url:
        raise SongError(f"Invalid URL: {url}")

    spotify_client = SpotifyClient()
    raw_track_meta = spotify_client.track(url)

    if raw_track_meta is None:
        raise SongError("Couldn't get metadata, check if you have passed correct track id")

    duration_ms = raw_track_meta.get("duration_ms", 0)
    name = raw_track_meta.get("name", "Unknown Track")

    if duration_ms == 0 or name.strip() == "":
        raise SongError(f"Track no longer exists or is restricted: {url}")

    artists = raw_track_meta.get("artists", [])
    primary_artist_id = artists[0].get("id") if artists else None
    raw_artist_meta = spotify_client.artist(primary_artist_id) if primary_artist_id else {}

    album = raw_track_meta.get("album", {})
    album_id = album.get("id")
    raw_album_meta = spotify_client.album(album_id) if album_id else {}

    album_name = raw_album_meta.get("name", "Unknown Album")
    album_artists = raw_album_meta.get("artists", [])
    album_artist = album_artists[0].get("name", "Unknown Artist") if album_artists else "Unknown Artist"

    copyrights = raw_album_meta.get("copyrights", [])
    copyright_text = copyrights[0].get("text") if copyrights else None

    album_genres = raw_album_meta.get("genres") or []
    artist_genres = (raw_artist_meta.get("genres") or []) if raw_artist_meta else []

    publisher = raw_album_meta.get("label") or raw_album_meta.get("publisher") or "Unknown Publisher"
    release_date = raw_album_meta.get("release_date", "1970-01-01")

    album_tracks = raw_album_meta.get("tracks", {}).get("items", [])
    disc_count = int(album_tracks[-1].get("disc_number", 1)) if album_tracks else 1

    return cls(
        name=name,
        artists=[a.get("name") for a in artists],
        artist=artists[0].get("name") if artists else "Unknown Artist",
        artist_id=primary_artist_id,
        album_id=album_id,
        album_name=album_name,
        album_artist=album_artist,
        album_type=raw_album_meta.get("album_type"),
        copyright_text=copyright_text,
        genres=album_genres + artist_genres,
        disc_number=raw_track_meta.get("disc_number", 1),
        disc_count=disc_count,
        duration=int(duration_ms / 1000),
        year=int(release_date[:4]),
        date=release_date,
        track_number=raw_track_meta.get("track_number", 1),
        tracks_count=raw_album_meta.get("total_tracks", 1),
        isrc=raw_track_meta.get("external_ids", {}).get("isrc"),
        song_id=raw_track_meta.get("id"),
        explicit=raw_track_meta.get("explicit", False),
        publisher=publisher,
        url=raw_track_meta.get("external_urls", {}).get("spotify", url),
        popularity=raw_track_meta.get("popularity", 0),
        cover_url=(
            max(raw_album_meta.get("images", []), key=lambda i: i.get("width", 0) * i.get("height", 0)).get("url")
            if raw_album_meta.get("images") else None
        ),
    )


# ── Single track download for inference ────────────────────────────────────────
def wait_for_file_ready(file_path: Path, timeout: int = 10) -> bool:
    """
    Wait for a file to be fully written.
    Returns True if file is ready, False if timeout.
    """
    if not file_path.exists():
        return False

    start_time = time.time()
    last_size = -1
    stable_count = 0

    while time.time() - start_time < timeout:
        try:
            current_size = file_path.stat().st_size

            if current_size == last_size:
                stable_count += 1
                if stable_count >= 3:  # Size stable for 3 checks
                    return True
            else:
                stable_count = 0
                last_size = current_size

            time.sleep(0.5)
        except (IOError, OSError):
            time.sleep(0.5)

    return file_path.exists()

def download_single_track(track_id: str) -> str:
    """Downloads one track for inference. Returns path to raw audio file."""
    Song.from_url = patched_from_url

    client = get_spotdl_client()

    unique_id = uuid.uuid4().hex
    temp_dir = f"./temp_inference_{unique_id}"
    os.makedirs(temp_dir, exist_ok=True)

    url = f"https://open.spotify.com/track/{track_id}"

    try:
        with _spotdl_lock:
            client.downloader.settings["output"] = f"{temp_dir}/{{artist}} - {{title}}.{{output-ext}}"

            print("pre download")
            print(track_id)
            songs = client.search([url])
            if not songs:
                raise Exception(f"spotdl could not find track: {track_id}")

            results = client.download_songs(songs)

        print("after download songs")

        # Handle both 2-value and 3-value tuples
        for result in results:
            if len(result) == 3:
                song, path, error = result
            elif len(result) == 2:
                song, path = result
                error = None
            else:
                print(f"Unexpected result format: {result}")
                continue

            if error:
                print(f"Download error: {error}")
                continue

            if path:
                file_path = Path(path).resolve()

                print(f"Waiting for file to be ready: {file_path.name}")

                # ✅ Wait for file to be fully written
                if wait_for_file_ready(file_path, timeout=10):
                    file_size = file_path.stat().st_size
                    print(f"✅ Successfully downloaded: {file_path}")
                    print(f"   File size: {file_size:,} bytes")
                    return str(file_path)
                else:
                    raise Exception(f"File not ready after timeout: {file_path}")

        raise Exception(f"Download failed for track: {track_id}")

    except Exception as e:
        print(f"Error downloading track {track_id}: {str(e)}")
        raise
    


# ── Process a single raw audio file for inference ──────────────────────────────
def process_single_audio(raw_path: str) -> str:
    """Converts raw audio to a normalized 30s mono WAV. Cleans up raw file after."""

    # Check FFmpeg availability
    if not shutil.which("ffmpeg"):
        raise Exception(
            "FFmpeg not available. "
            "Windows: Install with 'winget install ffmpeg'. "
            "Docker: Add 'RUN apt-get install -y ffmpeg' to Dockerfile."
        )

    raw_path = Path(raw_path)

    # ✅ Verify file exists before processing
    if not raw_path.exists():
        raise Exception(f"Input file not found: {raw_path}")

    # ✅ Use absolute path to avoid path issues
    raw_path_abs = raw_path.resolve()

    unique_id = uuid.uuid4().hex
    processed_path = Path(f"./temp_processed_{unique_id}.wav").resolve()

    cmd = [
        "ffmpeg", "-y",
        "-ss", "15",
        "-i", str(raw_path_abs),  # ✅ Use absolute path
        "-t", "30",
        "-ac", "1",
        "-ar", "22050",
        str(processed_path)        # ✅ Use absolute path
    ]

    try:
        print(f"🎵 Processing audio: {raw_path.name}")
        print(f"   Input: {raw_path_abs}")
        print(f"   Output: {processed_path}")

        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=30
        )

        print(f"✅ Audio processed: {processed_path.name}")

    except subprocess.TimeoutExpired:
        raise Exception(f"FFmpeg processing timed out for: {raw_path.name}")
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else str(e)
        print(f"❌ FFmpeg error: {error_msg}")
        raise Exception(f"FFmpeg processing failed for: {raw_path.name}\nError: {error_msg}")
    except FileNotFoundError:
        raise Exception("FFmpeg executable not found.")
    finally:
        # Clean up raw file and directory
        raw_dir = raw_path.parent
        if raw_path.exists():
            os.remove(raw_path)
            print(f"🧹 Cleaned up: {raw_path.name}")
        if raw_dir.exists() and not any(raw_dir.iterdir()):
            shutil.rmtree(raw_dir, ignore_errors=True)

    if not processed_path.exists():
        raise Exception("Processed audio file was not created.")

    return str(processed_path)


# ── Batch download for training data ───────────────────────────────────────────
def process_all_downloads(all_data):
    Song.from_url = patched_from_url
    client = get_spotdl_client()

    temp_dir = "./temp_downloads"
    os.makedirs(temp_dir, exist_ok=True)

    print(f"Starting batch download of {len(all_data)} tracks...")

    for item in all_data:
        category, track_id, artists, name = item
        url = f"https://open.spotify.com/track/{track_id}"

        final_dir = f"../data/raw/audio/{category}"
        os.makedirs(final_dir, exist_ok=True)

        try:
            print(f"Processing: {name} ({category})")

            with _spotdl_lock:
                client.downloader.settings["output"] = f"{temp_dir}/{{artist}} - {{title}}.{{output-ext}}"
                songs = client.search([url])

                if songs:
                    results = client.download_songs(songs)
                else:
                    results = []

            if songs:
                for song, temp_path in results:
                    if temp_path and os.path.exists(temp_path):
                        file_name = os.path.basename(temp_path)
                        dest_path = os.path.join(final_dir, file_name)
                        shutil.move(str(temp_path), dest_path)
                        print(f"Moved: {file_name} → {category}")
                    else:
                        print(f"Download failed for: {song.display_name}")
            else:
                print(f"No results for {name}")

        except Exception as e:
            print(f"Error downloading {name}: {e}")

    if os.path.exists(temp_dir) and not os.listdir(temp_dir):
        os.rmdir(temp_dir)

    print("\nAll downloads and sorting complete!")


# ── Batch audio processing for training data ───────────────────────────────────
RAW_DIR = Path("../data/raw/audio")
PROCESSED_DIR = Path("../data/processed/audio")

def process_audio_dataset():
    extensions = {".mp3", ".wav", ".m4a", ".flac", ".ogg"}

    print(f"Starting audio processing (Offset: 15s, Duration: 30s)...")

    for input_file in RAW_DIR.rglob("*"):
        if input_file.suffix.lower() not in extensions:
            continue

        category = input_file.parent.name
        output_dir = PROCESSED_DIR / category
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / input_file.with_suffix(".wav").name

        cmd = [
            "ffmpeg", "-y",
            "-ss", "15",
            "-i", str(input_file),
            "-t", "30",
            "-ac", "1",
            "-ar", "22050",
            str(output_file)
        ]

        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"Processed: [{category}] {input_file.name}")
        except subprocess.CalledProcessError:
            print(f"Failed: [{category}] {input_file.name}")

    print(f"\nDone! Files saved to: {PROCESSED_DIR}")