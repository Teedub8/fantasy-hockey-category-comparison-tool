import streamlit as st
import pandas as pd
import numpy as np

# -----------------------------
# Configuration
# -----------------------------

DEFAULT_LEAGUE = {
    "teams": 12,
    "skaters_per_team": 15,
    "depth_buffer": 0.30,
    "replacement_percentile": 15
}

CATEGORIES = ["G", "A", "PPP", "SOG", "SHP", "HITS", "BLKS", "FW"]

# -----------------------------
# Helper Functions
# -----------------------------

def calculate_pool_size(teams, skaters_per_team, buffer):
    return int(teams * skaters_per_team * (1 + buffer))

def z_score(series):
    if series.std(ddof=0) == 0 or series.isna().all():
        return pd.Series(0, index=series.index)
    return (series - series.mean()) / series.std(ddof=0)

def normalize(df, categories, pool_size, replacement_percentile):
    results = {}

    for pos in ["F", "D"]:
        pos_df = df[df["POS"] == pos]

        if pos_df.empty:
            results[pos] = pd.DataFrame()
            continue

        pos_df = pos_df.sort_values("TOI", ascending=False).head(pool_size)

        z_df = pd.DataFrame(index=pos_df.index)

        for cat in categories:
            if cat in pos_df.columns:
                z_df[cat] = z_score(pos_df[cat])
            else:
                z_df[cat] = 0

        z_df["TOTAL"] = z_df.sum(axis=1)

        valid_totals = z_df["TOTAL"].dropna()

        if valid_totals.empty:
            baseline = 0
        else:
            baseline = np.percentile(valid_totals, replacement_percentile)

        z_df["TOTAL"] = z_df["TOTAL"] - baseline
        results[pos] = z_df

    return results

# -----------------------------
# Streamlit App
# -----------------------------

st.set_page_config(
    page_title="Fantasy Hockey Player Comparison",
    layout="centered"
)

st.title("Fantasy Hockey Player Comparison Tool")

# -----------------------------
# Load Data (SAFE)
# -----------------------------

try:
    df = pd.read_csv("data/skaters_season.csv")
except Exception as e:
    st.error("Failed to load CSV file.")
    st.code(str(e))
    st.stop()

required_columns = {"Player", "POS", "TOI"}

if not required_columns.issubset(df.columns):
    st.error("CSV file is missing required columns.")
    st.write("Found columns:", list(df.columns))
    st.stop()

# -----------------------------
# Sidebar Controls
# -----------------------------

st.sidebar.header("League Settings")

teams = st.sidebar.number_input(
    "Teams", min_value=8, max_value=20, value=DEFAULT_LEAGUE["teams"]
)

skaters_per_team = st.sidebar.number_input(
    "Skaters per Team",
    min_value=10,
    max_value=20,
    value=DEFAULT_LEAGUE["skaters_per_team"]
)

pool_size = calculate_pool_size(
    teams,
    skaters_per_team,
    DEFAULT_LEAGUE["depth_buffer"]
)

st.sidebar.caption(f"Player pool size: {pool_size}")

st.sidebar.header("Categories")

active_categories = []
for cat in CATEGORIES:
    if cat in df.columns:
        if st.sidebar.checkbox(cat, value=True):
            active_categories.append(cat)

if not active_categories:
    st.warning("Select at least one category.")
    st.stop()

# -----------------------------
# Player Selection
# -----------------------------

player_list = sorted(df["Player"].dropna().unique())

if len(player_list) < 2:
    st.warning("Not enough players in dataset.")
    st.stop()

col1, col2 = st.columns(2)

with col1:
    player1 = st.selectbox("Player 1", player_list)

with col2:
    player2 = st.selectbox("Player 2", player_list)

# -----------------------------
# Normalize Data
# -----------------------------

normalized = normalize(
    df,
    active_categories,
    pool_size,
    DEFAULT_LEAGUE["replacement_percentile"]
)

p1 = df[df["Player"] == player1].iloc[0]
p2 = df[df["Player"] == player2].iloc[0]

pos = p1["POS"]

if pos not in normalized or normalized[pos].empty:
    st.warning(f"No normalized data available for position {pos}.")
    st.stop()

# -----------------------------
# Results
# -----------------------------

p1_score = normalized[pos].loc[p1.name, "TOTAL"]
p2_score = normalized[pos].loc[p2.name, "TOTAL"]

st.subheader("Value vs Replacement (0 = Streamer Level)")

c1, c2 = st.columns(2)
c1.metric(player1, round(p1_score, 2))
c2.metric(player2, round(p2_score, 2))

if st.checkbox("Show category breakdown"):
    breakdown = pd.DataFrame({
        player1: normalized[pos].loc[p1.name, active_categories],
        player2: normalized[pos].loc[p2.name, active_categories]
    })
    st.dataframe(breakdown.style.format("{:.2f}"))
