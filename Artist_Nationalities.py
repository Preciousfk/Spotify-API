import pandas as pd
import requests
import wikipedia
import time

# Load artist names
df = pd.read_excel("artist_names.xlsx")
artist_names = df["artist_names"].dropna().unique().tolist()

def get_musicbrainz_data(artist_name):
    """Fetch artist info from MusicBrainz API."""
    try:
        url = "https://musicbrainz.org/ws/2/artist/"
        params = {
            "query": f'artist:"{artist_name}"',
            "fmt": "json",
            "limit": 1
        }
        res = requests.get(url, params=params, headers={"User-Agent": "UWE-Research/1.0"})
        if res.status_code == 200:
            data = res.json()
            if "artists" in data and len(data["artists"]) > 0:
                artist = data["artists"][0]
                return {
                    "artist": artist_name,
                    "country": artist.get("country", "Unknown"),
                    "disambiguation": artist.get("disambiguation", ""),
                    "tags": ", ".join([t["name"] for t in artist.get("tags", [])]) if "tags" in artist else ""
                }
    except Exception as e:
        print(f"MusicBrainz error for {artist_name}: {e}")
    return None

def get_wikipedia_data(artist_name):
    """Fallback: Fetch nationality from Wikipedia summary."""
    try:
        page = wikipedia.page(artist_name, auto_suggest=False)
        summary = page.summary.lower()
        # Look for nationality keywords
        nationalities = [
            "nigerian", "ghanaian", "south african", "kenyan", "tanzanian", 
            "british", "american", "french", "jamaican", "canadian"
        ]
        nationality = next((n for n in nationalities if n in summary), "Unknown")
        return {
            "artist": artist_name,
            "Nationality": nationality,
            "disambiguation": "Wikipedia",
            "tags": ""
        }
    except Exception:
        return {
            "artist": artist_name,
            "country": "Unknown",
            "disambiguation": "Not found",
            "tags": ""
        }

results = []
for artist in artist_names[:20]:  # limit for testing first
    print(f"Fetching: {artist}")
    mb_data = get_musicbrainz_data(artist)
    if mb_data and mb_data["country"] != "Unknown":
        results.append(mb_data)
    else:
        wiki_data = get_wikipedia_data(artist)
        results.append(wiki_data)
    time.sleep(1)  # Respect API rate limits

# Save to Excel
out_df = pd.DataFrame(results)
out_df.to_excel("artist_nationalities.xlsx", index=False)
print("✅ Exported artist_nationalities.xlsx")
