# Create a test file: test_ffmpeg.py
import subprocess
import os

def test_ffmpeg():
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            check=True
        )
        print("✅ FFmpeg is accessible!")
        print(result.stdout[:200])
        return True
    except FileNotFoundError:
        print("❌ FFmpeg not found in PATH")

        # Try to find it
        try:
            result = subprocess.run(
                ["where.exe", "ffmpeg"],
                capture_output=True,
                text=True,
                check=True
            )
            ffmpeg_path = result.stdout.strip().split('\n')[0]
            print(f"Found FFmpeg at: {ffmpeg_path}")
            print(f"Add this to PATH: {os.path.dirname(ffmpeg_path)}")
        except:
            print("Could not locate FFmpeg")

        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_ffmpeg()