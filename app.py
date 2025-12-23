import streamlit as st
import pandas as pd
import numpy as np

# Ensure correct working directory (important for Streamlit Cloud)

# -----------------------------
# Configuration
# -----------------------------

DEFAULT_LEAGUE = {
    "teams": 12,
    "skaters_per_team": 15,
    "depth_buffer": 0.30,          # 30% buffer
    "replacement_percentile": 15   # replacement = streamer level
}

CATEGORIES = ["G", "A", "PPP", "SOG", "SHP", "HITS", "BLKS", "FW"]

# -----------------------------
# Helper Functions
# -----------------------------

def calculate_pool_size(teams, skaters_per_team, buffer):
    return int(teams * skaters_per_team * (1 + buffer))

def z_score(series):
    return (series - series.mean()) / series.std(ddof=0)

def normalize(df, categories, pool_size, replacement_percentile):
    results = {}

    for pos in ["F", "D"]:
       pos_df = df[df["POS"] == pos].copy()

    # Skip if there are no players of this position
    if pos_df.empty:
        results[pos] = pd.DataFrame()
    continue

# Fantasy-relevant players by TOI
pos_df = pos_df.sort_values("TOI", ascending=False).head(pool_size)

z_df = pd.DataFrame(index=pos_df.index)

        for cat in categories:
            z_df[cat] = z_score(pos_df[cat])

        z_df["TOTAL"] = z_df.sum(axis=1)

        # Shift so replacement level = 0
        baseline = np.percentile(z_df["TOTAL"], replacement_percentile)
        z_df["TOTAL"] = z_df["TOTAL"] - baseline

        results[pos] = z_df

    return results

# -----------------------------
# Streamlit UI
# -----------------------------

st.set_page_config(page_title="Fantasy Hockey Player Comparison", layout="centered")

st.title("Fantasy Hockey Player Comparison Tool")

# Load data
df = pd.read_csv("data/skaters_season.csv")

# Sidebar: League Settings
st.sidebar.header("League Settings")
teams = st.sidebar.number_input("Teams", 8, 20, DEFAULT_LEAGUE["teams"])
skaters_per_team = st.sidebar.number_input(
    "Skaters per Team", 10, 20, DEFAULT_LEAGUE["skaters_per_team"]
)

pool_size = calculate_pool_size(
    teams,
    skaters_per_team,
    DEFAULT_LEAGUE["depth_buffer"]
)

st.sidebar.caption(f"Player pool size: {pool_size}")

# Sidebar: Category Toggles
st.sidebar.header("Categories")
active_categories = [
    cat for cat in CATEGORIES if st.sidebar.checkbox(cat, value=True)
]

if not active_categories:
    st.warning("You must select at least one category.")
    st.stop()

# Player selection
player_list = sorted(df["Player"].unique())

col1, col2 = st.columns(2)
with col1:
    player1 = st.selectbox("Player 1", player_list)
with col2:
    player2 = st.selectbox("Player 2", player_list)

# Normalize
normalized = normalize(
    df,
    active_categories,
    pool_size,
    DEFAULT_LEAGUE["replacement_percentile"]
)

p1 = df[df["Player"] == player1].iloc[0]
p2 = df[df["Player"] == player2].iloc[0]

pos = p1["POS"]  # v1 assumes same position

p1_score = normalized[pos].loc[p1.name]["TOTAL"]
p2_score = normalized[pos].loc[p2.name]["TOTAL"]

# Results
st.subheader("Value vs Replacement (0 = Streamer Level)")

c1, c2 = st.columns(2)
c1.metric(player1, round(p1_score, 2))
c2.metric(player2, round(p2_score, 2))

# Optional breakdown
if st.checkbox("Show category breakdown"):
    breakdown = pd.DataFrame({
        player1: normalized[pos].loc[p1.name][active_categories],
        player2: normalized[pos].loc[p2.name][active_categories]
    })
    st.dataframe(breakdown.style.format("{:.2f}"))
