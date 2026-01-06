import pandas as pd
import pyodbc
import numpy as np
from pathlib import Path


# Load CSV data
df = pd.read_excel('Spotify_Tracks.xlsx')
df_1= pd.read_excel('Playlists.xlsx')
Artists= pd.read_excel('Artists.xlsx')
Track_Artists= pd.read_excel('canonical_track_ids.xlsx')
Artists_Nationalities= pd.read_excel('Artist_Nationalities_final.xlsx')
Countries = pd.read_excel('World_Countries_Nationalities_Codes.xlsx')




#DATA CLEANING

# Replace empty strings and NaNs with None
df = df.replace(r'^\s*$', None, regex=True).where(pd.notnull(df), None)
#convert the release date to date format
df['Release_Date'] = pd.to_datetime(df['Release_Date'], format='%Y-%m-%d',errors='coerce').dt.date
#trim date column to remove white spaces
df['Release_Date'] = df['Release_Date'].astype(str).str.strip()

# Replace empty/whitespace with None
df['Release_Date'] = df['Release_Date'].replace(r'^\s*$', None, regex=True)

# Normalize Spotify formats
def normalize_release_date(val):
    if val is None:
        return None
    val = str(val).strip()
    if len(val) == 4:
        return f"{val}-01-01"
    elif len(val) == 7:
        return f"{val}-01"
    return val

df['Release_Date'] = df['Release_Date'].apply(normalize_release_date)

# Convert to date
df['Release_Date'] = pd.to_datetime(
    df['Release_Date'],
    errors='coerce'
).dt.date

# VERY IMPORTANT: convert NaT → None (not string)
df['Release_Date'] = df['Release_Date'].where(
    pd.notnull(df['Release_Date']),
    None
)
#create is_single column
def add_is_single_flag(df):
    df = df.copy()
    df["Is_Single"] = (
        df["Track_Name"].str.strip().str.lower()
        == df["Album_Name"].str.strip().str.lower()
)
df= add_is_single_flag(df)


def create_canonical_track_ids(df):
    # Create a mapping of (Track_Name, Artist_Name) to the first Spotify_Track_ID
    canonical_map = df.groupby(['Track_Name', 'Artist_Name'])['Spotify_Track_ID'].first().reset_index()
    canonical_map = canonical_map.rename(columns={'Spotify_Track_ID': 'Canonical_Track_ID'})
    
    # Merge back to the original dataframe to get Canonical_Track_ID
    df = pd.merge(df, canonical_map, on=['Track_Name', 'Artist_Name'], how='left')
    
    return df
df = create_canonical_track_ids(df)

#creating of tracks dataframe
columns_to_keep = [
    'Track_Name', 
    'Release_Date', 
    'Is_Single', 
    'Canonical_Track_ID'
]
tracks_df = df[columns_to_keep].drop_duplicates(subset=['Canonical_Track_ID'], keep='first')
# tracks_df.to_excel("tracks_dataframe.xlsx", index=False)
 


# CREATE A DATAFRAME WITH ONLY THE CANONICAL TRACK IDS AND ARTIST NAMES
def create_canonical_track_ids_df(df, id_col, artist_col):
    # Select relevant columns and drop duplicates
    df_canonical = df[[id_col, artist_col]].drop_duplicates().reset_index(drop=True)
    return df_canonical
Track_Artists = create_canonical_track_ids_df(df, 'Canonical_Track_ID', 'Artist_Name')

# ##processing the Artist Nationalities df
# print(Artists_Nationalities.columns)
import pandas as pd

def clean_and_explode_artist_nationalities(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()
    # Replace blank cells and NaNs with None
    df = (
        df.replace(r'^\s*$', None, regex=True)
          .where(pd.notnull(df), None)
    )
    # Ensure no leading/trailing whitespace and consistent casing
    df["Artist_Name"] = df["Artist_Name"].str.strip().str.title()

    # Split multiple nationalities and clean
    df["Nationality"] = df["Nationality"].astype(str)
    df["Nationality"] = (
        df["Nationality"]
        .str.split("/")
        .apply(lambda x: [item.strip() for item in x if item.strip()])
    )
    # Explode nationalities into separate rows
    df = df.explode("Nationality").reset_index(drop=True)

    # Log row count after explosion
    print(f"Number of rows after exploding nationalities: {len(df)}")
    return df
Artists_Nationalities = clean_and_explode_artist_nationalities(Artists_Nationalities)

#function to explode genres from final_tracks.xlsx
def explode_genres_df(df, id_col, genre_col, delimiter):
    # We remove the try/except for FileNotFoundError, as the file is already loaded.
    try:
        print(f"Initial number of rows: {len(df)}")

        # 1. Input Check: Ensure the genre column exists
        if genre_col not in df.columns:
            # Raise a specific error if the column is missing
            raise KeyError(f"The specified genre column '{genre_col}' was not found in the input DataFrame.")
            
        # IMPORTANT: Create a copy of the input DataFrame to prevent 'SettingWithCopyWarning' 
        # and ensure the original DataFrame is not modified (good practice).
        df_processed = df.copy() 
        
        # 2. Process, Split, and Clean Genres 
        df_processed[genre_col] = (
            df_processed[genre_col].astype(str).replace('nan', '')
            .str.split(delimiter).apply(lambda x: [item.strip() for item in x if item.strip()])
        )
        
        #convert the genre names to lower case
        df_processed[genre_col] = df_processed[genre_col].apply(lambda genres: [genre.lower() for genre in genres])
        
        # 3. Explode the DataFrame
        df_exploded = df_processed.explode(genre_col)

        # 4. Clean up the resulting DataFrame (remove empty genre rows)
        df_cleaned = df_exploded[df_exploded[genre_col] != ''].reset_index(drop=True)

        print("-" * 30)
        print(f"✅ Genre Explosion Complete!")
        print(f"Final number of rows (exploded): {len(df_cleaned)}")
        
        # 5. Return the result instead of saving to a file
        return df_cleaned

    except KeyError as e:
        print(f"❌ Error: {e}")
        return pd.DataFrame() # Return empty DataFrame on failure
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        return pd.DataFrame()
# Constants for genre explosion
TRACK_ID_COLUMN = 'Canonical_Track_ID'
GENRE_COLUMN = 'Genre_Name'
DELIMITER = ','

df_exploded_genres = explode_genres_df(
    df=df, 
    id_col=TRACK_ID_COLUMN,
    genre_col=GENRE_COLUMN,
    delimiter=DELIMITER
)


# df_exploded_genres.to_excel("exploded_genres_final_tracks.xlsx", index=False)

#Connect to Azure SQL Database
try:
    conn = pyodbc.connect(
    'DRIVER={ODBC Driver 18 for SQL Server};'
    'SERVER=masters2025.database.windows.net;'
    'DATABASE=Spotify_data;'
    'UID=precious;'
    'PWD=tomboystuff2025!;'
    'Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
    print("Authentication Successful")
   
except Exception as e:
    print("Error in connection:", e)
cursor = conn.cursor()

# Helper function to insert if not exists and skip null album name valus and their concurrent rows

def insert_if_not_exists(table, key_column, key_value, insert_columns, insert_values):
    cursor.execute(f"SELECT 1 FROM {table} WHERE {key_column} = ?", key_value)
    if not cursor.fetchone():
        placeholders = ', '.join(['?'] * len(insert_values))
        columns = ', '.join(insert_columns)
        cursor.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", insert_values)

# Process each row
print("CSV Columns:", df.columns.tolist())


# Insert albums data

try:
    for _, row in df.iterrows():
        album_name = row.get('Album_Name')
        spotify_album_id = row.get('Spotify_Album_ID')

        # Skip rows with null or empty Album_Name
        if pd.isna(album_name) or str(album_name).strip() == '':
            print("Skipping row with null Album_Name")
            continue

        # Skip rows with null or empty Spotify_Album_ID
        if pd.isna(spotify_album_id) or str(spotify_album_id).strip() == '':
            print("Skipping row with null Spotify_Album_ID")
            continue

        # Check if album already exists
        cursor.execute("SELECT album_id FROM Albums WHERE Spotify_Album_ID = ?", spotify_album_id)
        existing = cursor.fetchone()

        if existing:
            album_id = existing[0]
            print(f"Album already exists: {album_name}")
        else:
            cursor.execute("""
                INSERT INTO Albums (Album_Name, Spotify_Album_ID, Release_Date)
                VALUES (?, ?, ?)
            """, album_name, spotify_album_id, row['Release_Date'])

            cursor.execute("SELECT SCOPE_IDENTITY()")
            album_id = cursor.fetchone()[0]
            print(f"Inserted new album: {album_name}")

except Exception as e:
    print("Error inserting album data:", e)


# Insert tracks data
for _, row in tracks_df.iterrows():    
    try:
        cursor.execute("""
            INSERT INTO Tracks (Track_Name, Release_Date, Is_Single,Canonical_Track_ID)
            VALUES (?, ?, ?, ?)
        """, row['Track_Name'], row['Release_Date'], row['Is_Single'],row['Canonical_Track_ID'])
        print('Track data successfully inserted')
    except Exception as e:
        print("Error inserting track data:", e)



# Insert playlists data
for _, row in df_1.iterrows():
    try:    
        cursor.execute("""
            INSERT INTO Playlists (Spotify_Playlist_ID, Playlist_Name, Playlist_Owner, Number_Of_Tracks, Number_Of_Followers, Spotify_Playlist_Url, Is_Public)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, row['Spotify_Playlist_ID'], row['Playlist_Name'], row['Playlist_Owner'], row['Number_Of_Tracks'], row['Number_Of_Followers'], row['Spotify_Playlist_Url'], row['Is_Public'])
        print('Playlist data successfully inserted')
    except Exception as e:
        print("Error inserting playlist data:", e)



# Insert artists data
for _, row in Artists.iterrows():
    try:
        artist_name = row.get('Artist_Name')
        cursor.execute(""" 
                       INSERT INTO ARTISTS(Artist_Name)
                       values (?)""" ,row['Artist_Name'])
        print('Artist data successfully inserted')  
    except Exception as e:
        print("Error inserting artist data:", e)   
  

#     Insert genres
# Create a set to track inserted (genre, track_id) pairs
# Create a set to track inserted genres and avoid duplicates
inserted_genres = set()
for _, row in df.iterrows():
    try:
        #  Split the string into a list of genres
        genres = str(row['Genre_Name']).split(', ')
        cleaned_genres = set()
        for g in genres:
            cleaned_genres.add(g.strip().lower())
        
        #  Iterate over the now-deduplicated, cleaned genres
        for genre in cleaned_genres:
            #  Check for duplicates ACROSS ALL ROWS using the 'inserted_genres' set
            if genre and genre not in inserted_genres:
                cursor.execute(
                    """INSERT INTO Genres (Genre_Name) VALUES (?)""",
                    (genre,)
                )
                inserted_genres.add(genre)
    except Exception as e:
        print(f"Error inserting genres for row {row.name}: {e}")
print("Genres insertion process complete.")


# LOAD COUNTRIES TEMPORARY TABLE
for _,row in Countries.iterrows():
    try:
        cursor.execute("""
            INSERT INTO Nationalities (Country_Name, Nationality, Country_Code)
                       values(?, ?, ?)
        """, (row['Country_Name'], row['Nationality'], row['Country_Code']))
        print(f"Country-Nationality-Code relationship for {row['Country_Name']} successfully inserted.")
    except Exception as e:              
        print(f"Error inserting country-nationality-code relationship for {row['Country_Name']}: {e}")   


## LOAD ARTIST_TRACKS RELATIONSHIP TABLE
# Retrieve all existing Artist IDs (assuming an Artists table exists with the Artist Names)
artist_lookup_query = "SELECT Artist_ID, Artist_Name FROM dbo.Artists"
df_artists_id = pd.read_sql(artist_lookup_query, conn)

# Retrieve all existing Track IDs (assuming a Tracks table exists with the Spotify String ID)
track_lookup_query = "SELECT Track_ID, Canonical_Track_ID FROM dbo.Tracks"
df_tracks_id = pd.read_sql(track_lookup_query, conn)

print("Artist and Track IDs retrieved from database.")

# Get the numerical Artist_ID
df_final_junction = pd.merge(
    Track_Artists, 
    df_artists_id, 
    on='Artist_Name', 
    how='inner' # Only include rows where the artist name was found
)

# Get the numerical Track_ID
df_final_junction = pd.merge(
    df_final_junction, 
    df_tracks_id, 
    left_on='Canonical_Track_ID',  
    right_on='Canonical_Track_ID',  
    how='inner' 
)

# Define the columns that form the composite primary key in the database and remove duplicates
KEY_COLUMNS = ['Artist_ID', 'Track_ID']
# Drop duplicates based ONLY on the two key columns.
df_insert = df_final_junction.drop_duplicates(subset=KEY_COLUMNS, keep='first')

print(f"Total unique records ready for insertion: {len(df_insert)}")


# insertion loop
for _, row in df_insert.iterrows():
    try:
        cursor.execute("""
            INSERT INTO dbo.Artist_Tracks (Artist_ID, Track_ID)
            VALUES (?, ?)
        """, (int(row['Artist_ID']), int(row['Track_ID'])))
        
    except Exception as e:
        print(f"CRITICAL SQL ERROR on row ({row['Artist_ID']}, {row['Track_ID']}): {e}")


# LOAD ARTIST NATIONALITIES TEMPORARY TABLE
for _,row in Artists_Nationalities.iterrows():
    try:
        cursor.execute("""
            INSERT INTO ##Artist_Nationalities (Artist_Name, Nationality)
            VALUES (?, ?)
        """, (row['Artist_Name'], row['Nationality']))
        print(f"Artist-Nationality relationship for {row['Artist_Name']} successfully inserted.")
    except Exception as e:
        print(f"Error inserting artist-nationality relationship for {row['Artist_Name']}: {e}")


# LOAD PLAYLIST_TRACKS RELATIONSHIP TABLE
# Retrieve all existing Playlists_ids 
merged_df = pd.merge(
    left=df,
    right=df_1,
    on='Playlist_Name', 
    how='inner'         
)
print(merged_df[['Canonical_Track_ID', 'Spotify_Playlist_ID']].head(20))
print(df.columns)

Track_lookup_query = "SELECT Canonical_Track_ID,Track_ID FROM dbo.tracks"
df_Track_id = pd.read_sql(Track_lookup_query, conn)



# LOAD PLAYLIST_TRACKS RELATIONSHIP TABLE
# Retrieve all existing Playlists_ids 
Playlist_lookup_query = "SELECT Playlist_ID ,Spotify_Playlist_ID FROM dbo.playlists"
df_Playlist_id = pd.read_sql(Playlist_lookup_query, conn)

# print("Playlist and Track IDs retrieved from database.")

# MERGE SOURCE DATA TO GET FINAL IDs 
#  Get the numerical track_ID
df_playlist_tracks_junction = pd.merge(
    df, 
    df_Track_id, 
    on='Canonical_Track_ID', 
    how='inner'
)

#  Get the numerical PLAYLIST_ID

df_playlist_tracks_junction = pd.merge(
    df_playlist_tracks_junction, 
    df_Playlist_id, 
    left_on='Playlist_ID_1',   
    right_on='Spotify_Playlist_ID',  
    how='inner' 
)

#print(df_playlist_tracks_junction.columns)


# remove duplicated

# Define the columns that form the composite primary key in the database
KEY_COLUMNS = ['Playlist_ID', 'Track_ID']
# Drop duplicates based ONLY on the two key columns.
df_insert = df_playlist_tracks_junction.drop_duplicates(subset=KEY_COLUMNS, keep='first')

print(f"Total unique records ready for insertion: {len(df_insert)}")
print(df_insert.tail(10))

#LOAD PLAYLIST_TRACKS RELATIONSHIP TABLE
for _, row in df_insert.iterrows():
    try:
        cursor.execute("""
            INSERT INTO Playlist_Tracks (Playlist_ID,Track_ID)
            VALUES (?, ?)
        """, (row['Playlist_ID'], row['Track_ID']))
        print(f"Playlist-Track relationship for Playlist {row['Playlist_ID']} and Track {row['Track_ID']} successfully inserted.")
    except Exception as e:
        print(f"Error inserting playlist-track relationship for Playlist {row['Playlist_ID']} and Track {row['Track_ID']}: {e}")


# LOAD TRACKS_GENRE RELATIONSHIP TABLE
# Retrieve all existing Genre IDs 
Genre_lookup_query = "SELECT Genre_ID,Genre_Name FROM dbo.Genres"       
df_Genre_id = pd.read_sql(Genre_lookup_query, conn)     
df_Genre_id.to_excel("genre_ids.xlsx", index=False)
# Retrieve all existing Track IDs (assuming a Tracks table exists with the Spotify String ID)
Track_lookup_query = "SELECT Track_ID, Canonical_Track_ID FROM dbo.Tracks"
df_Track_id = pd.read_sql(Track_lookup_query, conn) 
print("Track IDs retrieved from database.")
df_Track_id.to_excel("track_ids.xlsx", index=False)

   
# Merge 1: Get the numerical Track_ID
df_tracks_genres_junction = pd.merge(
    df_exploded_genres, 
    df_Track_id, 
    on='Canonical_Track_ID', 
    how='inner' )

# Merge 2: Get the numerical Genre_ID
df_tracks_genres_junction = pd.merge(   
    df_tracks_genres_junction, 
    df_Genre_id, 
    on='Genre_Name',  
    # right_on='Genre_Name',  
    how='inner' 
)       
df_tracks_genres_junction.to_excel("tracks_genres_junction.xlsx", index=False)
print(df_tracks_genres_junction.columns)

# remove duplicates
# Define the columns that form the composite primary key in the database    
KEY_COLUMNS = ['Track_ID', 'Genre_ID']
# Drop duplicates based ONLY on the two key columns.
df_insert = df_tracks_genres_junction.drop_duplicates(subset=KEY_COLUMNS, keep='first')
print(f"Total unique records ready for insertion: {len(df_insert)}")
#  INSERTION LOOP
for _, row in df_insert.iterrows():
    try:
        cursor.execute("""
            INSERT INTO dbo.Tracks_Genre (Track_ID, Genre_ID)
            VALUES (?, ?)
        """, (int(row['Track_ID']), int(row['Genre_ID'])))
        
    except Exception as e:
        # If an error happens here, the database is severely broken or locked.
        print(f"CRITICAL SQL ERROR on row ({row['Track_ID']}, {row['Genre_ID']}): {e}")



# LOAD ALBUM_PLAYLIST RELATIONSHIP TABLE
Album_lookup_query = "SELECT Album_ID,Spotify_Album_ID FROM dbo.Albums"       
df_Albums_id = pd.read_sql(Album_lookup_query, conn)     
df_Albums_id.to_excel("Album_ids.xlsx", index=False)
# Retrieve all existing Track IDs 
Playlist_lookup_query = "SELECT Spotify_Playlist_ID, Playlist_ID FROM dbo.Playlists"
df_Playlist_id = pd.read_sql(Playlist_lookup_query,conn) 
print("playlist IDs retrieved from database.")
df_Playlist_id.to_excel("Playlist_ids.xlsx", index=False)

# MERGE SOURCE DATA TO GET FINAL IDs  
# Merge 1: Get the numerical Track_ID
df_Albums_Playlist_junction = pd.merge(
    df, 
    df_Albums_id, 
    on='Spotify_Album_ID',
    how='inner' 
)
df_Albums_Playlist_junction = pd.merge(
    df_Albums_Playlist_junction, 
    df_Playlist_id, 
    right_on='Spotify_Playlist_ID',
    left_on='Playlist_ID_1',
    how='inner' 
)

print(df_Albums_Playlist_junction.columns)
df_Albums_Playlist_junction.to_excel("Albums_Playlist_junction.xlsx", index=False)


# Define the columns that form the composite primary key in the database and remove duplicates
KEY_COLUMNS = ['Album_ID', 'Playlist_ID']
# Drop duplicates based ONLY on the two key columns.
df_insert = df_Albums_Playlist_junction.drop_duplicates(subset=KEY_COLUMNS, keep='first')
print(f"Total unique records ready for insertion: {len(df_insert)}")
# insertion loop
for _, row in df_insert.iterrows():
    try:
        cursor.execute("""
            INSERT INTO dbo.Album_Playlist (Album_ID, Playlist_ID)
            VALUES (?, ?)
        """, (int(row['Album_ID']), int(row['Playlist_ID'])))
        
    except Exception as e:
        print(f"CRITICAL SQL ERROR on row ({row['Album_ID']}, {row['Playlist_ID']}): {e}")


conn.commit()
cursor.close()
conn.close()