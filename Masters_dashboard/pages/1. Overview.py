import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import altair as alt
import pyodbc
import base64
from scipy.stats import chisquare
from scipy.spatial.distance import jensenshannon
import plotly.express as px
import itertools


# --------------------------------------------------
# Ensure project root is on path
# --------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))
CACHE_TTL = 60 * 60  # 1 hour (safe for overview metrics)


from db import get_connection

st.title("📊 Dataset Overview & Data Quality")

# --------------------------------------------------
# Helpers
# --------------------------------------------------
def run_query(query: str) -> pd.DataFrame:
    """Run a lightweight SQL query safely."""
    try:
        with get_connection() as conn:
            return pd.read_sql(query, conn)
    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()

def fmt(x):
    try:
        return f"{float(x):.2f}"
    except Exception:
        return "—"

# --------------------------------------------------
# 1️⃣ Core entity counts
# --------------------------------------------------
st.subheader("📦 Dataset Size")

counts_query = """
SELECT
    (SELECT COUNT(DISTINCT(artist_id)) FROM artists) AS artists,
    (SELECT COUNT(Distinct(track_id)) FROM tracks) AS tracks,
    (SELECT COUNT(distinct(playlist_id)) FROM playlists) AS playlists,
    (SELECT COUNT(distinct(album_name)) FROM albums) AS albums,
    (SELECT COUNT(distinct(genre_id)) FROM genres) AS genres,
    (SELECT COUNT(distinct(nationality_id)) FROM nationalities) AS nationalities
"""

counts_df = run_query(counts_query)

if not counts_df.empty:
    counts = counts_df.iloc[0]

    c1, c2, c3 = st.columns(3)
    c1.metric("Artists", int(counts["artists"]))
    c2.metric("Tracks", int(counts["tracks"]))
    c3.metric("Playlists", int(counts["playlists"]))

    c4, c5, c6 = st.columns(3)
    c4.metric("Albums", int(counts["albums"]))
    c5.metric("Genres", int(counts["genres"]))
    c6.metric("Nationalities", int(counts["nationalities"]))
else:
    st.warning("Unable to load dataset counts.")

# --------------------------------------------------
# 2️⃣ Relationship averages
# --------------------------------------------------
st.subheader("📈 Dataset Averages")

averages_query = """
SELECT
    (SELECT CAST(COUNT(*) AS FLOAT) / NULLIF((SELECT COUNT(*) FROM artists), 0)
        FROM artist_tracks) AS tracks_per_artist,

    (SELECT CAST(COUNT(*) AS FLOAT) / NULLIF((SELECT COUNT(*) FROM tracks), 0)
        FROM tracks_genre) AS genres_per_track,

    (SELECT CAST(COUNT(*) AS FLOAT) / NULLIF((SELECT COUNT(*) FROM playlists), 0)
        FROM playlist_tracks) AS tracks_per_playlist
"""

avg_df = run_query(averages_query)

if not avg_df.empty:
    avg = avg_df.iloc[0]

    a1, a2, a3 = st.columns(3)
    a1.metric("Avg tracks per artist", fmt(avg["tracks_per_artist"]))
    a2.metric("Avg genres per track", fmt(avg["genres_per_track"]))
    a3.metric("Avg tracks per playlist", fmt(avg["tracks_per_playlist"]))
else:
    st.warning("Unable to load dataset averages.")

# --------------------------------------------------
# 3️⃣ Data quality checks
# --------------------------------------------------
st.subheader("⚠️ Data Quality Indicators")

quality_query = """
SELECT
    (SELECT COUNT(*) FROM artists
        WHERE artist_name IS NULL OR LTRIM(RTRIM(artist_name)) = '') AS null_artist_names,

    (SELECT COUNT(*) FROM tracks
        WHERE track_name IS NULL OR LTRIM(RTRIM(track_name)) = '') AS null_track_names,

    (SELECT COUNT(*) FROM genres
        WHERE genre_name IS NULL OR LTRIM(RTRIM(genre_name)) = '') AS null_genre_names
"""

quality_df = run_query(quality_query)

if not quality_df.empty:
    q = quality_df.iloc[0]

    q1, q2, q3 = st.columns(3)
    q1.metric("Artists missing names", int(q["null_artist_names"]))
    q2.metric("Tracks missing titles", int(q["null_track_names"]))
    q3.metric("Genres missing labels", int(q["null_genre_names"]))
else:
    st.warning("Unable to load data quality indicators.")


@st.cache_data(show_spinner=True, ttl=CACHE_TTL)
def tracks_without_genre_annotation() -> int:
    query = """
    SELECT COUNT(DISTINCT tg.track_id) AS tracks_with_no_genre
    FROM tracks_genre tg
    JOIN genres g ON g.genre_id = tg.genre_id
    WHERE LOWER(LTRIM(RTRIM(g.genre_name))) = 'unknown'
    """
    df = run_query(query)
    return int(df.iloc[0, 0]) if not df.empty else 0


@st.cache_data(show_spinner=True, ttl=CACHE_TTL)
def artists_without_nationality_annotation() -> int:
    query = """
    SELECT COUNT(DISTINCT a.artist_id) AS artists_with_no_nationality
    FROM artists a
    LEFT JOIN artist_nationalities an
        ON an.artist_id = a.artist_id
    WHERE an.nationality_id IS NULL
    """
    df = run_query(query)
    return int(df.iloc[0, 0]) if not df.empty else 0


AFRICA_CODES = (
    "'DZ','AO','BJ','BW','BF','BI','CM','CV','CF','TD','KM','CG','CD','CI','DJ','EG','GQ','ER','ET',"
    "'GA','GM','GH','GN','GW','KE','LS','LR','LY','MG','MW','ML','MR','MU','MA','MZ','NAM','NE','NG',"
    "'RW','ST','SN','SC','SL','SO','ZA','SS','SD','TZ','TG','TN','UG','ZM','ZW'"
)

# --------------------------------------------------
# 1) Artists: African vs Non-African
# --------------------------------------------------
@st.cache_data(show_spinner=True, ttl=CACHE_TTL)
def get_artists_africa_split() -> dict:
    query = f"""
    WITH ArtistCategorization AS (
        SELECT
            an.artist_id,
            MAX(CASE WHEN n.country_code IN ({AFRICA_CODES}) THEN 1 ELSE 0 END) AS is_african,
            MAX(CASE WHEN n.country_code NOT IN ({AFRICA_CODES}) THEN 1 ELSE 0 END) AS is_non_african
        FROM artist_nationalities an
        JOIN nationalities n
            ON n.nationality_id = an.nationality_id
        GROUP BY an.artist_id
    )
    SELECT
        SUM(CASE WHEN is_african = 1 AND is_non_african = 0 THEN 1 ELSE 0 END) AS pure_african_artists,
        SUM(CASE WHEN is_african = 1 AND is_non_african = 1 THEN 1 ELSE 0 END) AS mixed_african_artists,
        SUM(CASE WHEN is_african = 0 AND is_non_african = 1 THEN 1 ELSE 0 END) AS pure_non_african_artists,
        SUM(is_african) AS african_artists_including_mixed
    FROM ArtistCategorization;
    """
    df = run_query(query)
    return df.iloc[0].to_dict()


# 1.1) Artists: African vs Non-African visualization

st.subheader("👩🏾‍🎤 Artists: Total vs African")
try:
    split = get_artists_africa_split()
    pure_african_artists = int(split.get("pure_african_artists", 0) or 0)
    mixed_african_artist = int(split.get("mixed_african_artists", 0) or 0)
    non_african_artists = int(split.get("pure_non_african_artists", 0) or 0)
    total_artists = pure_african_artists + mixed_african_artist + non_african_artists

    kcols = st.columns(3)
    kcols[0].metric("pure_african_artists", pure_african_artists)
    kcols[1].metric("mixed_african_artist", mixed_african_artist)
    kcols[2].metric("non_african_artists", non_african_artists)

    pie_df = pd.DataFrame({
        "category": ["pure_african_artists", "mixed_african_artist", "non_african_artists"],
        "count": [pure_african_artists, mixed_african_artist, non_african_artists],
    })
    pie = alt.Chart(pie_df).mark_arc(innerRadius=60).encode(
        theta=alt.Theta("count:Q", title="Count"),
        color=alt.Color("category:N", title="Category",
                        scale=alt.Scale(range=["#2ecc71", "#e74c3c", "#95a5a6"])),
        tooltip=["category", "count"]
    ).properties(height=260)
    st.altair_chart(pie, width='stretch')
except Exception as e:
    st.error("Failed to load African artist split data.")
    st.exception(e)

# --------------------------------------------------
# 2) African countries distribution
# --------------------------------------------------

@st.cache_data(show_spinner=True, ttl=CACHE_TTL)
def get_african_country_distribution() -> pd.DataFrame:
    query = f"""
    SELECT TOP 10
        n.country_name,
        COUNT(DISTINCT a.artist_id) AS artists
    FROM artists a
    JOIN artist_nationalities an ON an.artist_id = a.artist_id
    JOIN nationalities n ON n.nationality_id = an.nationality_id
    WHERE n.country_code IN ({AFRICA_CODES})
    GROUP BY n.country_name
    ORDER BY artists DESC;
    """
    return run_query(query)

# ----------------------------
# 2.1) Country distribution among African artists (Top 10)
# ----------------------------
st.subheader("🌐 Top 10 Countries with most Artists in Playlist ")
try:
    dist = get_african_country_distribution()
    if dist.empty:
        st.info("No African artist country data found.")
    else:
        # st.dataframe(dist, use_container_width=True)
        bar = alt.Chart(dist).mark_bar(color="#db7a34").encode(
            x=alt.X("artists:Q", title="Artists"),
            y=alt.Y("country_name:N", sort="-x", title="Country"),
            tooltip=["country_name", "artists"]
        ).properties(height=max(400, 24 * len(dist)))
        st.altair_chart(bar, width='stretch')
except Exception as e:
    st.error(f"Error fetching African country distribution: {e}")



# --------------------------------------------------
# 3) Playlists with African tracks presence
# --------------------------------------------------
@st.cache_data(show_spinner=True, ttl=CACHE_TTL)
def get_playlists_african_presence() -> dict:
    query = f"""
    WITH african_artists AS (
        SELECT DISTINCT an.artist_id
        FROM artist_nationalities an
        JOIN nationalities n
            ON n.nationality_id = an.nationality_id
        WHERE n.country_code IN ({AFRICA_CODES})
    ),
    african_tracks AS (
        SELECT DISTINCT at.track_id
        FROM artist_tracks at
        JOIN african_artists aa
            ON aa.artist_id = at.artist_id
    )
    SELECT
        COUNT(DISTINCT p.playlist_id) AS total_playlists,
        COUNT(DISTINCT CASE WHEN at.track_id IS NOT NULL THEN p.playlist_id END)
            AS playlists_with_african_tracks
    FROM playlists p
    LEFT JOIN playlist_tracks pt ON pt.playlist_id = p.playlist_id
    LEFT JOIN african_tracks at ON at.track_id = pt.track_id;
    """
    df = run_query(query)
    return df.iloc[0].to_dict()


# 3.1) Playlists with African tracks presence visualization
st.subheader("🎧 Playlists with African Tracks (Share)")
try:
    pl_share = get_playlists_african_presence()
    total_playlists = int(pl_share.get("total_playlists", 0) or 0)
    pl_with_africa = int(pl_share.get("playlists_with_african_tracks", 0) or 0)
    pct = (pl_with_africa / total_playlists * 100) if total_playlists else 0.0

    cols = st.columns(3)
    cols[0].metric("Total playlists", total_playlists)
    cols[1].metric("Playlists w/ African tracks", pl_with_africa)
    cols[2].metric("Share (%)", f"{pct:.2f}")

    donut_df = pd.DataFrame({
        "category": ["With African tracks", "Without African tracks"],
        "count": [pl_with_africa, total_playlists - pl_with_africa],
    })
    donut = alt.Chart(donut_df).mark_arc(innerRadius=60).encode(
        theta=alt.Theta("count:Q", title="Playlists"),
        color=alt.Color("category:N", title="Category",
                        scale=alt.Scale(range=["#9b59b6", "#bdc3c7"])),
        tooltip=["category", "count"]
    ).properties(height=260)
    st.altair_chart(donut, width='stretch')
except Exception as e:
    st.error(f"Error fetching playlists African presence: {e}")

# --------------------------------------------------
# cross nationality collaborations
# --------------------------------------------------
@st.cache_data(show_spinner=True, ttl=CACHE_TTL)
def load_data():
    query = "SELECT * FROM vw_playlist_track_facts"
    return run_query(query)


df_collaboration = load_data()


def plot_cross_nationality_collaboration(df):
    st.subheader("🤝 Cross-Nationality Collaboration Rate")

    required_cols = {"track_id", "nationality"}
    missing = required_cols - set(df.columns)

    if missing:
        st.error(f"Data missing required columns: {missing}")
        return

    collab_flag = (
        df.dropna(subset=["track_id", "nationality"])
          .groupby("track_id")["nationality"]
          .nunique()
          .reset_index(name="n_nationalities")
    )

    collab_flag["collaboration"] = collab_flag["n_nationalities"].apply(
        lambda x: "Cross-national" if x > 1 else "Single-national"
    )

    chart = (
        alt.Chart(collab_flag)
        .mark_bar()
        .encode(
            x=alt.X("collaboration:N", title="Track Type"),
            y=alt.Y("count():Q", title="Number of Tracks"),
            tooltip=["collaboration", "count()"]
        )
    )

    st.altair_chart(chart, width="stretch")

plot_cross_nationality_collaboration(df_collaboration)

# --------------------------------------------------
#Release dates of tracks in the playlists
#--------------------------------------------------

@st.cache_data(show_spinner=True, ttl=CACHE_TTL)
def get_tracks_by_year() -> pd.DataFrame:
    query = """
    SELECT YEAR(release_date) AS year, COUNT(*) AS tracks
    FROM tracks
    WHERE release_date IS NOT NULL
    GROUP BY YEAR(release_date)
    ORDER BY YEAR(release_date);
    """
    return run_query(query)


@st.cache_data(show_spinner=True, ttl=CACHE_TTL)
def get_african_tracks_by_year() -> pd.DataFrame:
    query = f"""
    WITH african_tracks AS (
        SELECT DISTINCT at.track_id
        FROM artist_tracks at
        JOIN artist_nationalities an ON an.artist_id = at.artist_id
        JOIN nationalities n ON n.nationality_id = an.nationality_id
        WHERE n.country_code IN ({AFRICA_CODES})
    )
    SELECT YEAR(t.release_date) AS year, COUNT(*) AS african_tracks
    FROM tracks t
    WHERE t.track_id IN (SELECT track_id FROM african_tracks)
      AND t.release_date IS NOT NULL
    GROUP BY YEAR(t.release_date)
    ORDER BY YEAR(t.release_date);
    """
    return run_query(query)

# 4.1) Tracks by Year visualization

st.subheader("🗓️ Tracks by Year (Overall vs African)")
try:
    overall_year = get_tracks_by_year()
    african_year = get_african_tracks_by_year()

    # Merge datasets
    merged = pd.merge(
        overall_year.rename(columns={"tracks": "overall_tracks"}),
        african_year.rename(columns={"african_tracks": "african_tracks"}),
        on="year",
        how="outer"
    ).sort_values("year")

    # Ensure numeric year and remove NaNs
    merged['year'] = pd.to_numeric(merged['year'], errors='coerce')
    merged = merged.dropna(subset=['year'])

    # Only include years >= 1960
    merged = merged[merged['year'] >= 1960]

    if merged.empty:
        st.info("No data to display")
    else:
        # Convert to long-form for Altair
        long_df = merged.melt(id_vars="year", value_vars=["overall_tracks", "african_tracks"],
                              var_name="Track_Type", value_name="Tracks")

        # Map colors for clarity
        color_scale = alt.Scale(domain=["overall_tracks", "african_tracks"],
                                range=["#2980b9", "#27ae60"])

        # Create line chart with legend
        line_chart = alt.Chart(long_df).mark_line(point=True).encode(
            x=alt.X("year:Q", title="Year"),
            y=alt.Y("Tracks:Q", title="Number of Tracks"),
            color=alt.Color("Track_Type:N", scale=color_scale, title="Track Type"),
            tooltip=["year", "Track_Type", "Tracks"]
        ).properties(height=300)

        st.altair_chart(line_chart, width='stretch')
except Exception as e:
    st.error(f"Error fetching tracks by year: {e}")

# --------------------------------------------------
# Artist popularity by playlist
#--------------------------------------------------
st.subheader("🏆 Top 20 Artists by Playlist Presence")

@st.cache_data(show_spinner=True)
def get_artist_popularity_top20():
    query = """
    SELECT TOP 20
      a.artist_name,
      COUNT(DISTINCT p.playlist_id) AS playlists_with_artist,
      nationality
    FROM artists a
    LEFT JOIN artist_tracks at ON at.artist_id = a.artist_id
    LEFT JOIN playlist_tracks pt ON pt.track_id = at.track_id
    LEFT JOIN playlists p ON p.playlist_id = pt.playlist_id
    LEFT JOIN Artist_Nationalities an ON an.artist_id = a.artist_id
    LEFT JOIN Nationalities N ON N.NATIONALITY_ID = an.NATIONALITY_ID
    GROUP BY a.artist_id, a.artist_name, nationality
    ORDER BY playlists_with_artist DESC;
    """
    conn = get_connection()
    return pd.read_sql(query, conn)

# 5.1) Artist popularity visualization
try:
    pop = get_artist_popularity_top20()
    st.dataframe(pop, width='stretch')

    barh = alt.Chart(pop).mark_bar(color="#16a085").encode(
        x=alt.X("playlists_with_artist:Q", title="Playlists with artist"),
        y=alt.Y("artist_name:N", sort="-x", title="Artist"),
        color=alt.Color("nationality:N", title="Nationality", legend=alt.Legend(columns=1)),
        tooltip=["artist_name", "playlists_with_artist", "nationality"]
    ).properties(height=max(260, 20 * len(pop)))
    st.altair_chart(barh, width='stretch')

    # Quick insight
    if not pop.empty:
        top_row = pop.iloc[0]
        st.caption(f"Top artist: **{top_row['artist_name']}** in **{int(top_row['playlists_with_artist'])}** playlists ({top_row['nationality']}).")
except Exception as e:
    st.error(f"Error fetching artist popularity: {e}")


# --------------------------------------------------
# Tracks per Genre (Top 20 African Genres)
# --------------------------------------------------
@st.cache_data(show_spinner=True)
def tracks_per_genre():
    query ="""With african_genres as (select genre_id,genre_name from genres where genre_name in (('afrobeats'),('afropop'),('afro r&b'),('afrobeat'),('afropiano'),('afro soul'),('afroswing'),('azonto'),('alté'),('afro adura'),('ghanaian hip hop'),('amapiano'),
('gqom'),('rap'),('french r&b'),('pop urbaine'),('asakaa'),('hiplife'),('highlife'),('gospel'),('bongo piano'),('private school piano'),('bacardi'),('3 step'),('ndombolo'),('rumba congolaise'),
('afro house'),('bikutsi'),('gnawa'),('kizomba'),('sufi'),('tribal house'),('afro tech'),('ethiopian jazz'),('coupé décalé'),('traditional music'),('nigerian drill'),('bongo flava'),('singeli'),('gengetone'),('gospel r&b'),
('fújì'),('rap ivoire'),('kuduro'),('african gospel'),('alternative r&b'),('maskandi'),('moroccan pop'),('raï'),('moroccan rap'),('moroccan chaabi'),('mahraganat'),('christian alternative rock'),('lo-fi'),('lo-fi beats'),('gospel'),'bongo','rumba congolaise','singeli',
'ndombolo','hiplife'))
select top 20 count(t.track_id) no_of_tracks,genre_name from tracks_genre tg 
join african_genres ag on tg.genre_id=ag.genre_id 
join tracks t on t.track_id= tg.track_id
group by genre_name
order by count(t.track_id) desc;
"""
    conn = get_connection()
    return pd.read_sql(query, conn)

# 6.1) Tracks per Genre visualization
st.subheader("🎶 Tracks per Genre (Top 20 African Genres)")
try:
    tpg = tracks_per_genre()
    # st.dataframe(tpg, use_container_width=True)

    barh = alt.Chart(tpg).mark_bar(color="#8e44ad").encode(
        x=alt.X("no_of_tracks:Q", title="Number of Tracks"),
        y=alt.Y("genre_name:N", sort="-x", title="Genre"),
        tooltip=["genre_name", "no_of_tracks"]
    ).properties(height=max(400, 26 * len(tpg)))
    st.altair_chart(barh, width='stretch')

    # Quick insight
    if not tpg.empty:
        top_row = tpg.iloc[0]
        st.caption(f"Top genre: **{top_row['genre_name']}** with **{int(top_row['no_of_tracks'])}** tracks.")
except Exception as e:
    st.error(f"Error fetching tracks per genre: {e}")   

# --------------------------------------------------
# Tracks per Genre Distribution
# --------------------------------------------------
@st.cache_data(show_spinner=True)
def genres_per_track_distribution():
    query = """
WITH counts AS (
  SELECT t.track_id, COUNT(tg.genre_id) AS genre_count
  FROM tracks t
  LEFT JOIN tracks_genre tg ON tg.track_id = t.track_id
  GROUP BY t.track_id
)
SELECT genre_count, COUNT(*) AS tracks
FROM counts
GROUP BY genre_count
ORDER BY genre_count;
    """
    conn = get_connection()
    return pd.read_sql(query, conn)


# 7.1) Genres per Track Distribution visualization
st.subheader("🎵 Genres per Track Distribution")
try:
    gpt = genres_per_track_distribution()
    # st.dataframe(gpt, use_container_width=True)

    bar = alt.Chart(gpt).mark_bar(color="#d35400").encode(
        x=alt.X("genre_count:Q", title="Genres per Track",axis=alt.Axis(tickCount=20, format="d")),
        y=alt.Y("tracks:Q", title="Number of Tracks"),
        tooltip=["genre_count", "tracks"]
    ).properties(height=max(400, 26 * len(tpg)))
    st.altair_chart(bar, width='stretch')

    # Quick insight
    if not gpt.empty:
        max_row = gpt.loc[gpt['tracks'].idxmax()]
        st.caption(f"Most common genre count: **{int(max_row['genre_count'])}** genres for **{int(max_row['tracks'])}** tracks.")
except Exception as e:
    st.error(f"Error fetching genres per track distribution: {e}")

st.subheader("Count of Unique Genre Tags per Year")
st.markdown("""
This dashboard tracks the **number of unique genre tags** used in tracks over time. 
Use this to evaluate stylistic fragmentation and shifts in musical trends.
""")


@st.cache_data(show_spinner=True, ttl=CACHE_TTL)
def load_genre_data():
    query = "SELECT * FROM vw_playlist_genre_distribution"
    conn = get_connection()
    # It is safer to close the connection after reading
    df = pd.read_sql(query, conn)
    conn.close() 
    return df
    
try:
    df_genre = load_genre_data()
    
    # --- FIX 1: Ensure date conversion and extract Year ---
    df_genre['release_date'] = pd.to_datetime(df_genre['release_date'])
    df_genre['year'] = df_genre['release_date'].dt.year

    # --- FIX 2: Group by Year, not the full date ---
    genre_diversity = df_genre.groupby('year')['genre_name'].nunique().reset_index()
    genre_diversity.columns = ['Year', 'Unique Genre Count']

    # 4. Visualization - Bar Chart

    
    fig_bar = px.bar(
        genre_diversity, 
        x='Year', 
        y='Unique Genre Count',
        text='Unique Genre Count',
        labels={'Unique Genre Count': 'Number of Unique Genres'},
        template="plotly_white",
        color_discrete_sequence=['#636EFA']
    )
    fig_bar.update_traces(textposition='outside')
    # Use 'category' so the x-axis doesn't treat years like continuous numbers
    fig_bar.update_xaxes(type='category', title="Release Year") 
    
    st.plotly_chart(fig_bar, width='stretch')

    # 5. Comparative Table
    col1, = st.columns(1) 

    with col1:
        # --- FIX 2: Dynamic Header ---
        # Using an f-string makes the UI more informative by showing the actual year.
        latest_year = int(df_genre['year'].max())
        st.write(f"### Top 5 Genres in {latest_year}")
        
        # --- FIX 3: Data Selection Logic ---
        # We filter the dataframe for the latest year and get the top 5 most frequent genres.
        top_genres = (
            df_genre[df_genre['year'] == latest_year]['genre_name']
            .value_counts()
            .head(5)
            .reset_index()
        )
        
        # Rename columns for a professional display
        top_genres.columns = ['Genre Name', 'Total Tracks']
        
        # --- FIX 4: Table Display ---
        # st.table is great for static displays; st.dataframe is better if you want it sortable.
        st.table(top_genres)

except Exception as e:
    st.error(f"Error processing genre data: {e}")
    # Printing the error to the terminal is helpful for deep debugging
    import traceback
    print(traceback.format_exc())
    st.info("Example data format: release_date (YYYY-MM-DD), genre_name (Text)")

# --------------------------------------------------
# Interpretation (important for dissertation)
# --------------------------------------------------
with st.expander("ℹ️ How to interpret this page"):
    st.markdown("""
This page provides an overview of the **scale**, **structure**, and **annotation quality**
of the Spotify dataset used in this study.

- The *dataset size* metrics describe the breadth of artists, tracks, playlists, and genres analysed.
- The *average relationships* indicate how densely connected entities are
  (e.g., how many tracks an artist typically has).
- The *data quality indicators* highlight potential sources of bias or noise
  arising from missing metadata.

These diagnostics ensure that subsequent bias and concentration analyses
are interpreted within the context of the dataset’s completeness and limitations.
""")
