# obtain spotify playlist tracks
import os
import requests
import spotipy
import pandas as pd
import sys
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from traceback import print_exception

from config import PROCESSED_DIR, RAW_DIR
from audio_downloader import process_all_downloads, process_audio_dataset

# set_environment_variables()
load_dotenv()

scope = "playlist-read-collaborative user-top-read playlist-modify-public playlist-modify-private playlist-read-private"

# sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

# user = sp.current_user()
# print(f"Authenticated as: {user['display_name']}")

# # Fetch top tracks from last 4 weeks
# print("\nFetching your top tracks...")
# top_tracks = sp.current_user_top_tracks(limit=5, time_range='short_term')

# for track in top_tracks:
#     print(track)

# print("Getting playlist...")
# print(sp.playlist("0EN2gQhhn0rCYUR5BY1UJy"))

# print("search tracks")
# collect()

SEARCH_QUERIES = {
    "hits": [
        "top hits 2025",
        "top 40 2025",
        "pop hits 2025",
        "viral hits 2025",
        "top hits 2024",
        "top 40 2024",
    ],
    "niche": [
        "lo-fi indie 2025",
        "underground rap 2025",
        "ambient electronic 2025",
        "bedroom pop 2025",
        "lo-fi indie 2024",
        "underground rap 2024",
    ]
}

def search_tracks(sp, query: str, limit: int = 10):
    results = sp.search(q=query, type="track", limit=limit)
    return results["tracks"]["items"]

def collect():

    auth_manager=SpotifyOAuth(scope=scope)
    
    sp = spotipy.Spotify(auth_manager=auth_manager)

    # Get the current access token
    # token_info = auth_manager.get_access_token(as_dict=False)

    all_data = []
    seen = set()

    for label, queries in SEARCH_QUERIES.items():
        print(f"\nCollecting '{label}' tracks...")
        track_ids = []
        track_meta = {}

        for query in queries:
            print(f"  Searching: {query}")
            try:
                tracks = search_tracks(sp, query)
                for t in tracks:
                    if t and t.get("id") and t["id"] not in seen:
                        seen.add(t["id"])
                        artists = []

                        for artist in t["artists"]:
                            artists.append(artist["name"])
                        artist_names = ','.join(str(x) for x in artists)
                        
                        track_ids.append([label, t["id"], artist_names, t["name"]])

                        # download_song(songID=t["id"],category=label)

                        track_meta[t["id"]] = t
            except Exception as e:
                print(f"  Error on query '{query}': {e}")
                continue

        for track in track_ids:
            all_data.append(track)

    df = pd.DataFrame(all_data)
    out = RAW_DIR / "tracks.csv"
    df.to_csv(out, index=False)

    return all_data

def search_single_track():

    auth_manager=SpotifyOAuth(scope=scope)
    
    sp = spotipy.Spotify(auth_manager=auth_manager)

    query = "Dramamine"

    results = sp.search(q=query, type="track", limit=10)

    return results["tracks"]["items"]

if __name__ == "__main__":
    
#     tracks = collect()

#     if tracks:
#         process_all_downloads(tracks)

#         process_audio_dataset()

    print(search_single_track())