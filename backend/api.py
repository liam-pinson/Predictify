# api.py
import os
import time
import base64
import socket
import httpx

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from inference_service import run_spotify_inference

load_dotenv()

# Force IPv4 on Windows; IPv6/TLS routing is often the cause of WinError 10054
_original_getaddrinfo = socket.getaddrinfo
def force_ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = force_ipv4_getaddrinfo

app = FastAPI()

# fix allow origins to allow frontend external IP to access this endpoint
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://34.173.196.151", "*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SPOTIFY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")

if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
    raise RuntimeError("Missing SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET in .env")

class TrackRequest(BaseModel):
    track_id: str

_token_cache = {
    "access_token": None,
    "expires_at": 0,
    "source": None,
}

def make_client():
    return httpx.Client(
        timeout=20.0,
        verify=False,
        http2=False,
        trust_env=False,
        follow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        },
    )

def get_official_token():
    creds = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    encoded = base64.b64encode(creds.encode()).decode()

    with make_client() as client:
        resp = client.post(
            "https://accounts.spotify.com/api/token",
            headers={
                "Authorization": f"Basic {encoded}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials"},
        )
        resp.raise_for_status()
        data = resp.json()

    access_token = data["access_token"]
    expires_in = int(data.get("expires_in", 3600))

    _token_cache["access_token"] = access_token
    _token_cache["expires_at"] = time.time() + expires_in - 60
    _token_cache["source"] = "official"
    return access_token

def get_web_player_token():
    with make_client() as client:
        resp = client.get(
            "https://open.spotify.com/get_access_token",
            params={
                "reason": "transport",
                "productType": "web_player",
            },
            headers={
                "Referer": "https://open.spotify.com/",
                "Origin": "https://open.spotify.com",
                "App-Platform": "WebPlayer",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    access_token = data.get("accessToken") or data.get("access_token")
    expires_ms = data.get("accessTokenExpirationTimestampMs")

    if not access_token:
        raise RuntimeError(f"Could not get web player token: {data}")

    if expires_ms:
        _token_cache["expires_at"] = (int(expires_ms) / 1000) - 60
    else:
        _token_cache["expires_at"] = time.time() + 300

    _token_cache["access_token"] = access_token
    _token_cache["source"] = "web_player"
    return access_token

def get_spotify_token(force_refresh=False):
    if (
        not force_refresh
        and _token_cache["access_token"]
        and time.time() < _token_cache["expires_at"]
    ):
        return _token_cache["access_token"]

    errors = []

    try:
        return get_official_token()
    except Exception as e:
        errors.append(f"official token failed: {e}")

    try:
        return get_web_player_token()
    except Exception as e:
        errors.append(f"web player token failed: {e}")

    raise RuntimeError(" | ".join(errors))

def spotify_get(path: str, params: dict):
    token = get_spotify_token()

    with make_client() as client:
        resp = client.get(
            f"https://api.spotify.com/v1{path}",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
        )

        if resp.status_code == 401:
            token = get_spotify_token(force_refresh=True)
            resp = client.get(
                f"https://api.spotify.com/v1{path}",
                headers={"Authorization": f"Bearer {token}"},
                params=params,
            )

        resp.raise_for_status()
        return resp.json()

@app.get("/search")
def search_track(q: str = Query(..., description="Song name to search")):
    try:
        data = spotify_get(
            "/search",
            {
                "q": q,
                "type": "track",
                "limit": 10,
                "market": "US",
            },
        )
        tracks = data.get("tracks", {}).get("items", [])

        return [
            {
                "id": t.get("id"),
                "title": t.get("name"),
                "artist": ", ".join(a["name"] for a in t.get("artists", [])),
                "album": t.get("album", {}).get("name"),
                "image": (t.get("album", {}).get("images") or [{}])[0].get("url"),
                "preview_url": t.get("preview_url"),
                "popularity": t.get("popularity", 0),
            }
            for t in tracks if t
        ]
    except Exception as e:
        print(f"Search error: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Spotify search failed: {e}"
        )

@app.post("/predict/spotify")
def predict_spotify(req: TrackRequest):
    try:
        return run_spotify_inference(req.track_id)
    except Exception as e:
        print(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))