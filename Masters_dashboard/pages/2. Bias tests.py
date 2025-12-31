import pandas as pd
import numpy as np
import streamlit as st
from db import get_connection
import altair as alt
from scipy.stats import chi2_contingency

st.title("📊 Bias tests within User Curated Playlists")
st.subheader("Concentration Ratios")

# import playlist_nationality_distribution view
@st.cache_data(show_spinner=True)
def load_playlist_nationality():
    query = "SELECT * FROM vw_playlist_nationality_distribution"
    conn = get_connection()
    return pd.read_sql(query, conn)

df_nat = load_playlist_nationality()

# import playlist_genre_distribution view
@st.cache_data(show_spinner=True)
def load_genre_data():
    query = "SELECT * FROM vw_playlist_genre_distribution"
    conn = get_connection()
    return pd.read_sql(query, conn)

df_genre = load_genre_data()


#import playlist_artist_exposure view
@st.cache_data(show_spinner=True)
def load_artist_data():
    query = "SELECT * FROM vw_playlist_artist_exposure"
    conn = get_connection()
    return pd.read_sql(query, conn)
df_artist = load_artist_data()


# ======================================================
# IMPORTS
# ======================================================
import pandas as pd
import altair as alt
import streamlit as st


# ======================================================
# 1️⃣ GENERIC CONCENTRATION RATIO FUNCTION (CRk)
# ======================================================

def compute_crk(group, count_col="track_count", k=10):
    total = group[count_col].sum()
    if total == 0:
        return 0.0

    return (
        group.sort_values(count_col, ascending=False)
             .head(k)[count_col]
             .sum() / total
    )


# ======================================================
# 2️⃣ GENERIC CR10 PIPELINE (USED FOR ALL CATEGORIES)
# ======================================================

def compute_cr10_pipeline(
    df,
    category_col,
    playlist_id_col,
    playlist_name_col,
    count_col="track_count",
    k=10
):
    df = df.copy()

    # Sort once
    df = df.sort_values(
        [playlist_id_col, count_col],
        ascending=[True, False]
    )

    # Rank categories within playlist
    df["rank"] = (
        df.groupby(playlist_id_col)[count_col]
          .rank(method="first", ascending=False)
    )

    # Total tracks per playlist
    playlist_totals = (
        df.groupby([playlist_id_col, playlist_name_col])[count_col]
          .sum()
          .reset_index(name="total_tracks")
    )

    # Top-10 categories per playlist
    top10_totals = (
        df[df["rank"] <= k]
        .groupby([playlist_id_col, playlist_name_col])[count_col]
        .sum()
        .reset_index(name="top10_tracks")
    )

    # Merge + compute observed CR10
    cr10_obs = playlist_totals.merge(
        top10_totals,
        on=[playlist_id_col, playlist_name_col],
        how="left"
    ).fillna({"top10_tracks": 0})

    cr10_obs["CR10_observed"] = (
        cr10_obs["top10_tracks"] / cr10_obs["total_tracks"]
    )

    # Expected baseline CR10
    baseline = (
        df.groupby(category_col, as_index=False)[count_col]
          .sum()
    )

    CR10_expected = compute_crk(baseline, count_col=count_col, k=k)

    cr10_obs["CR10_expected"] = CR10_expected
    cr10_obs["CR10_delta"] = cr10_obs["CR10_observed"] - CR10_expected
    cr10_obs["CR10_ratio"] = cr10_obs["CR10_observed"] / CR10_expected

    return cr10_obs, CR10_expected


# ======================================================
# 3️⃣ HELPER: TOP-10 SHARE BAR CHART
# ======================================================

def plot_top10_bar(df, category_col, title):
    top10 = (
        df.groupby(category_col, as_index=False)["track_count"]
          .sum()
          .sort_values("track_count", ascending=False)
          .head(10)
    )

    top10["share"] = (
        top10["track_count"] / top10["track_count"].sum()
    )

    chart = (
        alt.Chart(top10)
        .mark_bar()
        .encode(
            x=alt.X(f"{category_col}:N", sort="-y", title=category_col.replace("_", " ").title()),
            y=alt.Y("share:Q", title="Share of Tracks (Top 10)", axis=alt.Axis(format="%")),
            tooltip=[
                category_col,
                alt.Tooltip("share:Q", format=".1%")
            ]
        )
        .properties(height=400, title=title)
    )

    st.altair_chart(chart, width="stretch")


# ======================================================
# 4️⃣ NATIONALITY CR10
# ======================================================

cr10_nat, CR10_nat_expected = compute_cr10_pipeline(
    df_nat,
    category_col="nationality",
    playlist_id_col="playlist_id",
    playlist_name_col="playlist_name"
)

st.subheader("🎧 Cultural Dominance — Top 10 Nationalities")

cols = st.columns(4)
cols[0].metric("Mean CR10 (Observed)", f"{cr10_nat.CR10_observed.mean():.2%}")
cols[1].metric("CR10 (Expected)", f"{CR10_nat_expected:.2%}")
cols[2].metric("Δ CR10", f"{cr10_nat.CR10_delta.mean():.2%}")
cols[3].metric("CR10 Ratio", f"{cr10_nat.CR10_ratio.mean():.2f}×")

playlist_options = ["All playlists"] + sorted(
    df_nat["playlist_name"].dropna().unique()
)

selected_playlist = st.selectbox(
    "Select playlist to explore nationality dominance",
    playlist_options,
    key="nat_playlist_selector"
)

# Filter data for chart
plot_df = (
    df_nat.copy()
    if selected_playlist == "All playlists"
    else df_nat[df_nat["playlist_name"] == selected_playlist]
)

# --------------------------------------------------
# TOP-10 NATIONALITIES FOR SELECTED VIEW
# --------------------------------------------------

top10_nat_df = (
    plot_df
    .groupby("nationality", as_index=False)["track_count"]
    .sum()
    .sort_values("track_count", ascending=False)
    .head(10)
)

total_tracks = top10_nat_df["track_count"].sum()
top10_nat_df["share"] = top10_nat_df["track_count"] / total_tracks

# --------------------------------------------------
# INTERACTIVE BAR CHART
# --------------------------------------------------

chart = (
    alt.Chart(top10_nat_df)
    .mark_bar()
    .encode(
        x=alt.X(
            "nationality:N",
            sort="-y",
            title="Nationality"
        ),
        y=alt.Y(
            "share:Q",
            title="Share of Tracks (Top 10)",
            axis=alt.Axis(format="%")
        ),
        tooltip=[
            "nationality",
            alt.Tooltip("share:Q", format=".1%")
        ]
    )
    .properties(
        height=420,
        title=(
            "Top 10 Nationalities — All Playlists"
            if selected_playlist == "All playlists"
            else f"Top 10 Nationalities — {selected_playlist}"
        )
    )
)

st.altair_chart(chart, width="stretch")

display_nat = cr10_nat.copy()
display_nat[["CR10_observed", "CR10_expected", "CR10_delta"]] *= 100
display_nat = display_nat.round(2)

st.dataframe(
    display_nat.rename(columns={
        "playlist_name": "Playlist",
        "CR10_observed": "CR10 Observed (%)",
        "CR10_expected": "CR10 Expected (%)",
        "CR10_delta": "Δ CR10 (pp)",
        "CR10_ratio": "CR10 Ratio"
    }),
    width="stretch"
)


# ======================================================
# 5️⃣ GENRE CR10 (IDENTICAL STRUCTURE)
# ======================================================
# ======================================================
# GENRE CR10 (ALREADY COMPUTED)
# ======================================================

cr10_genre, CR10_genre_expected = compute_cr10_pipeline(
    df_genre,
    category_col="genre_name",
    playlist_id_col="playlist_id",
    playlist_name_col="Playlist_name"
)

st.subheader("🎶 Cultural Dominance — Top 10 Genres")

# --------------------------------------------------
# GLOBAL CR10 KPIs (UNCHANGED)
# --------------------------------------------------

cols = st.columns(4)
cols[0].metric("Mean CR10 (Observed)", f"{cr10_genre.CR10_observed.mean():.2%}")
cols[1].metric("CR10 (Expected)", f"{CR10_genre_expected:.2%}")
cols[2].metric("Δ CR10", f"{cr10_genre.CR10_delta.mean():.2%}")
cols[3].metric("CR10 Ratio", f"{cr10_genre.CR10_ratio.mean():.2f}×")

# --------------------------------------------------
# PLAYLIST SELECTOR FOR GENRE BAR CHART
# --------------------------------------------------

playlist_options = ["All playlists"] + sorted(
    df_genre["Playlist_name"].dropna().unique()
)

selected_playlist = st.selectbox(
    "Select playlist to explore genre dominance",
    playlist_options,
    key="genre_playlist_selector"
)

# Filter data for chart
plot_df = (
    df_genre.copy()
    if selected_playlist == "All playlists"
    else df_genre[df_genre["Playlist_name"] == selected_playlist]
)

# --------------------------------------------------
# TOP-10 GENRES FOR SELECTED VIEW
# --------------------------------------------------

top10_genre_df = (
    plot_df
    .groupby("genre_name", as_index=False)["track_count"]
    .sum()
    .sort_values("track_count", ascending=False)
    .head(10)
)

total_tracks = top10_genre_df["track_count"].sum()
top10_genre_df["share"] = top10_genre_df["track_count"] / total_tracks

# --------------------------------------------------
# INTERACTIVE BAR CHART
# --------------------------------------------------

chart = (
    alt.Chart(top10_genre_df)
    .mark_bar()
    .encode(
        x=alt.X(
            "genre_name:N",
            sort="-y",
            title="Genre"
        ),
        y=alt.Y(
            "share:Q",
            title="Share of Tracks (Top 10)",
            axis=alt.Axis(format="%")
        ),
        tooltip=[
            "genre_name",
            alt.Tooltip("share:Q", format=".1%")
        ]
    )
    .properties(
        height=420,
        title=(
            "Top 10 Genres — All Playlists"
            if selected_playlist == "All playlists"
            else f"Top 10 Genres — {selected_playlist}"
        )
    )
)

st.altair_chart(chart, width="stretch")

# --------------------------------------------------
# CR10 TABLE (UNCHANGED)
# --------------------------------------------------

display_genre = cr10_genre.copy()
display_genre[["CR10_observed", "CR10_expected", "CR10_delta"]] *= 100
display_genre = display_genre.round(2)

st.dataframe(
    display_genre.rename(columns={
        "Playlist_name": "Playlist",
        "CR10_observed": "CR10 Observed (%)",
        "CR10_expected": "CR10 Expected (%)",
        "CR10_delta": "Δ CR10 (pp)",
        "CR10_ratio": "CR10 Ratio"
    }),
    width="stretch"
)

# cr10_genre, CR10_genre_expected = compute_cr10_pipeline(
#     df_genre,
#     category_col="genre_name",
#     playlist_id_col="playlist_id",
#     playlist_name_col="Playlist_name"
# )

# st.subheader("🎶 Cultural Dominance — Top 10 Genres")

# cols = st.columns(4)
# cols[0].metric("Mean CR10 (Observed)", f"{cr10_genre.CR10_observed.mean():.2%}")
# cols[1].metric("CR10 (Expected)", f"{CR10_genre_expected:.2%}")
# cols[2].metric("Δ CR10", f"{cr10_genre.CR10_delta.mean():.2%}")
# cols[3].metric("CR10 Ratio", f"{cr10_genre.CR10_ratio.mean():.2f}×")

# plot_top10_bar(df_genre, "genre_name", "Top 10 Genres by Track Share")

# display_genre = cr10_genre.copy()
# display_genre[["CR10_observed", "CR10_expected", "CR10_delta"]] *= 100
# display_genre = display_genre.round(2)

# st.dataframe(
#     display_genre.rename(columns={
#         "Playlist_name": "Playlist",
#         "CR10_observed": "CR10 Observed (%)",
#         "CR10_expected": "CR10 Expected (%)",
#         "CR10_delta": "Δ CR10 (pp)",
#         "CR10_ratio": "CR10 Ratio"
#     }),
#     width="stretch"
# )


# ======================================================
# 6️⃣ ARTIST CR10 (IDENTICAL STRUCTURE)
# ======================================================
# ======================================================
# ARTIST CR10 (ALREADY COMPUTED)
# ======================================================

cr10_artist, CR10_artist_expected = compute_cr10_pipeline(
    df_artist,
    category_col="artist_name",
    playlist_id_col="playlist_id",
    playlist_name_col="playlist_name"
)

st.subheader("👩🏾‍🎤 Cultural Dominance — Top 10 Artists")

# --------------------------------------------------
# GLOBAL CR10 KPIs (UNCHANGED)
# --------------------------------------------------

cols = st.columns(4)
cols[0].metric("Mean CR10 (Observed)", f"{cr10_artist.CR10_observed.mean():.2%}")
cols[1].metric("CR10 (Expected)", f"{CR10_artist_expected:.2%}")
cols[2].metric("Δ CR10", f"{cr10_artist.CR10_delta.mean():.2%}")
cols[3].metric("CR10 Ratio", f"{cr10_artist.CR10_ratio.mean():.2f}×")

# --------------------------------------------------
# PLAYLIST SELECTOR FOR ARTIST BAR CHART
# --------------------------------------------------

playlist_options = ["All playlists"] + sorted(
    df_artist["playlist_name"].dropna().unique()
)

selected_playlist = st.selectbox(
    "Select playlist to explore artist dominance",
    playlist_options,
    key="artist_playlist_selector"
)

# Filter data for chart
plot_df = (
    df_artist.copy()
    if selected_playlist == "All playlists"
    else df_artist[df_artist["playlist_name"] == selected_playlist]
)

# --------------------------------------------------
# TOP-10 ARTISTS FOR SELECTED VIEW
# --------------------------------------------------

top10_artist_df = (
    plot_df
    .groupby("artist_name", as_index=False)["track_count"]
    .sum()
    .sort_values("track_count", ascending=False)
    .head(10)
)

total_tracks = top10_artist_df["track_count"].sum()
top10_artist_df["share"] = top10_artist_df["track_count"] / total_tracks

# --------------------------------------------------
# INTERACTIVE BAR CHART
# --------------------------------------------------

chart = (
    alt.Chart(top10_artist_df)
    .mark_bar()
    .encode(
        x=alt.X(
            "artist_name:N",
            sort="-y",
            title="Artist"
        ),
        y=alt.Y(
            "share:Q",
            title="Share of Tracks (Top 10)",
            axis=alt.Axis(format="%")
        ),
        tooltip=[
            "artist_name",
            alt.Tooltip("share:Q", format=".1%")
        ]
    )
    .properties(
        height=420,
        title=(
            "Top 10 Artists — All Playlists"
            if selected_playlist == "All playlists"
            else f"Top 10 Artists — {selected_playlist}"
        )
    )
)

st.altair_chart(chart, width="stretch")

# --------------------------------------------------
# CR10 TABLE (UNCHANGED)
# --------------------------------------------------

display_artist = cr10_artist.copy()
display_artist[["CR10_observed", "CR10_expected", "CR10_delta"]] *= 100
display_artist = display_artist.round(2)

st.dataframe(
    display_artist.rename(columns={
        "playlist_name": "Playlist",
        "CR10_observed": "CR10 Observed (%)",
        "CR10_expected": "CR10 Expected (%)",
        "CR10_delta": "Δ CR10 (pp)",
        "CR10_ratio": "CR10 Ratio"
    }),
    width="stretch"
)

# cr10_artist, CR10_artist_expected = compute_cr10_pipeline(
#     df_artist,
#     category_col="artist_name",
#     playlist_id_col="playlist_id",   # artist table uses playlist_name only
#     playlist_name_col="playlist_name"
# )

# st.subheader("👩🏾‍🎤 Cultural Dominance — Top 10 Artists")

# cols = st.columns(4)
# cols[0].metric("Mean CR10 (Observed)", f"{cr10_artist.CR10_observed.mean():.2%}")
# cols[1].metric("CR10 (Expected)", f"{CR10_artist_expected:.2%}")
# cols[2].metric("Δ CR10", f"{cr10_artist.CR10_delta.mean():.2%}")
# cols[3].metric("CR10 Ratio", f"{cr10_artist.CR10_ratio.mean():.2f}×")

# plot_top10_bar(df_artist, "artist_name", "Top 10 Artists by Track Share")

# display_artist = cr10_artist.copy()
# display_artist[["CR10_observed", "CR10_expected", "CR10_delta"]] *= 100
# display_artist = display_artist.round(2)

# st.dataframe(
#     display_artist.rename(columns={
#         "playlist_name": "Playlist",
#         "CR10_observed": "CR10 Observed (%)",
#         "CR10_expected": "CR10 Expected (%)",
#         "CR10_delta": "Δ CR10 (pp)",
#         "CR10_ratio": "CR10 Ratio"
#     }),
#     width="stretch"
# )


# ======================================================
# GINI COEFFICIENT (ROBUST & CORRECT)
# ======================================================

def gini_coefficient(values: pd.Series) -> float:
    """
    Compute the Gini coefficient for a non-negative distribution.
    Returns a value between 0 (perfect equality) and 1 (perfect inequality).
    """
    x = values.astype(float).values

    # Remove negative values (safety)
    x = x[x >= 0]

    # Handle empty or zero-sum cases
    if x.size == 0 or np.isclose(x.sum(), 0):
        return 0.0

    # Sort ascending
    x = np.sort(x)

    n = x.size
    cumx = np.cumsum(x)

    # Closed-form Gini (Lorenz curve formulation)
    gini = (n + 1 - 2 * np.sum(cumx) / cumx[-1]) / n
    return gini


# ======================================================
# BASELINE (CATALOGUE-LEVEL) GINI
# ======================================================

# ---------- NATIONALITY ----------
nationality_dist = (
    df_nat
    .groupby("nationality")["track_count"]
    .sum()
)

gini_nationality = gini_coefficient(nationality_dist)


# ---------- GENRE ----------
genre_dist_raw = (
    df_genre
    .groupby("genre_name")["track_count"]
    .sum()
)

gini_genre = gini_coefficient(genre_dist_raw)


# ---------- ARTIST ----------
artist_dist = (
    df_artist
    .groupby("artist_name")["track_count"]
    .sum()
)

gini_artist = gini_coefficient(artist_dist)


# ======================================================
# PLAYLIST-LEVEL GINI (NATIONALITIES)
# ======================================================

playlist_gini_nat = (
    df_nat
    .groupby("playlist_name")
    .apply(lambda g: gini_coefficient(g["track_count"]))
    .reset_index(name="gini_nationality")
)


# ======================================================
# PLAYLIST-LEVEL GINI (genres)
# ======================================================
playlist_gini_genre = (
    df_genre
    .groupby("Playlist_name")
    .apply(lambda g: gini_coefficient(g["track_count"]))
    .reset_index(name="gini_genre")
)
# ======================================================
# PLAYLIST-LEVEL GINI (artists)
# ======================================================
playlist_gini_artists = (
    df_artist
    .groupby("playlist_name")
    .apply(lambda g: gini_coefficient(g["track_count"]))
    .reset_index(name="gini_artist")
)

# ======================================================
# STREAMLIT OUTPUT
# ======================================================

st.subheader("📐 Inequality Metrics (Gini Coefficient)")

g1, g2, g3 = st.columns(3)
g1.metric("Nationality Gini", f"{gini_nationality:.3f}")
g2.metric("Genre Gini", f"{gini_genre:.3f}")
g3.metric("Artist Gini", f"{gini_artist:.3f}")

st.subheader("📊 Playlist-level Nationality Inequality")

playlist_gini_display = playlist_gini_nat.copy()
playlist_gini_display["gini_nationality"] = playlist_gini_display["gini_nationality"].round(3)

st.dataframe(
    playlist_gini_display.rename(columns={
        "playlist_name": "Playlist",
        "gini_nationality": "Nationality Gini"
    }),
    width="stretch"
)

st.subheader("playlist-level genre Inequality")
playlist_gini_display = playlist_gini_genre.copy()
playlist_gini_display["gini_genre"] = playlist_gini_display["gini_genre"].round(3)  
st.dataframe(
    playlist_gini_display.rename(columns={
        "Playlist_name": "Playlist",
        "gini_genre": "Genre Gini"
    }),
    width="stretch"
)
st.subheader("playlist-level artist Inequality")
playlist_gini_display = playlist_gini_artists.copy()    
playlist_gini_display["gini_artist"] = playlist_gini_display["gini_artist"].round(3)
st.dataframe(   
    playlist_gini_display.rename(columns={
        "playlist_name": "Playlist",
        "gini_artist": "Artist Gini"
    }),
    width="stretch"
)

# --------------------------------------------------
#chi-squared homogeneity test
#--------------------------------------------------

from scipy.stats import chi2_contingency
import pandas as pd

def chi2_homogeneity(
    df,
    group_col,      # e.g. playlist_name
    category_col,   # e.g. artist_name / nationality / genre
    count_col="track_count",
    min_expected=1
):
    """
    Streamlit-safe Chi-square homogeneity test
    Automatically removes zero-expected categories
    """

    # Pivot to contingency table
    table = (
        df.pivot_table(
            index=group_col,
            columns=category_col,
            values=count_col,
            aggfunc="sum",
            fill_value=0
        )
    )

    # --- DROP EMPTY COLUMNS ---
    table = table.loc[:, table.sum(axis=0) > 0]

    # --- DROP EMPTY ROWS ---
    table = table.loc[table.sum(axis=1) > 0]

    # Still too sparse → abort safely
    if table.shape[1] < 2 or table.shape[0] < 2:
        return {
            "chi2": None,
            "p_value": None,
            "dof": None,
            "note": "Insufficient shared categories for χ² test"
        }

    # Compute chi-square
    chi2, p, dof, expected = chi2_contingency(table.values)

    # Optional: check minimum expected frequency
    if (expected < min_expected).any():
        return {
            "chi2": chi2,
            "p_value": p,
            "dof": dof,
            "warning": "Some expected counts < 1; interpret with caution"
        }

    return {
        "chi2": chi2,
        "p_value": p,
        "dof": dof
    }

# --------------------------------------------------
#nationality homogeneity test
#--------------------------------------------------

st.subheader("🌍 Nationality Homogeneity Test (χ²)")

nat_result = chi2_homogeneity(
    df=df_nat,
    group_col="playlist_name",
    category_col="nationality",
    count_col="track_count"
)

c1, c2, c3 = st.columns(3)
c1.metric("χ² statistic", f"{nat_result['chi2']:.2f}")
c2.metric("Degrees of freedom", nat_result["dof"])
c3.metric("p-value", f"{nat_result['p_value']:.4f}")

if nat_result["p_value"] < 0.05:
    st.error("❌ Reject homogeneity: nationality distributions differ across playlists")
else:
    st.success("✅ Fail to reject homogeneity: nationality distributions are similar")


# --------------------------------------------------
# genre homogeneity test
# --------------------------------------------------

st.subheader("🎼 Genre Homogeneity Test (χ²)")

genre_result = chi2_homogeneity(
    df=df_genre,
    group_col="Playlist_name",
    category_col="genre_name",
    count_col="track_count"
)

g1, g2, g3 = st.columns(3)
g1.metric("χ² statistic", f"{genre_result['chi2']:.2f}")
g2.metric("Degrees of freedom", genre_result["dof"])
g3.metric("p-value", f"{genre_result['p_value']:.4f}")

if genre_result["p_value"] < 0.05:
    st.error("❌ Reject homogeneity: genre composition varies by playlist")
else:
    st.success("✅ Fail to reject homogeneity: genre composition is consistent")


# --------------------------------------------------
# artist homogeneity test
# --------------------------------------------------

artist_result = chi2_homogeneity(
    df_artist,
    group_col="playlist_name",
    category_col="artist_name",
    count_col="track_count"
)

st.subheader("χ² Homogeneity Test — Artists")
h1, h2, h3 = st.columns(3)
h1.metric("χ² statistic", f"{artist_result['chi2']:.2f}")
h2.metric("Degrees of freedom", artist_result["dof"])
h3.metric("p-value", f"{artist_result['p_value']:.4f}")
if artist_result["p_value"] < 0.05:
    st.error("❌ Reject homogeneity: artist exposure varies by playlist")
else:
    st.success("✅ Fail to reject homogeneity: artist exposure is consistent")



#--------------------------------------------------
#intrepretation note
#--------------------------------------------------

with st.expander("ℹ️ How to interpret χ² homogeneity tests"):
    st.markdown("""
**Chi-square tests of homogeneity** evaluate whether category distributions
(e.g. nationalities, genres, artists) are consistent across playlists.

- **p < 0.05** → Distributions differ → playlist-specific curation bias
- **p ≥ 0.05** → Distributions similar → systematic or uniform patterns

These tests complement:
- **CR10** (top dominance),
- **Gini** (overall inequality),
by assessing **whether bias is consistent across playlists**.
""")


# --------------------------------------------------
#   Chi-square Residuals Analysis
# --------------------------------------------------
# ============================================================
# χ² HETEROGENEITY ANALYSIS — NATIONALITIES, GENRES, ARTISTS
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from scipy.stats import chi2_contingency

st.set_page_config(page_title="Bias Tests — χ² Heterogeneity", layout="wide")

# ============================================================
# GENERIC χ² HETEROGENEITY FUNCTION (NATIONALITIES / GENRES)
# ============================================================

def chi2_heterogeneity(
    df,
    group_col,
    category_col,
    value_col="track_count",
    min_expected=5
):
    """
    χ² test of homogeneity with standardised residuals
    """

    table = pd.pivot_table(
        df,
        index=group_col,
        columns=category_col,
        values=value_col,
        aggfunc="sum",
        fill_value=0
    )

    # Remove sparse categories
    table = table.loc[:, table.sum(axis=0) >= min_expected]

    if table.shape[0] < 2 or table.shape[1] < 2:
        return {"error": "Insufficient data after filtering"}

    chi2, p, dof, expected = chi2_contingency(table.values)

    expected_df = pd.DataFrame(
        expected,
        index=table.index,
        columns=table.columns
    )

    residuals = (table - expected_df) / np.sqrt(expected_df)

    return {
        "chi2": chi2,
        "p_value": p,
        "dof": dof,
        "n_categories": table.shape[1],
        "n_playlists": table.shape[0],
        "result": "Reject homogeneity" if p < 0.05 else "Fail to reject",
        "residuals": residuals
    }

# ============================================================
# ARTIST χ² TEST (MATCHING OUTPUT FORMAT)
# ============================================================

def chi2_artist_heterogeneity(df, min_artist_exposure=20):
    """
    χ² test for artist exposure across playlists
    """

    table = pd.pivot_table(
        df,
        index="artist_name",
        columns="playlist_id",
        values="track_count",
        aggfunc="sum",
        fill_value=0
    )

    # Filter sparse artists & playlists
    table = table.loc[table.sum(axis=1) >= min_artist_exposure]
    table = table.loc[:, table.sum(axis=0) > 0]

    if table.shape[0] < 2 or table.shape[1] < 2:
        return {"error": "Insufficient data after filtering"}

    chi2, p, dof, expected = chi2_contingency(table.values)

    expected_df = pd.DataFrame(
        expected,
        index=table.index,
        columns=table.columns
    )

    residuals = (table - expected_df) / np.sqrt(expected_df)

    return {
        "chi2": chi2,
        "p_value": p,
        "dof": dof,
        "n_categories": table.shape[0],
        "n_playlists": table.shape[1],
        "result": "Reject homogeneity" if p < 0.05 else "Fail to reject",
        "residuals": residuals
    }

# ============================================================
# RESIDUAL DRIVER EXTRACTION (ALL ENTITIES)
# ============================================================

def residual_driver_table(residuals, top_n=15, label="Category"):
    out = (
        residuals.abs()
        .sum(axis=0)
        .sort_values(ascending=False)
        .head(top_n)
        .reset_index()
    )
    out.columns = [label, "Total χ² Residual Impact"]
    return out

# ============================================================
# LOAD YOUR DATA (REPLACE WITH YOUR SQL LOADERS)
# ============================================================

# These MUST already exist:
# df_nat   → playlist_id | nationality | track_count
# df_genre → playlist_id | genre_name  | track_count
# df_artist→ playlist_id | artist_name | track_count

# ============================================================
# NATIONALITIES
# ============================================================

st.header("🌍 Nationalities — χ² Heterogeneity")

nat_result = chi2_heterogeneity(
    df_nat,
    group_col="playlist_id",
    category_col="nationality"
)

if "error" in nat_result:
    st.error(nat_result["error"])
else:
    c1, c2, c3 = st.columns(3)
    c1.metric("χ² statistic", f"{nat_result['chi2']:.2f}")
    c2.metric("Degrees of freedom", nat_result["dof"])
    c3.metric("p-value", f"{nat_result['p_value']:.6f}")

    if nat_result["p_value"] < 0.05:
        st.error("❌ Reject homogeneity: nationality distributions differ across playlists")
    else:
        st.success("✅ Fail to reject homogeneity")

    nat_impact = residual_driver_table(
        nat_result["residuals"],
        label="Nationality"
    )

    nat_chart = (
        alt.Chart(nat_impact)
        .mark_bar()
        .encode(
            x=alt.X("Total χ² Residual Impact:Q",
                    title="Total Standardised Residual (χ² contribution)"),
            y=alt.Y("Nationality:N", sort="-x"),
            tooltip=["Nationality",
                     alt.Tooltip("Total χ² Residual Impact:Q", format=".2f")]
        )
        .properties(title="🌍 Nationalities Driving Playlist Heterogeneity")
    )

    st.altair_chart(nat_chart, width='stretch')

# ============================================================
# GENRES
# ============================================================

st.header("🎼 Genres — χ² Heterogeneity")

genre_result = chi2_heterogeneity(
    df_genre,
    group_col="playlist_id",
    category_col="genre_name"
)

if "error" in genre_result:
    st.error(genre_result["error"])
else:
    g1, g2, g3 = st.columns(3)
    g1.metric("χ² statistic", f"{genre_result['chi2']:.2f}")
    g2.metric("Degrees of freedom", genre_result["dof"])
    g3.metric("p-value", f"{genre_result['p_value']:.6f}")

    if genre_result["p_value"] < 0.05:
        st.error("❌ Reject homogeneity: genre composition varies across playlists")
    else:
        st.success("✅ Fail to reject homogeneity")

    genre_impact = residual_driver_table(
        genre_result["residuals"],
        label="Genre"
    )

    genre_chart = (
        alt.Chart(genre_impact)
        .mark_bar()
        .encode(
            x=alt.X("Total χ² Residual Impact:Q",
                    title="Total Standardised Residual (χ² contribution)"),
            y=alt.Y("Genre:N", sort="-x"),
            tooltip=["Genre",
                     alt.Tooltip("Total χ² Residual Impact:Q", format=".2f")]
        )
        .properties(title="🎼 Genres Driving Playlist Heterogeneity")
    )

    st.altair_chart(genre_chart, width='stretch')

# ============================================================
# ARTISTS
# ============================================================

st.header("🎤 Artists — χ² Heterogeneity")

artist_result = chi2_artist_heterogeneity(
    df_artist,
    min_artist_exposure=20
)

if "error" in artist_result:
    st.error(artist_result["error"])
else:
    a1, a2, a3 = st.columns(3)
    a1.metric("χ² statistic", f"{artist_result['chi2']:.2f}")
    a2.metric("Degrees of freedom", artist_result["dof"])
    a3.metric("p-value", f"{artist_result['p_value']:.6f}")

    if artist_result["p_value"] < 0.05:
        st.error("❌ Reject homogeneity: artist exposure differs across playlists")
    else:
        st.success("✅ Fail to reject homogeneity")

    artist_impact = (
        artist_result["residuals"]
        .abs()
        .sum(axis=1)
        .sort_values(ascending=False)
        .head(15)
        .reset_index()
    )
    artist_impact.columns = ["Artist", "Total χ² Residual Impact"]

    artist_chart = (
        alt.Chart(artist_impact)
        .mark_bar()
        .encode(
            x=alt.X("Total χ² Residual Impact:Q",
                    title="Total Standardised Residual (χ² contribution)"),
            y=alt.Y("Artist:N", sort="-x"),
            tooltip=["Artist",
                     alt.Tooltip("Total χ² Residual Impact:Q", format=".2f")]
        )
        .properties(title="🎤 Artists Driving Playlist Heterogeneity")
    )

    st.altair_chart(artist_chart, width='stretch')
