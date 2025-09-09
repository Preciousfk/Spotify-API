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

# Define scopes for Authorization Code flow
SCOPE = "playlist-read-private playlist-read-collaborative"

# Spotify clients
sp_user = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE
))

sp_public = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET
))

print("Authentication successful 🎉")


# ✅ Function to get genres for artists
def get_artist_genres(artist_ids):
    genres = []
    try:
        artists = sp_public.artists(artist_ids)['artists']
        for artist in artists:
            genres.extend(artist.get('genres', []))
    except Exception as e:
        print(f"Error fetching genres for {artist_ids}: {e}")
    return ', '.join(list(set(genres))) if genres else "Unknown"


# ✅ Function to get playlist tracks
def get_playlist_tracks(playlist_id, is_public=False):
    sp = sp_public if is_public else sp_user

    all_tracks = []
    results = sp.playlist_items(
        f'spotify:playlist:{playlist_id}',
        fields="items(track(id,name,artists(id,name),album(id,name,release_date),external_urls,uri)),next",
        additional_types=['track'],
        market="from_token" if not is_public else None
    )

    while results:
        for item in results['items']:
            track = item['track']
            if track:
                artist_ids = [a.get("id") for a in track["artists"]]
                track_info = {
                    "track_id": track.get("id"),
                    "track_name": track.get("name"),
                    "artist_ids": ', '.join(artist_ids),
                    "artist_names": ', '.join([a.get("name") for a in track["artists"]]),
                    "album_id": track["album"]["id"],
                    "album_name": track["album"]["name"],
                    "release_date": track["album"]["release_date"],
                    "spotify_url": track["external_urls"]["spotify"],
                    "track_uri": track["uri"],
                    "genres": get_artist_genres(artist_ids)  # ✅ Add genres here
                }
                all_tracks.append(track_info)

        if results['next']:
            results = sp.next(results)
        else:
            break

    return all_tracks


# ✅ Main function
def main():
    playlist_ids = {
        "African Hits 2025": {"id": "6Kxt3I9yhhGZkV0Z8jZXfn", "public": False},
        # Add more playlists if needed
    }

    all_data = []

    for name, info in playlist_ids.items():
        print(f"\nFetching playlist: {name}")
        tracks = get_playlist_tracks(info["id"], is_public=info["public"])
        for track in tracks:
            track["playlist_name"] = name
        all_data.extend(tracks)
        print(f"Found {len(tracks)} tracks in '{name}'")

    # ✅ Export to Excel
    df = pd.DataFrame(all_data)
    df.to_excel("spotify_playlists_tracks.xlsx", index=False)
    print("Exported to spotify_playlists_data.xlsx")


if __name__ == "__main__":
    main()
