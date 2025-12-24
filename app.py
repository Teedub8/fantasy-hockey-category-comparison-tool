import streamlit as st
import pandas as pd
import numpy as np
import requests

# -----------------------------
# Helper Functions
# -----------------------------

@st.cache_data(ttl=3600)
def fetch_nhl_players():
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
    url = f"https://statsapi.web.nhl.com/api/v1/people/{player_id}/stats?stats=statsSingleSeason&season={season}"
    response = requests.get(url).json()
    stats = response['stats'][0]['splits']
    if stats:
        return stats[0]['stat']
    else:
        return {}

@st.cache_data(ttl=3600)
def build_full_stats_df():
    df_players = fetch_nhl_players()
    stats_list = []
    for idx, row in df_players.iterrows():
        player_stats = fetch_player_stats(row['id'])
        player_stats['id'] = row['id']
        stats_list.append(player_stats)
    df_stats = pd.DataFrame(stats_list)
    full_df = pd.merge(df_players, df_stats, on='id', how='left')
    numeric_cols = df_stats.select_dtypes(include='number').columns
    full_df[numeric_cols] = full_df[numeric_cols].fillna(0)
    return full_df

# -----------------------------
# Streamlit App
# -----------------------------

st.title("Fantasy Hockey Multi-Player Comparison Dashboard")

df = build_full_stats_df()
player_names = df['name'].tolist()
numeric_cols = df.select_dtypes(include='number').columns.tolist()

st.subheader("Select Players for Side A")
side_a_input = st.text_input("Search Side A Players (comma-separated)")
if side_a_input:
    side_a_list = [name.strip() for name in side_a_input.split(",")]
    side_a_options = [name for name in player_names if any(n.lower() in name.lower() for n in side_a_list)]
else:
    side_a_options = player_names
side_a_selected = st.multiselect("Side A Players", side_a_options)

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
def aggregate_players(players):
    if not players:
        return pd.Series([0]*len(numeric_cols), index=numeric_cols)
    subset = df[df['name'].isin(players)]
    return subset[numeric_cols].sum()

side_a_stats = aggregate_players(side_a_selected)
side_b_stats = aggregate_players(side_b_selected)

# Percentiles for each player group
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

# -----------------------------
# Highlight higher stat and percentile
# -----------------------------
def highlight_comparison(row):
    colors = []
    # Highlight higher raw stat (green)
    if row["Side A"] > row["Side B"]:
        colors.append('background-color: lightgreen')
        colors.append('')
    elif row["Side B"] > row["Side A"]:
        colors.append('')
        colors.append('background-color: lightgreen')
    else:
        colors.append('')
        colors.append('')

    # Highlight higher percentile (blue)
    if row["Percentile - Side A"] > row["Percentile - Side B"]:
        colors.append('background-color: lightblue')
        colors.append('')
    elif row["Percentile - Side B"] > row["Percentile - Side A"]:
        colors.append('')
        colors.append('background-color: lightblue')
    else:
        colors.append('')
        colors.append('')

    return colors

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

# Determine who “wins” the matchup
if category_wins_a > category_wins_b:
    st.markdown("### ✅ Side A wins the matchup!")
elif category_wins_b > category_wins_a:
    st.markdown("### ✅ Side B wins the matchup!")
else:
    st.markdown("### ⚖️ The matchup is tied!")
