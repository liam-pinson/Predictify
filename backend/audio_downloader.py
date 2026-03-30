import os
import uuid
import shutil
import subprocess
from spotdl import Spotdl
from spotdl.types.song import Song, SongError
from spotdl.utils.spotify import SpotifyClient
from dotenv import load_dotenv
from pathlib import Path

from config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET

load_dotenv()


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
    artist_genres = raw_artist_meta.get("genres") or [] if raw_artist_meta else []

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
def download_single_track(track_id: str) -> str:
    """Downloads one track for inference. Returns path to raw audio file."""
    Song.from_url = patched_from_url

    unique_id = uuid.uuid4().hex
    temp_dir = f"./temp_inference_{unique_id}"
    os.makedirs(temp_dir, exist_ok=True)

    url = f"https://open.spotify.com/track/{track_id}"

    spotdl_client = Spotdl(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        downloader_settings={
            "output": f"{temp_dir}/{{artist}} - {{title}}.{{output-ext}}"
        }
    )

    songs = spotdl_client.search([url])
    if not songs:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise Exception(f"spotdl could not find track: {track_id}")

    results = spotdl_client.download_songs(songs)

    for song, path in results:
        if path and os.path.exists(path):
            return str(path)

    shutil.rmtree(temp_dir, ignore_errors=True)
    raise Exception(f"Download failed for track: {track_id}")


# ── Process a single raw audio file for inference ──────────────────────────────
def process_single_audio(raw_path: str) -> str:
    """Converts raw audio to a normalized 30s mono WAV. Cleans up raw file after."""
    raw_path = Path(raw_path)
    unique_id = uuid.uuid4().hex
    processed_path = Path(f"./temp_processed_{unique_id}.wav")

    cmd = [
        "ffmpeg", "-y",
        "-ss", "15",
        "-i", str(raw_path),
        "-t", "30",
        "-ac", "1",
        "-ar", "22050",
        str(processed_path)
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        raise Exception(f"FFmpeg processing failed for: {raw_path.name}")
    finally:
        # Always clean up raw file and its temp folder
        raw_dir = raw_path.parent
        if raw_path.exists():
            os.remove(raw_path)
        if raw_dir.exists() and not any(raw_dir.iterdir()):
            shutil.rmtree(raw_dir, ignore_errors=True)

    if not processed_path.exists():
        raise Exception("Processed audio file was not created.")

    return str(processed_path)


# ── Batch download for training data ───────────────────────────────────────────
def process_all_downloads(all_data):
    Song.from_url = patched_from_url

    temp_dir = "./temp_downloads"
    os.makedirs(temp_dir, exist_ok=True)

    spotdl = Spotdl(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        downloader_settings={
            "output": f"{temp_dir}/{{artist}} - {{title}}.{{output-ext}}"
        }
    )

    print(f"🚀 Starting batch download of {len(all_data)} tracks...")

    for item in all_data:
        category, track_id, artists, name = item
        url = f"https://open.spotify.com/track/{track_id}"

        final_dir = f"../data/raw/audio/{category}"
        os.makedirs(final_dir, exist_ok=True)

        try:
            print(f"  🔍 Processing: {name} ({category})")
            songs = spotdl.search([url])

            if songs:
                results = spotdl.download_songs(songs)
                for song, temp_path in results:
                    if temp_path and os.path.exists(temp_path):
                        file_name = os.path.basename(temp_path)
                        dest_path = os.path.join(final_dir, file_name)
                        shutil.move(str(temp_path), dest_path)
                        print(f"    ✅ Moved: {file_name} → {category}")
                    else:
                        print(f"    ❌ Download failed for: {song.display_name}")
            else:
                print(f"    ❌ No results for {name}")

        except Exception as e:
            print(f"    💥 Error downloading {name}: {e}")

    if os.path.exists(temp_dir) and not os.listdir(temp_dir):
        os.rmdir(temp_dir)

    print("\n✨ All downloads and sorting complete!")


# ── Batch audio processing for training data ───────────────────────────────────
RAW_DIR = Path("../data/raw/audio")
PROCESSED_DIR = Path("../data/processed/audio")

def process_audio_dataset():
    extensions = {".mp3", ".wav", ".m4a", ".flac", ".ogg"}

    print(f"🚀 Starting audio processing (Offset: 15s, Duration: 30s)...")

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
            print(f"  ✅ Processed: [{category}] {input_file.name}")
        except subprocess.CalledProcessError:
            print(f"  ❌ Failed: [{category}] {input_file.name}")

    print(f"\n✨ Done! Files saved to: {PROCESSED_DIR}")