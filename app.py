import streamlit as st
import pandas as pd
import numpy as np
import os
import altair as alt

DATA_PATH = "data/full_nhl_stats.csv"

st.title("Fantasy Hockey Trade & Player Comparison Tool")

# -----------------------------
# Sidebar: league settings
# -----------------------------
st.sidebar.header("League Settings")
league_size = st.sidebar.number_input("Number of teams in your league", min_value=4, max_value=20, value=12)
roster_size = st.sidebar.number_input("Roster spots per team", min_value=10, max_value=20, value=15)
all_categories = ["goals","assists","points","plusMinus","shots","hits","blocks","pim","ppg","shg","gwg"]
st.sidebar.header("Select categories to compare")
category_checks = {}
for cat in all_categories:
    category_checks[cat] = st.sidebar.checkbox(cat, value=True)

# Only keep the selected categories
selected_categories = [cat for cat, checked in category_checks.items() if checked]


# -----------------------------
# Load CSV data
# -----------------------------
if os.path.exists(DATA_PATH):
    df = pd.read_csv(DATA_PATH)
    st.success("Loaded NHL stats from CSV.")
else:
    st.warning("CSV not found. Please upload or fetch data.")
    df = pd.DataFrame()

# -----------------------------
# Functions
# -----------------------------
def highlight_comparison(row):
    styles = [''] * len(row)
    try:
        a_idx = row.index.get_loc("Side A Z")
        b_idx = row.index.get_loc("Side B Z")
        if row["Side A Z"] > row["Side B Z"]:
            styles[a_idx] = 'background-color: lightgreen'
        elif row["Side B Z"] > row["Side A Z"]:
            styles[b_idx] = 'background-color: lightgreen'
    except KeyError:
        pass
    return styles

def get_replacement_level(df, league_size, roster_size):
    total_players = league_size * roster_size
    sorted_df = df.sort_values(by="points", ascending=False)  # or total points/stat you prefer
    replacement_level = sorted_df.iloc[total_players:]
    return replacement_level

def compute_z_scores(df, numeric_cols, replacement_pool):
    mean_vals = replacement_pool[numeric_cols].mean()
    std_vals = replacement_pool[numeric_cols].std()
    z_scores = (df[numeric_cols] - mean_vals) / std_vals
    return z_scores

# -----------------------------
# Multi-player selection
# -----------------------------
if not df.empty:
    player_names = df['name'].tolist()

    st.subheader("Side A Players")
    side_a_input = st.text_input("Search Side A Players (comma-separated)")
    side_a_options = [name for name in player_names if any(n.lower() in name.lower() for n in side_a_input.split(","))] if side_a_input else player_names
    side_a_selected = st.multiselect("Side A Players", side_a_options)

    st.subheader("Side B Players")
    side_b_input = st.text_input("Search Side B Players (comma-separated)")
    side_b_options = [name for name in player_names if any(n.lower() in name.lower() for n in side_b_input.split(","))] if side_b_input else player_names
    side_b_selected = st.multiselect("Side B Players", side_b_options)

    numeric_cols = selected_categories
    replacement_pool = get_replacement_level(df, league_size, roster_size)
    z_scores_df = compute_z_scores(df, numeric_cols, replacement_pool)

    # Aggregate z-scores for each side
    side_a_z = z_scores_df[df['name'].isin(side_a_selected)].sum() if side_a_selected else pd.Series([0]*len(numeric_cols), index=numeric_cols)
    side_b_z = z_scores_df[df['name'].isin(side_b_selected)].sum() if side_b_selected else pd.Series([0]*len(numeric_cols), index=numeric_cols)

    # Percentiles per category (0-100)
    side_a_percentiles = [(df[col] <= side_a_z[col]).mean()*100 for col in numeric_cols]
    side_b_percentiles = [(df[col] <= side_b_z[col]).mean()*100 for col in numeric_cols]

    # Build comparison dataframe
    comparison_df = pd.DataFrame({
        "Stat": numeric_cols,
        "Side A Z": side_a_z.values,
        "Percentile - Side A": side_a_percentiles,
        "Side B Z": side_b_z.values,
        "Percentile - Side B": side_b_percentiles
    })

    # Show dataframe with highlights
    st.dataframe(comparison_df.style.apply(highlight_comparison, axis=1))

    # -----------------------------
    # Side-by-side bar chart
    # -----------------------------
    chart_df = pd.DataFrame({
        "Stat": numeric_cols * 2,
        "Side": ["Side A"]*len(numeric_cols) + ["Side B"]*len(numeric_cols),
        "Z-Score": list(side_a_z.values) + list(side_b_z.values)
    })

    bar_chart = alt.Chart(chart_df).mark_bar().encode(
        x=alt.X('Stat:N', title='Stat'),
        y=alt.Y('Z-Score:Q'),
        color='Side:N',
        xOffset='Side:N'
    )

    st.altair_chart(bar_chart, use_container_width=True)

    # -----------------------------
    # Category wins
    # -----------------------------
    category_wins_a = (side_a_z > side_b_z).sum()
    category_wins_b = (side_b_z > side_a_z).sum()
    category_ties = (side_a_z == side_b_z).sum()

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
