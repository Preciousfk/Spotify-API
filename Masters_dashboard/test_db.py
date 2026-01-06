import pyodbc

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=masters2025.database.windows.net;"
    "DATABASE=Spotify_db;"
    "UID=precious;"
    "PWD=tomboystuff2025!;"
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
    "Connection Timeout=30;"
)

print("Connected successfully")
conn.close()