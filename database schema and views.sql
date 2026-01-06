use Spotify_data;


-- Main tables creation

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

    Artist_ID INT NOT NULL,
    Track_ID int NOT NULL,


    PRIMARY KEY (Artist_ID, Track_ID),


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

    Artist_ID INT NOT NULL,
    Nationality_ID INT NOT NULL,

 
    PRIMARY KEY (Artist_ID, Nationality_ID),

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
    A.Artist_ID,          
    N.Nationality_ID      
FROM
    ##Artist_Nationalities AS S  
inner JOIN
    Artists AS A ON S.Artist_Name = A.Artist_Name  
inner JOIN
    Nationalities AS N ON S.Nationality = N.Nationality  


--9)  CREATE PLAYLIST_TRACKS JUNCTION TABLE

CREATE TABLE Playlist_Tracks(

    playlist_ID INT NOT NULL,
    Track_ID INT NOT NULL,

    PRIMARY KEY (playlist_id, Track_ID),


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


--- creation of views for analysis----
GO
CREATE VIEW vw_all_playlists AS
SELECT
    playlist_id,
    playlist_name,
    playlist_owner,
    CASE 
  WHEN playlist_owner = 'Spotify' THEN 'Algorithmic'
  ELSE 'User'
END AS playlist_type
FROM playlists;

GO
CREATE VIEW vw_user_curated_playlists AS
SELECT
    playlist_id,
    playlist_name,
    playlist_owner
FROM playlists
WHERE LOWER(playlist_owner) <> 'spotify';


GO
CREATE VIEW vw_playlist_track_facts AS
SELECT
    p.playlist_id,
    p.playlist_name,
    t.track_id,
    t.track_name,
    a.artist_id,
    a.artist_name,
    n.nationality,
    t.release_date,
    CASE 
        WHEN n.country_code IN (
            'DZ','AO','BJ','BW','BF','BI','CM','CV','CF','TD','KM','CG','CD','CI','DJ','EG','GQ','ER','ET',
            'GA','GM','GH','GN','GW','KE','LS','LR','LY','MG','MW','ML','MR','MU','MA','MZ','NA','NE','NG',
            'RW','ST','SN','SC','SL','SO','ZA','SS','SD','TZ','TG','TN','UG','ZM','ZW'
        ) THEN 'African'
        ELSE 'non_African' 
    END AS is_african_nationality,
    g.genre_name
FROM vw_user_curated_playlists p
JOIN playlist_tracks pt ON pt.playlist_id = p.playlist_id
JOIN tracks t ON t.track_id = pt.track_id
JOIN artist_tracks at ON at.track_id = t.track_id
JOIN artists a ON a.artist_id = at.artist_id
LEFT JOIN artist_nationalities an ON an.artist_id = a.artist_id
LEFT JOIN nationalities n ON n.nationality_id = an.nationality_id
LEFT JOIN tracks_genre tg ON tg.track_id = t.track_id
LEFT JOIN genres g ON g.genre_id = tg.genre_id
;


GO
CREATE VIEW vw_playlist_nationality_distribution AS
SELECT
    playlist_id,
    playlist_name,
    nationality,
    COUNT(*) AS track_count
FROM vw_playlist_track_facts
GROUP BY playlist_id, nationality,playlist_name
;




GO
CREATE VIEW vw_playlist_genre_distribution AS
With african_genres as (select genre_id,genre_name from genres where genre_name in
 (('afrobeats'),('afropop'),('afro r&b'),('afrobeat'),('afropiano'),('afro soul'),('afroswing'),
 ('azonto'),('alté'),('afro adura'),('ghanaian hip hop'),('amapiano'),
('gqom'),('rap'),('french r&b'),('pop urbaine'),('asakaa'),('hiplife'),('highlife'),
('gospel'),('bongo piano'),('private school piano'),('bacardi'),('3 step'),('ndombolo'),
('rumba congolaise'),('afro house'),('bikutsi'),('gnawa'),('kizomba'),('sufi'),('tribal house'),
('afro tech'),('ethiopian jazz'),('coupé décalé'),('traditional music'),('nigerian drill'),
('bongo flava'),('singeli'),('gengetone'),('gospel r&b'),('fújì'),('rap ivoire'),('kuduro'),
('african gospel'),('alternative r&b'),('maskandi'),('moroccan pop'),('raï'),('moroccan rap'),
('moroccan chaabi'),('mahraganat'),('christian alternative rock'),('lo-fi'),('lo-fi beats'),('gospel'),
'bongo','rumba congolaise','singeli','ndombolo','hiplife','nigerian drill','jazz'))
SELECT
    playlist_id,
    Playlist_name,
    ag.genre_name,
    a.release_date,
    COUNT(distinct(track_id)) AS track_count,
    CAST(COUNT(track_id) AS FLOAT)
      / SUM(COUNT(track_id)) OVER (PARTITION BY playlist_id) AS proportion
FROM vw_playlist_track_facts a
join african_genres ag on ag.genre_name= a.genre_name
GROUP BY playlist_id,playlist_name, ag.genre_name;


GO
CREATE VIEW vw_playlist_artist_exposure AS
SELECT
    playlist_id,
    playlist_name,
    artist_id,
    artist_name,
    COUNT(distinct(track_id)) AS track_count,
    CAST(COUNT(*) AS FLOAT)
      / SUM(COUNT(*)) OVER (PARTITION BY playlist_id) AS proportion
FROM vw_playlist_track_facts
GROUP BY playlist_id,playlist_name, artist_id, artist_name;

GO
CREATE VIEW vw_tracks AS
SELECT
    p.playlist_id,
    p.playlist_name,
    t.track_id,
    t.track_name,
    a.artist_id,
    a.artist_name,
    n.nationality,
    p.playlist_type,
    CASE 
        WHEN n.country_code IN (
            'DZ','AO','BJ','BW','BF','BI','CM','CV','CF','TD','KM','CG','CD','CI','DJ','EG','GQ','ER','ET',
            'GA','GM','GH','GN','GW','KE','LS','LR','LY','MG','MW','ML','MR','MU','MA','MZ','NA','NE','NG',
            'RW','ST','SN','SC','SL','SO','ZA','SS','SD','TZ','TG','TN','UG','ZM','ZW'
        ) THEN 'African'
        ELSE 'non_African' 
    END AS is_african_nationality,
    g.genre_name
FROM vw_all_playlists p
JOIN playlist_tracks pt ON pt.playlist_id = p.playlist_id
JOIN tracks t ON t.track_id = pt.track_id
JOIN artist_tracks at ON at.track_id = t.track_id
JOIN artists a ON a.artist_id = at.artist_id
LEFT JOIN artist_nationalities an ON an.artist_id = a.artist_id
LEFT JOIN nationalities n ON n.nationality_id = an.nationality_id
LEFT JOIN tracks_genre tg ON tg.track_id = t.track_id
LEFT JOIN genres g ON g.genre_id = tg.genre_id
;


GO
CREATE VIEW vw_all_playlist_nationality_distribution AS
SELECT
    playlist_id,
    playlist_name,
    nationality,
    COUNT(*) AS track_count,
    playlist_type
FROM vw_tracks
where is_african_nationality= 'African'
GROUP BY playlist_id, nationality,playlist_name,playlist_type 
;



GO
CREATE VIEW vw_all_playlist_genre_distribution AS
With african_genres as (select genre_id,genre_name from genres where genre_name in
 (('afrobeats'),('afropop'),('afro r&b'),('afrobeat'),('afropiano'),('afro soul'),('afroswing'),
 ('azonto'),('alté'),('afro adura'),('ghanaian hip hop'),('amapiano'),
('gqom'),('rap'),('french r&b'),('pop urbaine'),('asakaa'),('hiplife'),('highlife'),
('gospel'),('bongo piano'),('private school piano'),('bacardi'),('3 step'),('ndombolo'),
('rumba congolaise'),('afro house'),('bikutsi'),('gnawa'),('kizomba'),('sufi'),('tribal house'),
('afro tech'),('ethiopian jazz'),('coupé décalé'),('traditional music'),('nigerian drill'),
('bongo flava'),('singeli'),('gengetone'),('gospel r&b'),('fújì'),('rap ivoire'),('kuduro'),
('african gospel'),('alternative r&b'),('maskandi'),('moroccan pop'),('raï'),('moroccan rap'),
('moroccan chaabi'),('mahraganat'),('christian alternative rock'),('lo-fi'),('lo-fi beats'),('gospel'),
'bongo','rumba congolaise','singeli','ndombolo','hiplife','nigerian drill','jazz'))
SELECT
    playlist_id,
    Playlist_name,
    ag.genre_name,
    COUNT(distinct(track_id)) AS track_count,
    CAST(COUNT(track_id) AS FLOAT)
      / SUM(COUNT(track_id)) OVER (PARTITION BY playlist_id) AS proportion,
      playlist_type
FROM vw_tracks a
join african_genres ag on ag.genre_name= a.genre_name
GROUP BY playlist_id,playlist_name, ag.genre_name,playlist_type;



GO
CREATE VIEW vw_all_playlist_artist_exposure AS
SELECT
    playlist_id,
    playlist_name,
    artist_id,
    artist_name,
    COUNT(distinct(track_id)) AS track_count,
    CAST(COUNT(*) AS FLOAT)
      / SUM(COUNT(*)) OVER (PARTITION BY playlist_id) AS proportion,
      playlist_type
FROM vw_tracks
GROUP BY playlist_id,playlist_name, artist_id, artist_name,playlist_type;




