import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd

# Load environment variables
load_dotenv()
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")

# Authenticate with Authorization Code Flow
scope = "playlist-read-private"
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=CLIENT_ID,
                                               client_secret=CLIENT_SECRET,
                                               redirect_uri=REDIRECT_URI,
                                               scope=scope))

# Function to search playlists by keyword
def search_playlists(keyword, limit=50, offset=0):
    results = sp.search(q=keyword, type='playlist', limit=limit, offset=offset)
    playlists = []
    for playlist in results['playlists']['items']:
        if playlist and 'name' in playlist:  # ✅ Check for valid playlist object
            playlists.append({
                "name": playlist.get('name'),
                "owner": playlist['owner'].get('display_name'),
                "tracks_count": playlist.get('tracks', {}).get('total', 0),
                "url": playlist['external_urls'].get('spotify')
            })
    return playlists


# Collect playlists for multiple keywords
keywords = ["African","Afro"]
all_playlists = []

for word in keywords:
    print(f"\nSearching for playlists with '{word}'...")
    offset = 0
    while True:
        playlists = search_playlists(word, limit=50, offset=offset)
        if not playlists:
            break
        all_playlists.extend(playlists)
        offset += 50  # Go to next batch
        if offset >= 1000:  # Stop after 1000 per keyword (API practical limit)
            break

# Convert to DataFrame
df = pd.DataFrame(all_playlists).drop_duplicates(subset=["url"])

# ✅ Export to Excel
excel_file = "spotify_playlists.xlsx"
df.to_excel(excel_file, index=False)
print(f"\nExported {len(df)} playlists to {excel_file}")

# ✅ OPTIONAL: Export to Google Sheets
# Install required library: pip install gspread oauth2client
# Uncomment below after setting up Google API credentials

# import gspread
# from oauth2client.service_account import ServiceAccountCredentials
#
# scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
# creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
# client = gspread.authorize(creds)
#
# sheet = client.create("Spotify Playlists")
# worksheet = sheet.get_worksheet(0)
# worksheet.append_row(df.columns.tolist())
# for row in df.values.tolist():
#     worksheet.append_row(row)
# print("Exported to Google Sheets")
