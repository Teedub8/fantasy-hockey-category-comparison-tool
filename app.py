import streamlit as st
import pandas as pd
import numpy as np
import requests
import os

# -----------------------------
# Paths
# -----------------------------
DATA_PATH = "data/full_nhl_stats.csv"  # pre-downloaded CSV

# -----------------------------
# Helper Functions
# -----------------------------

@st.cache_data(ttl=3600)
def fetch_nhl_players():
    """Fetch all NHL players with IDs, teams, and positions"""
    teams_url = "https://statsapi.web.nhl.com/api/v1/teams"
    teams = requests.get(teams_url).json()['teams']
    all_players = []
    for team in teams:
        roster_url = f"https://statsapi.web.nhl.com/api/v1/teams/{team['id']}/roster"
        roster = requests.get(roster_url).json()['roster']
        for player in roster:
            all_players.append({
                "id": player['person']['id'],
                "name": player['person']['fullName'],
                "position": player['position']['name'],
                "team": team['name']
            })
    return pd.DataFrame(all_players)

@st.cache_data(ttl=3600)
def fetch_player_stats(player_id, season="20252026"):
    """Fetch season stats for a player"""
    url = f"https://statsapi.web.nhl.com/api/v1/people/{player_id}/stats?stats=statsSingleSeason&season={season}"
    response = requests.get(url).json()
    stats = response['stats'][0]['splits']
    if stats:
        return stats[0]['stat']
    else:
        return {}

@st.cache_data(ttl=3600)
def build_full_stats_df():
    """Build full DataFrame with all player stats"""
    df_players = fetch_nhl_players()
    stats_list = []
    for _, row in df_players.iterrows():
        player_stats = fetch_player_stats(row['id'])
        player_stats['id'] = row['id']
        stats_list.append(player_stats)
    df_stats = pd.DataFrame(stats_list)
    full_df = pd.merge(df_players, df_stats, on='id', how='left')
    numeric_cols = df_stats.select_dtypes(include='number').columns
    full_df[numeric_cols] = full_df[numeric_cols].fillna(0)
    return full_df

def aggregate_players(df, players, numeric_cols):
    """Sum stats for a list of players"""
    if not players:
        return pd.Series([0]*len(numeric_cols), index=numeric_cols)
    subset = df[df['name'].isin(players)]
    return subset[numeric_cols].sum()

def highlight_comparison(row):
    """Highlight higher stat and percentile safely"""
    styles = [''] * len(row)
    try:
        a_idx = row.index.get_loc("Side A")
        b_idx = row.index.get_loc("Side B")
        pa_idx = row.index.get_loc("Percentile - Side A")
        pb_idx = row.index.get_loc("Percentile - Side B")

        if row["Side A"] > row["Side B"]:
            styles[a_idx] = 'background-color: lightgreen'
        elif row["Side B"] > row["Side A"]:
            styles[b_idx] = 'background-color: lightgreen'

        if row["Percentile - Side A"] > row["Percentile - Side B"]:
            styles[pa_idx] = 'background-color: lightblue'
        elif row["Percentile - Side B"] > row["Percentile - Side A"]:
            styles[pb_idx] = 'background-color: lightblue'
    except KeyError:
        pass
    return styles

# -----------------------------
# Streamlit App
# -----------------------------

st.title("Fantasy Hockey Multi-Player Comparison Dashboard")

# -----------------------------
# Load CSV data by default
# -----------------------------
if os.path.exists(DATA_PATH):
    df = pd.read_csv(DATA_PATH)
    st.success("Loaded NHL stats from CSV.")
else:
    st.warning("CSV not found. Use 'Fetch Live NHL Stats' button to load data.")
    df = pd.DataFrame()

# -----------------------------
# Fetch Live NHL Stats Button
# -----------------------------
if st.button("Fetch Live NHL Stats"):
    with st.spinner("Fetching NHL player data... this may take a while"):
        try:
            df = build_full_stats_df()
            os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
            df.to_csv(DATA_PATH, index=False)
            st.success("Live NHL data fetched and saved!")
        except requests.exceptions.RequestException:
            st.error("Failed to fetch NHL data. Try again later.")
            df = pd.DataFrame()

# Only show comparison if data exists
if not df.empty:
    player_names = df['name'].tolist()
    numeric_cols = df.select_dtypes(include='number').columns.tolist()

    # -----------------------------
    # Side A selection
    # -----------------------------
    st.subheader("Select Players for Side A")
    side_a_input = st.text_input("Search Side A Players (comma-separated)")
    if side_a_input:
        side_a_list = [name.strip() for name in side_a_input.split(",")]
        side_a_options = [name for name in player_names if any(n.lower() in name.lower() for n in side_a_list)]
    else:
        side_a_options = player_names
    side_a_selected = st.multiselect("Side A Players", side_a_options)

    # -----------------------------
    # Side B selection
    # -----------------------------
    st.subheader("Select Players for Side B")
    side_b_input = st.text_input("Search Side B Players (comma-separated)")
    if side_b_input:
        side_b_list = [name.strip() for name in side_b_input.split(",")]
        side_b_options = [name for name in player_names if any(n.lower() in name.lower() for n in side_b_list)]
    else:
        side_b_options = player_names
    side_b_selected = st.multiselect("Side B Players", side_b_options)

    # -----------------------------
    # Aggregate stats
    # -----------------------------
    side_a_stats = aggregate_players(df, side_a_selected, numeric_cols)
    side_b_stats = aggregate_players(df, side_b_selected, numeric_cols)

    # Percentiles
    percentiles = df[numeric_cols].rank(pct=True) * 100
    side_a_percentiles = percentiles.loc[df['name'].isin(side_a_selected)].sum()
    side_b_percentiles = percentiles.loc[df['name'].isin(side_b_selected)].sum()

    # Build comparison DataFrame
    comparison_df = pd.DataFrame({
        "Stat": numeric_cols,
        "Side A": side_a_stats.values,
        "Percentile - Side A": side_a_percentiles.values,
        "Side B": side_b_stats.values,
        "Percentile - Side B": side_b_percentiles.values
    })

    # Show comparison with highlights
    st.dataframe(comparison_df.style.apply(highlight_comparison, axis=1))

    # -----------------------------
    # Summary visualization
    # -----------------------------
    st.subheader("Overall Comparison Summary")
    side_a_total = side_a_stats.sum()
    side_b_total = side_b_stats.sum()
    st.markdown(f"**Side A Total Stats: {side_a_total}**")
    st.markdown(f"**Side B Total Stats: {side_b_total}**")
    st.bar_chart(pd.DataFrame({
        "Side A": side_a_stats,
        "Side B": side_b_stats
    }))

    # -----------------------------
    # Category wins
    # -----------------------------
    category_wins_a = (side_a_stats > side_b_stats).sum()
    category_wins_b = (side_b_stats > side_a_stats).sum()
    category_ties = (side_a_stats == side_b_stats).sum()

    st.subheader("Category Wins")
    st.markdown(f"- Side A wins: {category_wins_a} categories")
    st.markdown(f"- Side B wins: {category_wins_b} categories")
    st.markdown(f"- Tied: {category_ties} categories")

    if category_wins_a > category_wins_b:
        st.markdown("### ✅ Side A wins the matchup!")
    elif category_wins_b > category_wins_a:
        st.markdown("### ✅ Side B wins the matchup!")
    else:
        st.markdown("### ⚖️ The matchup is tied!")
