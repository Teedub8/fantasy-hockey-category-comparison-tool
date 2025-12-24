import streamlit as st
import pandas as pd
import numpy as np
import os
import altair as alt

DATA_PATH = "data/full_nhl_stats.csv"

st.title("Fantasy Hockey Multi-Player & Trade Comparison Dashboard")

# -----------------------------
# Sidebar for league settings
# -----------------------------
st.sidebar.header("League Settings")
league_size = st.sidebar.number_input("Number of teams", min_value=4, max_value=20, value=12)
all_categories = ["goals","assists","points","plusMinus","shots"]
selected_categories = st.sidebar.multiselect("Select categories to compare", all_categories, default=all_categories)

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
# Helper functions
# -----------------------------
def highlight_comparison(row):
    styles = [''] * len(row)
    try:
        a_idx = row.index.get_loc("Side A")
        b_idx = row.index.get_loc("Side B")
        if row["Side A"] > row["Side B"]:
            styles[a_idx] = 'background-color: lightgreen'
        elif row["Side B"] > row["Side A"]:
            styles[b_idx] = 'background-color: lightgreen'
    except KeyError:
        pass
    return styles

def aggregate_z_scores(df, players, numeric_cols):
    """Compute sum of z-scores for selected players"""
    if not players:
        return pd.Series([0]*len(numeric_cols), index=numeric_cols)
    z_scores = (df[numeric_cols] - df[numeric_cols].mean()) / df[numeric_cols].std()
    return z_scores[df['name'].isin(players)].sum()

def compute_percentiles(df, side_values, numeric_cols):
    """Percentile per stat, 0-100"""
    percentiles = []
    for i, col in enumerate(numeric_cols):
        percent = (df[col] <= side_values[i]).mean() * 100
        percentiles.append(percent)
    return percentiles

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

    # -----------------------------
    # Aggregate stats
    # -----------------------------
    side_a_sum = df[df['name'].isin(side_a_selected)][numeric_cols].sum() if side_a_selected else pd.Series([0]*len(numeric_cols), index=numeric_cols)
    side_b_sum = df[df['name'].isin(side_b_selected)][numeric_cols].sum() if side_b_selected else pd.Series([0]*len(numeric_cols), index=numeric_cols)

    # -----------------------------
    # Compute z-scores
    # -----------------------------
    side_a_z = aggregate_z_scores(df, side_a_selected, numeric_cols)
    side_b_z = aggregate_z_scores(df, side_b_selected, numeric_cols)

    # -----------------------------
    # Compute percentiles
    # -----------------------------
    side_a_percentiles = compute_percentiles(df, side_a_sum.values, numeric_cols)
    side_b_percentiles = compute_percentiles(df, side_b_sum.values, numeric_cols)

    # -----------------------------
    # Build comparison dataframe
    # -----------------------------
    comparison_df = pd.DataFrame({
        "Stat": numeric_cols,
        "Side A": side_a_z.values,
        "Percentile - Side A": side_a_percentiles,
        "Side B": side_b_z.values,
        "Percentile - Side B": side_b_percentiles
    })

    # Show dataframe with highlight
    st.dataframe(comparison_df.style.apply(highlight_comparison, axis=1))

    # -----------------------------
    # Side-by-side bar chart
    # -----------------------------
    chart_df = pd.DataFrame({
        "Stat": numeric_cols * 2,
        "Side": ["Side A"]*len(numeric_cols) + ["Side B"]*len(numeric_cols),
        "Value": list(side_a_z.values) + list(side_b_z.values)
    })

    bar_chart = alt.Chart(chart_df).mark_bar().encode(
        x=alt.X('Stat:N', title='Stat'),
        y=alt.Y('Value:Q', title='Z-Score Sum'),
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
