import streamlit as st
import pandas as pd
import numpy as np
import yahoo_fantasy_api as yfa
from yahoo_oauth import OAuth2

# -----------------------------
# Streamlit App Config
# -----------------------------
st.set_page_config(
    page_title="Fantasy Hockey Player Comparison",
    layout="wide"
)

st.title("Fantasy Hockey Player Comparison Tool")

# -----------------------------
# Yahoo OAuth (Secrets-Based)
# -----------------------------
oauth = OAuth2(
    consumer_key=st.secrets["yahoo"]["consumer_key"],
    consumer_secret=st.secrets["yahoo"]["consumer_secret"],
)

if not oauth.token_is_valid():
    st.warning("Yahoo authorization required")

    auth_url = oauth.authorization_url()
    st.write("https://api.login.yahoo.com/oauth2/request_auth?redirect_uri=oob&response_type=code&client_id=dj0yJmk9dUJ0aG1nUVNCSU1OJmQ9WVdrOWJUVlpWM1pDWW0wbWNHbzlNQT09JnM9Y29uc3VtZXJzZWNyZXQmc3Y9MCZ4PTgx")
    st.code(auth_url)

    verifier = st.text_input("Enter the Yahoo authorization code here")

    if verifier:
        oauth.get_access_token(verifier)
        st.success("Authorization successful. Please refresh the page.")
        st.stop()

    st.stop()

# -----------------------------
# Sidebar Inputs
# -----------------------------
st.sidebar.header("Yahoo League Settings")
league_id = st.sidebar.text_input("Enter your Yahoo League ID")
fetch_button = st.sidebar.button("Fetch Live Stats")

# -----------------------------
# Data Fetching
# -----------------------------
@st.cache_data(show_spinner=False)
def fetch_yahoo_league_data(oauth, league_id):
    gm = yfa.Game(oauth, "nhl")
    league = gm.to_league(league_id)

    teams = league.teams()

    all_rostered_players = []

    for team in teams:
        roster = team.roster()
        for slot in ["players", "bench", "ir", "ir_plus", "na"]:
            all_rostered_players.extend(roster.get(slot, []))

    rostered_ids = {p["player_id"] for p in all_rostered_players}

    all_players = league.player_stats()
    df = pd.DataFrame(all_players)

    df["is_rostered"] = df["player_id"].isin(rostered_ids)

    return df

# -----------------------------
# Z-Score Calculation
# -----------------------------
@st.cache_data(show_spinner=False)
def compute_z_scores(df, numeric_cols):
    # Replacement pool = unrostered players ONLY
    replacement_pool = df[~df["is_rostered"]][numeric_cols]

    mean_vals = replacement_pool.mean()
    std_vals = replacement_pool.std(ddof=0)

    z_scores = (df[numeric_cols] - mean_vals) / std_vals
    return z_scores

# -----------------------------
# Main App Logic
# -----------------------------
if fetch_button and league_id:
    with st.spinner("Fetching live data from Yahoo…"):
        df = fetch_yahoo_league_data(oauth, league_id)

    if df is not None and not df.empty:
        numeric_cols = [
            c for c in df.columns
            if pd.api.types.is_numeric_dtype(df[c])
        ]

        z_scores = compute_z_scores(df, numeric_cols)
        z_scores_df = pd.concat([df[["name"]], z_scores], axis=1)

        st.sidebar.header("Compare Players")
        players_to_compare = st.sidebar.multiselect(
            "Select players to compare",
            df["name"].sort_values().unique().tolist()
        )

        if players_to_compare:
            comparison_df = z_scores_df[
                z_scores_df["name"].isin(players_to_compare)
            ]

            st.subheader("Player Z-Score Comparison")
            st.dataframe(
                comparison_df.style.highlight_max(
                    axis=0, color="lightgreen"
                ),
                use_container_width=True
            )

            st.subheader("Category Comparison")
            melted = comparison_df.melt(
                id_vars="name",
                var_name="Category",
                value_name="Z-Score"
            )

            import plotly.express as px
            fig = px.bar(
                melted,
                x="Category",
                y="Z-Score",
                color="name",
                barmode="group"
            )

            st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("No data returned from Yahoo. Check League ID.")

else:
    st.info("Enter your Yahoo League ID and click 'Fetch Live Stats' to begin.")
