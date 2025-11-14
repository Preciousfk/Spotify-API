import pandas as pd
import pyodbc
import numpy as np
from pathlib import Path


# Load CSV data
df = pd.read_excel('final_tracks.xlsx')
df_1= pd.read_excel('Final Afican Playlists.xlsx')
# Artists= pd.read_excel('Artists.xlsx')
# Track_Artists= pd.read_excel('canonical_track_ids_Artist_names.xlsx')
# Artists_Nationalities= pd.read_excel('Artist_Nationalities_final.xlsx')
# Countries = pd.read_excel('World_Countries_Nationalities_Codes.xlsx')


# print("DF Source Columns:", Track_Artists.columns.tolist())


# Replace empty strings and NaNs with None
df = df.replace(r'^\s*$', None, regex=True).where(pd.notnull(df), None)
#convert the release date to date format
df['Release_Date'] = pd.to_datetime(df['Release_Date'], format='%Y-%m-%d',errors='coerce').dt.date

# identify the rows with the same value in the track name and album names and create a new column called singles
df['Is_Single'] = df['Track_Name'] == df['Album_Name']
# for the songs where is_single is True replace the album name and album id  with nulls
df.loc[df['Is_Single'] == True, 'Album_Name'] = None
df.loc[df['Is_Single'] == True, 'Spotify_Album_ID'] = None
df= df.drop_duplicates()

# print(df[df['Album_Name'].isnull()][['Track_Name', 'Album_Name','Artist_Name','Is_Single']].head(20))

#NORMALIZE SPOTIFY TRACK IDS TO CREATE CANONICAL TRACK IDS
df['Track_Name'] = df['Track_Name'].replace('', np.nan)
df['Artist_Name'] = df['Artist_Name'].replace('', np.nan)
complete_song_mask = df['Track_Name'].notna() & df['Artist_Name'].notna()
canonical_map = df.groupby(['Track_Name', 'Artist_Name'])['Spotify_Track_ID'].transform('first')
df['Canonical_Track_ID'] = df['Spotify_Track_ID']
df.loc[complete_song_mask, 'Canonical_Track_ID'] = canonical_map[complete_song_mask]

# df.to_excel("final_tracks_With_Canonical_track_id.xlsx", index=False)


## CREATE A DATAFRAME WITH ONLY THE CANONICAL TRACK IDS AND ARTIST NAMES

# cols= ['Canonical_Track_ID','Artist_Name']
# #create a dataframe from the series
# df_canonical_track_ids = df[cols].copy()
# df_canonical_track_ids.to_excel("canonical_track_ids.xlsx", index=False)    
# print("Exported to canonical_track_ids.xlsx")

# ##processing the Artist Nationalities df
# print(Artists_Nationalities.columns)

# #replace blank cells with Null
# Artists_Nationalities = Artists_Nationalities.replace(r'^\s*$', None, regex=True).where(pd.notnull(Artists_Nationalities), None)
# #esure no leading/trailing whitespace in Artist_Name and National
# Artists_Nationalities['Artist_Name'] = Artists_Nationalities['Artist_Name'].str.strip()
# #ensure first letter is capital for consistency
# Artists_Nationalities['Artist_Name'] = Artists_Nationalities['Artist_Name'].str.title()
# ## 4. Split by delimiter and strip whitespace, then explode
# Artists_Nationalities['Nationality'] = Artists_Nationalities['Nationality'].astype(str)
# Artists_Nationalities['Nationality'] = Artists_Nationalities['Nationality'].str.split('/').apply(lambda x: [item.strip() for item in x if item.strip()])          
# Artists_Nationalities = Artists_Nationalities.explode('Nationality').reset_index(drop=True)      
# print(Artists_Nationalities.head(50))


# df = pd.DataFrame(df)
# df.to_excel("cleaned_df.xlsx", index=False)
# print("Exported to cleaned_df.xlsx")

#function to explode genres from final_tracks.xlsx
# def explode_genres_df(df, id_col, genre_col, delimiter):
#     # We remove the try/except for FileNotFoundError, as the file is already loaded.
#     try:
#         print(f"Initial number of rows: {len(df)}")

#         # 1. Input Check: Ensure the genre column exists
#         if genre_col not in df.columns:
#             # Raise a specific error if the column is missing
#             raise KeyError(f"The specified genre column '{genre_col}' was not found in the input DataFrame.")
            
#         # IMPORTANT: Create a copy of the input DataFrame to prevent 'SettingWithCopyWarning' 
#         # and ensure the original DataFrame is not modified (good practice).
#         df_processed = df.copy() 
        
#         # 2. Process, Split, and Clean Genres 
#         df_processed[genre_col] = (
#             df_processed[genre_col].astype(str).replace('nan', '')
#             .str.split(delimiter).apply(lambda x: [item.strip() for item in x if item.strip()])
#         )
        
#         # 3. Explode the DataFrame
#         df_exploded = df_processed.explode(genre_col)

#         # 4. Clean up the resulting DataFrame (remove empty genre rows)
#         df_cleaned = df_exploded[df_exploded[genre_col] != ''].reset_index(drop=True)

#         print("-" * 30)
#         print(f"✅ Genre Explosion Complete!")
#         print(f"Final number of rows (exploded): {len(df_cleaned)}")
        
#         # 5. Return the result instead of saving to a file
#         return df_cleaned

#     except KeyError as e:
#         print(f"❌ Error: {e}")
#         return pd.DataFrame() # Return empty DataFrame on failure
#     except Exception as e:
#         print(f"❌ An unexpected error occurred: {e}")
#         return pd.DataFrame()
# # Constants for genre explosion
# TRACK_ID_COLUMN = 'Canonical_Track_ID'
# GENRE_COLUMN = 'Genre_Name'
# DELIMITER = ','

# df_exploded_genres = explode_genres_df(
#     df=df, 
#     id_col=TRACK_ID_COLUMN,
#     genre_col=GENRE_COLUMN,
#     delimiter=DELIMITER
# )


# print(df_exploded_genres.head(20))

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
# print("CSV Columns:", df.columns.tolist())


## Insert albums data

# try:
#     for _, row in df.iterrows():
#         album_name = row.get('Album_Name')
#         spotify_album_id = row.get('Spotify_Album_ID')

#         # Skip rows with null or empty Album_Name
#         if pd.isna(album_name) or str(album_name).strip() == '':
#             print("Skipping row with null Album_Name")
#             continue

#         # Skip rows with null or empty Spotify_Album_ID
#         if pd.isna(spotify_album_id) or str(spotify_album_id).strip() == '':
#             print("Skipping row with null Spotify_Album_ID")
#             continue

#         # Check if album already exists
#         cursor.execute("SELECT album_id FROM Albums WHERE Spotify_Album_ID = ?", spotify_album_id)
#         existing = cursor.fetchone()

#         if existing:
#             album_id = existing[0]
#             print(f"Album already exists: {album_name}")
#         else:
#             cursor.execute("""
#                 INSERT INTO Albums (Album_Name, Spotify_Album_ID, Release_Date)
#                 VALUES (?, ?, ?)
#             """, album_name, spotify_album_id, row['Release_Date'])

#             cursor.execute("SELECT SCOPE_IDENTITY()")
#             album_id = cursor.fetchone()[0]
#             print(f"Inserted new album: {album_name}")

# except Exception as e:
#     print("Error inserting album data:", e)



## Insert tracks data
# for _, row in df.iterrows():    
#     try:
#         cursor.execute("""
#             INSERT INTO Tracks (Track_Name, Spotify_Track_ID, Release_Date, Is_Single,Canonical_Track_ID)
#             VALUES (?, ?, ?, ?, ?)
#         """, row['Track_Name'], row['Spotify_Track_ID'], row['Release_Date'], row['Is_Single'],row['Canonical_Track_ID'])
#         print('Track data successfully inserted')
#     except Exception as e:
#         print("Error inserting track data:", e)



## Insert playlists data
# for _, row in df_1.iterrows():
#     try:    
#         cursor.execute("""
#             INSERT INTO Playlists (Spotify_Playlist_ID, Playlist_Name, Playlist_Owner, Number_Of_Tracks, Number_Of_Followers, Spotify_Playlist_Url, Is_Public)
#             VALUES (?, ?, ?, ?, ?, ?, ?)
#         """, row['Spotify_Playlist_ID'], row['Playlist_Name'], row['Playlist_Owner'], row['Number_Of_Tracks'], row['Number_Of_Followers'], row['Spotify_Playlist_Url'], row['Is_Public'])
#         print('Playlist data successfully inserted')
#     except Exception as e:
#         print("Error inserting playlist data:", e)



# # Insert artists data
# for _, row in Artists.iterrows():
#     try:
#         artist_name = row.get('Artist_Name')
#         cursor.execute(""" 
#                        INSERT INTO ARTISTS(Artist_Name)
#                        values (?)""" ,row['Artist_Name'])
#         print('Artist data successfully inserted')  
#     except Exception as e:
#         print("Error inserting artist data:", e)   
  

    # Insert genres
# Create a set to track inserted (genre, track_id) pairs
# Create a set to track inserted genres and avoid duplicates
# inserted_genres = set()

# for _, row in df.iterrows():
#     try:
#         # 1. Split the string into a list of genres
#         genres = str(row['Genre_Name']).split(', ')
        
#         # --- NEW CODE BLOCK FOR DEDUPING/CLEANUP WITHIN THE ROW ---
#         # 2. Cleanup and normalize each genre, and use a set to remove duplicates within this row.
#         cleaned_genres = set()
#         for g in genres:
#             cleaned_genres.add(g.strip().lower())
#         # --- END NEW CODE BLOCK ---
        
#         # 3. Iterate over the now-deduplicated, cleaned genres
#         for genre in cleaned_genres:
#             # 4. Check for duplicates ACROSS ALL ROWS using the 'inserted_genres' set
#             if genre and genre not in inserted_genres:
#                 cursor.execute(
#                     """INSERT INTO Genres (Genre_Name) VALUES (?)""",
#                     (genre,)
#                 )
#                 inserted_genres.add(genre)
                
#         # Move print statement outside the inner loop to avoid clutter
        
#     except Exception as e:
#         print(f"Error inserting genres for row {row.name}: {e}")

# # This print statement should ideally be outside the main 'for' loop
# print("Genres insertion process complete.")









# SOURCING THE TRACK AND ARTIST IDS FROM THE RESPECTIVE TABLES IN DB

# artist_lookup_query = "SELECT Artist_ID, Artist_Name FROM dbo.Artists"
# df_artists_id = pd.read_sql(artist_lookup_query, conn)

# # Retrieve all existing Track IDs (assuming a Tracks table exists with the Spotify String ID)
# track_lookup_query = "SELECT Track_ID, Canonical_Track_ID FROM dbo.Tracks"
# df_tracks_id = pd.read_sql(track_lookup_query, conn)

# print("Artist and Track IDs retrieved from database.")

# # --- STEP 2: MERGE SOURCE DATA TO GET FINAL IDs ---

# # # Merge 1: Get the numerical Artist_ID
# df_final_junction = pd.merge(
#     Track_Artists, 
#     df_artists_id, 
#     on='Artist_Name', 
#     how='inner' # Only include rows where the artist name was found
# )

# # # Merge 2: Get the numerical Track_ID
# # Corrected Merge (Assuming the column is 'Spotify_Track_ID')
# df_final_junction = pd.merge(
#     df_final_junction, 
#     df_tracks_id, 
#     left_on='Canonical_Track_ID',   # Use the correct column name from df_final_junction
#     right_on='Canonical_Track_ID',  # Use the correct column name from df_tracks_id (the DB output)
#     how='inner' 
# )

# # --- STEP 3: DEDUPICATION (THIS RESOLVES YOUR ERROR) ---

# # Define the columns that form the composite primary key in the database
# KEY_COLUMNS = ['Artist_ID', 'Track_ID']
# # Drop duplicates based ONLY on the two key columns.
# df_insert = df_final_junction.drop_duplicates(subset=KEY_COLUMNS, keep='first')

# print(f"Total unique records ready for insertion: {len(df_insert)}")


# --- STEP 4: INSERTION LOOP ---
# for _, row in df_insert.iterrows():
#     try:
#         cursor.execute("""
#             INSERT INTO dbo.Artist_Tracks (Artist_ID, Track_ID)
#             VALUES (?, ?)
#         """, (int(row['Artist_ID']), int(row['Track_ID'])))
        
#     except Exception as e:
#         # If an error happens here, the database is severely broken or locked.
#         print(f"CRITICAL SQL ERROR on row ({row['Artist_ID']}, {row['Track_ID']}): {e}")






#insert track-artists relationships
# for _, row in Track_Artists.iterrows():
#     try:
#         # FIX: Parameters must be grouped into a single tuple (row[...], row[...])
#         cursor.execute("""
#             INSERT INTO ##Tracks_Artists (Spotify_Track_ID, Artist_Name)
#             VALUES (?, ?)
#         """, (row['Spotify_Track_ID'], row['Artist_Name']))
        
#         # It's better to print the specific track ID being inserted for debugging
#         print(f"Track-Artist relationship for {row['Spotify_Track_ID']} successfully inserted.")
        
#     except Exception as e:
#         # Include the specific data causing the error for better debugging
#         print(f"Error inserting track-artist relationship for {row['Spotify_Track_ID']}: {e}")

# # LOAD ARTIST NATIONALITIES TEMPORARY TABLE
# for _,row in Artists_Nationalities.iterrows():
#     try:
#         cursor.execute("""
#             INSERT INTO ##Artist_Nationalities (Artist_Name, Nationality)
#             VALUES (?, ?)
#         """, (row['Artist_Name'], row['Nationality']))
#         print(f"Artist-Nationality relationship for {row['Artist_Name']} successfully inserted.")
#     except Exception as e:
#         print(f"Error inserting artist-nationality relationship for {row['Artist_Name']}: {e}")


# # LOAD COUNTRIES TEMPORARY TABLE
# for _,row in Countries.iterrows():
#     try:
#         cursor.execute("""
#             INSERT INTO Nationalities (Country_Name, Nationality, Country_Code)
#                        values(?, ?, ?)
#         """, (row['Country_Name'], row['Nationality'], row['Country_Code']))
#         print(f"Country-Nationality-Code relationship for {row['Country_Name']} successfully inserted.")
#     except Exception as e:              
#         print(f"Error inserting country-nationality-code relationship for {row['Country_Name']}: {e}")   
                
# ##CREATE A Playlists_Track DATAFRAME WITH CONONICAL IDS AND PLAYLIST IDS
# #Match the spotify playlist ids from df_1 to df based on playlist names
# merged_df = pd.merge(
#     left=df,
#     right=df_1,
#     on='Playlist_Name', # The common column to match rows
#     how='inner'         # Keeps only rows that match in both DataFrames
# )
# print(merged_df[['Canonical_Track_ID', 'Spotify_Playlist_ID']].head(20))


# print(df.columns)

# Track_lookup_query = "SELECT Canonical_Track_ID,Track_ID FROM dbo.tracks"
# df_Track_id = pd.read_sql(Track_lookup_query, conn)

# print(df.columns)
# print(df_Track_id.columns)

## LOAD PLAYLIST_TRACKS RELATIONSHIP TABLE

# # Retrieve all existing Playlists_ids (assuming a Tracks table exists with the Spotify String ID)
# Playlist_lookup_query = "SELECT Playlist_ID ,Spotify_Playlist_ID FROM dbo.playlists"
# df_Playlist_id = pd.read_sql(Playlist_lookup_query, conn)

# print("Playlist and Track IDs retrieved from database.")

# --- STEP 2: MERGE SOURCE DATA TO GET FINAL IDs ---

# # Merge 1: Get the numerical track_ID
# df_playlist_tracks_junction = pd.merge(
#     df, 
#     df_Track_id, 
#     on='Canonical_Track_ID', 
#     how='inner'
# )

# # # # Merge 2: Get the numerical PLAYLIST_ID

# df_playlist_tracks_junction = pd.merge(
#     df_playlist_tracks_junction, 
#     df_Playlist_id, 
#     left_on='Playlist_ID_1',   
#     right_on='Spotify_Playlist_ID',  
#     how='inner' 
# )

# print(df_playlist_tracks_junction.columns)


# # # --- STEP 3: DEDUPICATION (THIS RESOLVES YOUR ERROR) ---

# # Define the columns that form the composite primary key in the database
# KEY_COLUMNS = ['Playlist_ID', 'Track_ID']
# # Drop duplicates based ONLY on the two key columns.
# df_insert = df_playlist_tracks_junction.drop_duplicates(subset=KEY_COLUMNS, keep='first')

# print(f"Total unique records ready for insertion: {len(df_insert)}")
# print(df_insert.tail(10))

# #LOAD PLAYLIST_TRACKS RELATIONSHIP TABLE
# for _, row in df_insert.iterrows():
#     try:
#         cursor.execute("""
#             INSERT INTO Playlist_Tracks (Playlist_ID,Track_ID)
#             VALUES (?, ?)
#         """, (row['Playlist_ID'], row['Track_ID']))
#         print(f"Playlist-Track relationship for Playlist {row['Playlist_ID']} and Track {row['Track_ID']} successfully inserted.")
#     except Exception as e:
#         print(f"Error inserting playlist-track relationship for Playlist {row['Playlist_ID']} and Track {row['Track_ID']}: {e}")


## LOAD TRACKS_GENRE RELATIONSHIP TABLE
# # Retrieve all existing Genre IDs (assuming a Genres table exists with the Genre_Name)
# Genre_lookup_query = "SELECT Genre_ID,Genre_Name FROM dbo.Genres"       
# df_Genre_id = pd.read_sql(Genre_lookup_query, conn)     
# print("Genre IDs retrieved from database.")
# # Retrieve all existing Track IDs (assuming a Tracks table exists with the Spotify String ID)
# Track_lookup_query = "SELECT Track_ID, Canonical_Track_ID FROM dbo.Tracks"
# df_Track_id = pd.read_sql(Track_lookup_query, conn) 
# print("Track IDs retrieved from database.")
# # --- STEP 2: MERGE SOURCE DATA TO GET FINAL IDs ---    
# # Merge 1: Get the numerical Track_ID
# df_tracks_genres_junction = pd.merge(
#     df_exploded_genres, 
#     df_Track_id, 
#     on='Canonical_Track_ID', 
#     how='inner' 
# )
# # Merge 2: Get the numerical Genre_ID
# df_tracks_genres_junction = pd.merge(   
#     df_tracks_genres_junction, 
#     df_Genre_id, 
#     left_on='Genre_Name',   
#     right_on='Genre_Name',  
#     how='inner' 
# )       
# print(df_tracks_genres_junction.columns)
# # --- STEP 3: DEDUPICATION (THIS RESOLVES YOUR ERROR) ---
# # Define the columns that form the composite primary key in the database    
# KEY_COLUMNS = ['Track_ID', 'Genre_ID']
# # Drop duplicates based ONLY on the two key columns.
# df_insert = df_tracks_genres_junction.drop_duplicates(subset=KEY_COLUMNS, keep='first')
# print(f"Total unique records ready for insertion: {len(df_insert)}")
# # --- STEP 4: INSERTION LOOP ---
# for _, row in df_insert.iterrows():
#     try:
#         cursor.execute("""
#             INSERT INTO dbo.Tracks_Genre (Track_ID, Genre_ID)
#             VALUES (?, ?)
#         """, (int(row['Track_ID']), int(row['Genre_ID'])))
        
#     except Exception as e:
#         # If an error happens here, the database is severely broken or locked.
#         print(f"CRITICAL SQL ERROR on row ({row['Track_ID']}, {row['Genre_ID']}): {e}")



#Commit and close
conn.commit()
cursor.close()
conn.close()