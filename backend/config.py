# backend/config.py
import os
from dotenv import load_dotenv
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

SPOTIFY_CLIENT_ID     = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI  = os.getenv("SPOTIFY_REDIRECT_URI")
SPOTIFY_USERNAME      = os.getenv("SPOTIFY_USERNAME")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


PROCESSED_DIR = BASE_DIR / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

RAW_DIR = BASE_DIR / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

AUDIO_DIR = BASE_DIR/ "data" / "raw" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)