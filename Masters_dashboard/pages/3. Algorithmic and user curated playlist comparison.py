import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from scipy.stats import chi2_contingency
from db import get_connection

st.set_page_config(
    page_title="Algorithmic vs User Bias — χ² Independence",
    layout="wide"
)

st.title("🤖 Algorithmic vs User-Curated Playlists")
st.caption("χ² Tests of Independence for Cultural Representation")
st.markdown("""
This dashboard compares the representation of different cultural groups in algorithmically
 generated playlists versus user-curated playlists. 
We use the Chi-squared (χ²) test of independence to determine if there are significant differences 
in the distribution of cultural groups between these two types of playlists.
""")   


# import all_playlist_nationality_distribution view
@st.cache_data(show_spinner=True)
def load_playlist_nationality():
    query = "SELECT * FROM vw_all_playlist_nationality_distribution"
    conn = get_connection()
    return pd.read_sql(query, conn)

df_nat_1 = load_playlist_nationality()


#import all_playlist_genre_distribution view
@st.cache_data(show_spinner=True)   
def load_playlist_genre():
    query = "SELECT * FROM vw_all_playlist_genre_distribution"
    conn = get_connection()
    return pd.read_sql(query, conn)
df_genre_1 = load_playlist_genre()


#Import all_playlist_artist_distribution view
@st.cache_data(show_spinner=True)
def load_artist_data():
    query = "SELECT * FROM vw_all_playlist_artist_exposure"
    conn = get_connection()
    return pd.read_sql(query, conn)
df_artist_1 = load_artist_data()


st.subheader("Nationality Exposure Distribution within Algorithmic and User-Curated Playlists ")

def nationality_playlist_comparison(df, top_n=20):
    """
    Prepares nationality proportions for algorithmic vs user playlists
    """

    # Aggregate counts
    agg = (
        df.groupby(["playlist_type", "nationality"])["track_count"]
        .sum()
        .reset_index()
    )

    # Convert to proportions within playlist type
    agg["share"] = (
        agg.groupby("playlist_type")["track_count"]
           .transform(lambda x: x / x.sum())
    )

    # Keep top nationalities by total exposure
    top_nats = (
        agg.groupby("nationality")["track_count"]
           .sum()
           .sort_values(ascending=False)
           .head(top_n)
           .index
    )

    return agg[agg["nationality"].isin(top_nats)]


import altair as alt
import streamlit as st

plot_df = nationality_playlist_comparison(df_nat_1, top_n=20)

base = alt.Chart(plot_df).encode(
    y=alt.Y("nationality:N", sort="-x", title="Nationality")
)

lines = base.mark_rule(color="lightgray").encode(
    x="min(share):Q",
    x2="max(share):Q"
)

points = base.mark_circle(size=80).encode(
    x="share:Q",
    color=alt.Color(
        "playlist_type:N",
        scale=alt.Scale(
            domain=["Algorithmic", "User"],
            range=["#d62728", "#1f77b4"]
        ),
        title="Playlist Type"
    ),
    tooltip=[
        "playlist_type",
        alt.Tooltip("share:Q", format=".2%")
    ]
)

chart = (
    (lines + points)
    .properties(
        title="🎧 Nationality Representation: Algorithmic vs User-Curated Playlists"
    )
)

st.altair_chart(chart, use_container_width=True)

# genre distribution comparison function within playlist types
st.subheader("Genre exposure distribution within Algorithmic and User curated playlists")

def genre_playlist_comparison(df, top_n=20):
    """
    Prepares genre proportions for algorithmic vs user playlists
    """

    agg = (
        df.groupby(["playlist_type", "genre_name"])["track_count"]
        .sum()
        .reset_index()
    )

    agg["share"] = (
        agg.groupby("playlist_type")["track_count"]
           .transform(lambda x: x / x.sum())
    )

    top_genres = (
        agg.groupby("genre_name")["track_count"]
           .sum()
           .sort_values(ascending=False)
           .head(top_n)
           .index
    )

    return agg[agg["genre_name"].isin(top_genres)]


plot_df = genre_playlist_comparison(df_genre_1, top_n=20)

base = alt.Chart(plot_df).encode(
    y=alt.Y("genre_name:N", sort="-x", title="Genre")
)

lines = base.mark_rule(color="lightgray").encode(
    x="min(share):Q",
    x2="max(share):Q"
)

points = base.mark_circle(size=80).encode(
    x="share:Q",
    color=alt.Color(
        "playlist_type:N",
        scale=alt.Scale(
            domain=["Algorithmic", "User"],
            range=["#d62728", "#1f77b4"]
        ),
        title="Playlist Type"
    ),
    tooltip=[
        "playlist_type",
        alt.Tooltip("share:Q", title="Share of Tracks", format=".2%")
    ]
)

chart = (
    lines + points
).properties(
    title="🎼 Genre Representation: Algorithmic vs User-Curated Playlists"
)

st.altair_chart(chart, use_container_width=True)


st.subheader("Artist distribution Exposure within Algorithmic and User curated playlists")
def artist_playlist_comparison(df, top_n=20):
    """
    Prepares artist proportions for algorithmic vs user playlists
    """

    agg = (
        df.groupby(["playlist_type", "artist_name"])["track_count"]
        .sum()
        .reset_index()
    )

    agg["share"] = (
        agg.groupby("playlist_type")["track_count"]
           .transform(lambda x: x / x.sum())
    )

    top_artists = (
        agg.groupby("artist_name")["track_count"]
           .sum()
           .sort_values(ascending=False)
           .head(top_n)
           .index
    )

    return agg[agg["artist_name"].isin(top_artists)]


plot_df = artist_playlist_comparison(df_artist_1, top_n=20)

base = alt.Chart(plot_df).encode(
    y=alt.Y("artist_name:N", sort="-x", title="Artist")
)

lines = base.mark_rule(color="lightgray").encode(
    x="min(share):Q",
    x2="max(share):Q"
)

points = base.mark_circle(size=80).encode(
    x="share:Q",
    color=alt.Color(
        "playlist_type:N",
        scale=alt.Scale(
            domain=["Algorithmic", "User"],
            range=["#d62728", "#1f77b4"]
        ),
        title="Playlist Type"
    ),
    tooltip=[
        "artist_name",
        "playlist_type",
        alt.Tooltip("share:Q", title="Share of Tracks", format=".2%")
    ]
)

chart = (
    lines + points
).properties(
    title="🎤 Artist Representation: Algorithmic vs User-Curated Playlists"
)

st.altair_chart(chart, use_container_width=True)


# Chi-squared test of independence function
st.subheader("Chi-squared Test of Independence ")

def chi2_independence(
    df,
    category_col,
    playlist_type_col="playlist_type",
    count_col="track_count",
    min_category_exposure=5
):
    """
    Chi-square test of independence between playlist type and a categorical variable

    Parameters
    ----------
    df : DataFrame
    category_col : str
        'nationality', 'genre_name', or 'artist_name'
    playlist_type_col : str
        Typically 'playlist_type' (Algorithmic vs User)
    count_col : str
        Track counts
    min_category_exposure : int
        Minimum total exposure to avoid sparse χ² issues
    """

    # Aggregate counts
    table = (
        df.groupby([playlist_type_col, category_col])[count_col]
        .sum()
        .unstack(fill_value=0)
    )

    # Remove sparse categories (CRITICAL)
    table = table.loc[:, table.sum(axis=0) >= min_category_exposure]

    # Safety check
    if table.shape[0] < 2 or table.shape[1] < 2:
        return {"error": "Insufficient data after filtering"}

    # χ² test
    chi2, p, dof, expected = chi2_contingency(table.values)

    # Effect size: Cramér’s V
    n = table.values.sum()
    cramers_v = np.sqrt(chi2 / (n * (min(table.shape) - 1)))

    return {
        "chi2": chi2,
        "p_value": p,
        "degrees_of_freedom": dof,
        "cramers_v": cramers_v,
        "n_categories": table.shape[1],
        "result": "Reject independence" if p < 0.05 else "Fail to reject"
    }

# Chi-squared test for nationality
nat_chi2 = chi2_independence(
    df=df_nat_1,
    category_col="nationality",
    min_category_exposure=5
)

nat_chi2

#chi-squared test for genres
genre_chi2 = chi2_independence(
    df=df_genre_1,
    category_col="genre_name",
    min_category_exposure=5
)

genre_chi2

#chi-squared test for artists
artist_chi2 = chi2_independence(
    df=df_artist_1,
    category_col="artist_name",
    min_category_exposure=10
)

artist_chi2


import streamlit as st

st.subheader("χ² Tests of Independence")

c1, c2, c3 = st.columns(3)

with c1:
    st.metric(
        "Nationality χ²",
        f"{nat_chi2['chi2']:.2f}",
        f"V = {nat_chi2['cramers_v']:.2f}"
    )

with c2:
    st.metric(
        "Genre χ²",
        f"{genre_chi2['chi2']:.2f}",
        f"V = {genre_chi2['cramers_v']:.2f}"
    )

with c3:
    st.metric(
        "Artist χ²",
        f"{artist_chi2['chi2']:.2f}",
        f"V = {artist_chi2['cramers_v']:.2f}"
    )



st.subheader("Artist-level χ² Contributions")

def artist_chi2_contributions(df, min_artist_exposure=10, top_n=20):
    """
    Computes artist-level χ² contributions for Algorithmic vs User playlists
    """

    # Build contingency table
    table = (
        df.groupby(["playlist_type", "artist_name"])["track_count"]
        .sum()
        .unstack(fill_value=0)
    )

    # Remove sparse artists (CRITICAL)
    table = table.loc[:, table.sum(axis=0) >= min_artist_exposure]

    if table.shape[0] < 2 or table.shape[1] < 2:
        return pd.DataFrame()

    # χ² test
    chi2, p, dof, expected = chi2_contingency(table.values)

    # Compute per-cell χ² contribution
    contrib = (table.values - expected) ** 2 / expected

    contrib_df = pd.DataFrame(
        contrib,
        index=table.index,
        columns=table.columns
    )

    # Sum contributions per artist
    artist_contrib = (
        contrib_df.sum(axis=0)
        .sort_values(ascending=False)
        .head(top_n)
        .reset_index()
        .rename(columns={
            "artist_name": "artist_name",
            0: "chi2_contribution"
        })
    )

    return artist_contrib


import altair as alt
import streamlit as st

artist_drivers = artist_chi2_contributions(
    df_artist_1,
    min_artist_exposure=10,
    top_n=20
)

if artist_drivers.empty:
    st.warning("Not enough data to compute artist χ² contributions.")
else:
    chart = (
        alt.Chart(artist_drivers)
        .mark_bar()
        .encode(
            x=alt.X(
                "chi2_contribution:Q",
                title="χ² Contribution"
            ),
            y=alt.Y(
                "artist_name:N",
                sort="-x",
                title="Artist"
            ),
            tooltip=[
                "artist_name",
                alt.Tooltip(
                    "chi2_contribution:Q",
                    title="χ² Contribution",
                    format=".2f"
                )
            ]
        )
        .properties(
            title="🎤 Artists Driving χ² Dependence (Algorithmic vs User)"
        )
    )

    st.altair_chart(chart, use_container_width=True)


#Jensen-Shannon divergence function
import numpy as np
import pandas as pd
from scipy.spatial.distance import jensenshannon

def js_divergence(
    df,
    category_col,
    playlist_type_col="playlist_type",
    count_col="track_count",
    min_category_exposure=5
):
    """
    Jensen-Shannon divergence between Algorithmic and User playlists
    for a categorical variable (nationality, genre, artist)
    """

    # Aggregate counts
    agg = (
        df.groupby([playlist_type_col, category_col])[count_col]
        .sum()
        .reset_index()
    )

    # Remove sparse categories
    total_exposure = agg.groupby(category_col)[count_col].sum()
    keep = total_exposure[total_exposure >= min_category_exposure].index
    agg = agg[agg[category_col].isin(keep)]

    # Pivot to distributions
    pivot = (
        agg.pivot_table(
            index=category_col,
            columns=playlist_type_col,
            values=count_col,
            fill_value=0
        )
    )

    # Ensure both playlist types exist
    if pivot.shape[1] < 2:
        return {"error": "Both playlist types required"}

    # Normalise to probability distributions
    if not {"Algorithmic", "User"}.issubset(pivot.columns):
       return {"error": "Missing playlist types"}

    P = pivot["Algorithmic"].values.astype(float)
    Q = pivot["User"].values.astype(float)


    P = P / P.sum()
    Q = Q / Q.sum()

    # Jensen–Shannon divergence
    js = jensenshannon(P, Q, base=2) ** 2

    return {
        "js_divergence": js,
        "n_categories": pivot.shape[0]
    }


js_nationality = js_divergence(
    df=df_nat_1,
    category_col="nationality",
    min_category_exposure=5
)

# js_nationality


js_genre = js_divergence(
    df=df_genre_1,
    category_col="genre_name",
    min_category_exposure=5
)

# js_genre

js_artist = js_divergence(
    df=df_artist_1,     
    category_col="artist_name",
    min_category_exposure=10
)
# js_artist


# Display Jensen-Shannon divergence results

st.subheader("Jensen–Shannon Divergence")

c1, c2, c3 = st.columns(3)

c1.metric(
    "Nationality JS",
    f"{js_nationality['js_divergence']:.3f}"
)

c2.metric(
    "Genre JS",
    f"{js_genre['js_divergence']:.3f}"
)

c3.metric(
    "Artist JS",
    f"{js_artist['js_divergence']:.3f}"
)

st.caption(
    "Low JS values indicate similar distributions, while higher values indicate stronger divergence. "
    "Artist-level divergence is substantially larger than nationality or genre."
)
