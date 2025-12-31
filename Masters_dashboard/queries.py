use Spotify_data;


- Main tables creation

-- 1)
 CREATE TABLE Albums (
    album_id INT PRIMARY KEY IDENTITY(1,1),
    album_name NVARCHAR(255),
    spotify_album_id NVARCHAR(100),
    release_date DATE
);



-- 2)
 CREATE TABLE Tracks (
    track_id INT PRIMARY KEY IDENTITY(1,1),
    canonical_track_id varchar(255),
    track_name NVARCHAR(255),
    release_date DATE,
    is_single float,
    spotify_track_url NVARCHAR(500),
    spotify_track_uri NVARCHAR(100)
    
);


-- 3)
 CREATE TABLE Playlists (
    Id     INT     PRIMARY KEY IDENTITY (1, 1) NOT NULL,
    Spotify_Playlist_ID VARCHAR (50) NULL,
    Playlist_Name    VARCHAR (500) NULL,
    Playlist_Owner     VARCHAR (50) NULL,
    Number_Of_Tracks    INT          NULL,
    Number_Of_Followers INT          NULL,
    Spotify_Playlist_URL varchar(1000) null,
    is_public  float null
);

-- 4)
CREATE TABLE Artists(
    Artist_ID INT   primary key  IDENTITY (1, 1),
    Artist_Name nvarchar(255) NOT NULL UNIQUE);


-- 5)
 CREATE TABLE Nationalities (
    Nationality_Id INT   PRIMARY KEY IDENTITY (1, 1) NOT NULL,
    Nationality    VARCHAR (50)  NULL,
    Country_Name   VARCHAR (50)  NULL,
    Country_Code   VARCHAR (50)  NULL
);


---JUNCTION TABLEs CREATION--------

--  6)
 CREATE TABLE Artist_Tracks (
    -- Foreign Keys pointing to the parent tables
    Artist_ID INT NOT NULL,
    Track_ID int NOT NULL,

    -- Define the Composite Primary Key
    PRIMARY KEY (Artist_ID, Track_ID),

    -- Enforce Referential Integrity (FKs)
    FOREIGN KEY (Artist_ID) REFERENCES Artists(Artist_Id),
    FOREIGN KEY (Track_ID) REFERENCES Tracks(Track_ID)
);




-- 7) CREATE TABLE GENRES
CREATE TABLE Genres (
    GENRE_Id   INT          IDENTITY (1, 1) NOT NULL,
    [Genre_Name] VARCHAR (50) NULL,
    CONSTRAINT PK_Genre PRIMARY KEY CLUSTERED (GENRE_Id ASC)
);


-- 8). Create the Junction Table 
CREATE TABLE Artist_Nationalities (
    -- Foreign Keys pointing to the parent tables
    Artist_ID INT NOT NULL,
    Nationality_ID INT NOT NULL,

    -- Define the Composite Primary Key
    PRIMARY KEY (Artist_ID, Nationality_ID),

    -- Enforce Referential Integrity (FKs)
    FOREIGN KEY (Artist_ID) REFERENCES dbo.Artists(Artist_Id),
    FOREIGN KEY (Nationality_ID) REFERENCES nationalities(Nationality_ID)
);

---8.1) create temporary table

CREATE TABLE ##Artist_Nationalities (
    Artist_Name VARCHAR(255),
     Nationality VARCHAR(255)

);


-- 8.2) Load Artist_Nationalities table 
INSERT INTO Artist_Nationalities (Artist_ID, Nationality_ID)
SELECT
    A.Artist_ID,          -- The ID looked up from the Artists table
    N.Nationality_ID      -- The ID looked up from the Nationalities table
FROM
    ##Artist_Nationalities AS S  -- S: Your raw data source (with names)
inner JOIN
    Artists AS A ON S.Artist_Name = A.Artist_Name  -- Match names to get Artist_ID
inner JOIN
    Nationalities AS N ON S.Nationality = N.Nationality  -- Match names to get Nationality_ID;


--9)  CREATE PLAYLIST_TRACKS JUNCTION TABLE

CREATE TABLE Playlist_Tracks(
    -- Foreign Keys pointing to the parent tables
    playlist_ID INT NOT NULL,
    Track_ID INT NOT NULL,

    -- Define the Composite Primary Key
    PRIMARY KEY (playlist_id, Track_ID),

    -- Enforce Referential Integrity (FKs)
    FOREIGN KEY (playlist_id) REFERENCES playlists(playlist_Id),
    FOREIGN KEY (Track_ID) REFERENCES Tracks(Track_ID)
);

-- 9.1) CREATE TEMPORATY TABLE WITH PLAYLIST AND TRACK IDS
CREATE TABLE Playlist_Tracks_TEMP (
    Canonical_Track_id VARCHAR(255),
     Spotify_playlist_id VARCHAR(255)
);



--10.0) CREATE Album_Playlist JUNCTION TABLE
CREATE TABLE Album_Playlist (
    ALBUM_ID INT NOT NULL,
    PLAYLIST_ID INT NOT NULL,
     PRIMARY KEY (ALBUM_ID,PLAYLIST_ID),
     FOREIGN KEY (ALBUM_ID) REFERENCES ALBUMs(ALBUM_ID),
     FOREIGN KEY (PLAYLIST_ID) REFERENCES PLAYLISTS(PLAYLIST_ID))


-- 11) CREATE TRACKS_GENRE JUNCTION TABLE
CREATE TABLE Tracks_Genre (
    TRACK_ID INT NOT NULL,
    GENRE_ID INT NOT NULL,
    PRIMARY KEY CLUSTERED (TRACK_ID ASC, GENRE_ID ASC),
    FOREIGN KEY (GENRE_ID) REFERENCES dbo.Genres (GENRE_Id),
    FOREIGN KEY (TRACK_ID) REFERENCES dbo.Tracks (track_id)
);


