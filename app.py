import streamlit as st
import pandas as pd
import numpy as np
from yahoo_oauth import OAuth2
import yahoo_fantasy_api as yfa

# -----------------------------
# Streamlit App Config
# -----------------------------
st.set_page_config(page_title="Fantasy Hockey Player Comparison", layout="wide")

st.title("Fantasy Hockey Player Comparison Tool")

from yahoo_oauth import OAuth2

oauth = OAuth2(
    consumer_key=st.secrets["yahoo"]["consumer_key"],
    consumer_secret=st.secrets["yahoo"]["consumer_secret"],
)

if not oauth.token_is_valid():
    st.warning("Authenticating with Yahoo…")
    oauth.refresh_access_token()
    st.stop()

# -----------------------------
# Yahoo League Authentication
# -----------------------------
st.sidebar.header("Yahoo League Settings")
league_id = st.sidebar.text_input("Enter your Yahoo League ID")

# Button to fetch live data
fetch_button = st.sidebar.button("Fetch Live Stats")

# -----------------------------
# Utility Functions
# -----------------------------

    # Connect to Yahoo Fantasy API
    gm = yfa.Game(oauth, 'nhl')
    league = gm.to_league(league_id)
    
    # Fetch rosters and players
    teams = league.teams()
    all_rostered_players = []
    for team in teams:
        roster = team.roster()
        # Include all roster spots: active, bench, IR/IL, IR+, NA
        for player_list in ['players', 'bench', 'ir', 'ir_plus', 'na']:
            all_rostered_players.extend(roster.get(player_list, []))
    
    # Flatten unique player IDs
    all_rostered_ids = list({p['player_id']: p for p in all_rostered_players}.keys())
    
    # Fetch stats for all players in league
    all_players = league.player_stats()
    all_players_df = pd.DataFrame(all_players)

    # Add a column indicating if player is rostered
    all_players_df['is_rostered'] = all_players_df['player_id'].isin(all_rostered_ids)
    
def fetch_yahoo_league_data(league_id):
    all_players_df = []

    return all_players_df

@st.cache_data
def compute_z_scores(df, numeric_cols):
    # Replacement pool = all unrostered players
    replacement_pool = df[~df['is_rostered']][numeric_cols]
    mean_vals = replacement_pool.mean()
    std_vals = replacement_pool.std(ddof=0)
    
    z_scores = (df[numeric_cols] - mean_vals) / std_vals
    return z_scores

# -----------------------------
# Main Logic
# -----------------------------
if fetch_button and league_id:
    with st.spinner("Fetching league data from Yahoo..."):
        df = fetch_yahoo_league_data(league_id)
    
    if df is not None:
        numeric_cols = [c for c in df.columns if df[c].dtype in [np.float64, np.int64]]
        
        # Compute z-scores
        z_scores = compute_z_scores(df, numeric_cols)
        z_scores_df = pd.concat([df[['name']], z_scores], axis=1)

        # -----------------------------
        # Player Comparison Inputs
        # -----------------------------
        st.sidebar.header("Compare Players")
        players_to_compare = st.sidebar.multiselect("Select players to compare", df['name'].tolist())
        
        if players_to_compare:
            comparison_df = z_scores_df[z_scores_df['name'].isin(players_to_compare)]
            
            # Display comparison table
            st.subheader("Player Z-Score Comparison")
            st.dataframe(comparison_df.style.highlight_max(axis=0, color='lightgreen'))

            # Side-by-side bar chart
            st.subheader("Category Comparison")
            import plotly.express as px
            melted = comparison_df.melt(id_vars='name', var_name='Category', value_name='Z-Score')
            fig = px.bar(melted, x='Category', y='Z-Score', color='name', barmode='group')
            st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Enter your Yahoo League ID and click 'Fetch Live Stats' to start.")
