import os
import sys
import subprocess
import shutil

def setup_ffmpeg():
    """
    Setup FFmpeg for both local (Windows) and containerized (Linux) environments.
    Returns True if FFmpeg is available, False otherwise.
    """
    # Check if FFmpeg is already in PATH
    if shutil.which("ffmpeg"):
        print("FFmpeg found in PATH")
        return True

    # Windows-specific setup
    if sys.platform == "win32":
        print("Searching for FFmpeg on Windows...")

        # Common Windows FFmpeg locations
        ffmpeg_paths = [
            # WinGet installation
            os.path.join(
                os.environ.get("LOCALAPPDATA", ""),
                "Microsoft", "WinGet", "Packages"
            ),
            # Manual installations
            r"C:\ffmpeg\bin",
            r"C:\Program Files\ffmpeg\bin",
            r"C:\Program Files (x86)\ffmpeg\bin",
        ]

        # Search for ffmpeg.exe
        for base_path in ffmpeg_paths:
            if not os.path.exists(base_path):
                continue

            # If it's the WinGet packages folder, search recursively
            if "WinGet" in base_path:
                for root, dirs, files in os.walk(base_path):
                    if "ffmpeg.exe" in files:
                        ffmpeg_dir = root
                        os.environ["PATH"] += os.pathsep + ffmpeg_dir
                        os.environ["FFMPEG_BINARY"] = os.path.join(ffmpeg_dir, "ffmpeg.exe")
                        os.environ["FFPROBE_BINARY"] = os.path.join(ffmpeg_dir, "ffprobe.exe")
                        print(f"Found FFmpeg at: {ffmpeg_dir}")
                        return True
            else:
                # Direct path
                ffmpeg_exe = os.path.join(base_path, "ffmpeg.exe")
                if os.path.exists(ffmpeg_exe):
                    os.environ["PATH"] += os.pathsep + base_path
                    os.environ["FFMPEG_BINARY"] = ffmpeg_exe
                    os.environ["FFPROBE_BINARY"] = os.path.join(base_path, "ffprobe.exe")
                    print(f"Found FFmpeg at: {base_path}")
                    return True

        print("FFmpeg not found on Windows")
        print("Please install FFmpeg: winget install ffmpeg")
        return False

    # Linux/Docker - FFmpeg should be installed via apt-get in Dockerfile
    else:
        print("FFmpeg not found in Docker container")
        print("Make sure FFmpeg is installed in Dockerfile: RUN apt-get install -y ffmpeg")
        return False

def verify_ffmpeg():
    """Verify FFmpeg is working"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        version = result.stdout.split('\n')[0]
        print(f"FFmpeg verified: {version}")
        return True
    except Exception as e:
        print(f"FFmpeg verification failed: {e}")
        return False