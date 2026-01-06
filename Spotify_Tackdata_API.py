from dotenv import load_dotenv
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
import pandas as pd


# Load environment variables

load_dotenv()
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")

print("REDIRECT_URI:", repr(REDIRECT_URI))

# Spotify auth

SCOPE = "playlist-read-private playlist-read-collaborative"

sp_user = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE
    )
)

sp_public = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
)

print("Authentication successful")

#  get genres for artists

def get_artist_genres(artist_ids):
    if not artist_ids:
        return "Unknown"

    genres = set()
    try:
        # Spotify API allows up to 50 artists per call
        for i in range(0, len(artist_ids), 50):
            batch = artist_ids[i:i + 50]
            artists = sp_public.artists(batch)["artists"]
            for artist in artists:
                genres.update(artist.get("genres", []))
    except Exception as e:
        print(f"Error fetching genres for {artist_ids}: {e}")

    return ", ".join(sorted(genres)) if genres else "Unknown"


#  get playlist tracks

def get_playlist_tracks(playlist_id, is_public=False):
    sp = sp_public if is_public else sp_user
    all_tracks = []

    results = sp.playlist_items(
        playlist_id,
        fields="items(track(id,name,artists(id,name),album(id,name,release_date),external_urls,uri)),next",
        additional_types=["track"],
        market="from_token" if not is_public else None
    )

    while results:
        for item in results["items"]:
            track = item.get("track")
            if not track:
                continue

            artist_ids = [a["id"] for a in track["artists"] if a.get("id")]

            track_info = {
                "track_id": track.get("id"),
                "track_name": track.get("name"),
                "artist_ids": ", ".join(artist_ids),
                "artist_names": ", ".join(a["name"] for a in track["artists"]),
                "album_id": track["album"]["id"],
                "album_name": track["album"]["name"],
                "release_date": track["album"]["release_date"],
                "spotify_url": track["external_urls"]["spotify"],
                "track_uri": track["uri"],
                "genres": get_artist_genres(artist_ids),
                "playlist_id": playlist_id
            }

            all_tracks.append(track_info)

        if results["next"]:
            results = sp.next(results)
        else:
            break

    return all_tracks

#main function 

def main():
    playlist_ids = {
        "Popular African Songs": {
            "id": "3fgsVcazA1P9NBvYkIlhv6",
            "is_public": True
        }
    }

    all_data = []

    for name, info in playlist_ids.items():
        print(f"\nFetching playlist: {name}")

        tracks = get_playlist_tracks(
            info["id"],
            is_public=info["is_public"]
        )

        for track in tracks:
            track["playlist_name"] = name

        all_data.extend(tracks)
        print(f"Found {len(tracks)} tracks in '{name}'")

    # Export to Excel
    df = pd.DataFrame(all_data)
    df.to_excel("spotify_tracks_data_test1.xlsx", index=False)
    print("Exported to spotify_tracks_data_test1.xlsx")


if __name__ == "__main__":
    main()
