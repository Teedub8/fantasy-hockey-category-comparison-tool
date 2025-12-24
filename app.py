import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import StringIO

st.set_page_config(page_title="Fantasy Hockey Comparison Tool", layout="wide")

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.title("Controls")
league_id_input = st.sidebar.text_input("Enter Yahoo League ID (optional)")
fetch_button = st.sidebar.button("Fetch Live NHL Stats")

# -----------------------------
# Data Fetching
# -----------------------------
@st.cache_data(show_spinner=False)
def fetch_nhl_stats():
    # Example: fetch NHL player stats from a public endpoint
    # For Yahoo league integration, replace with yahoo_fantasy_api fetch using league_id_input
    try:
        url = "https://statsapi.web.nhl.com/api/v1/people?season=20252026"  # placeholder
        # Replace with actual stats fetch
        # Here we simulate a CSV for testing
        csv_data = """
name,goals,assists,points,shots,hits,blocks
Player A,10,15,25,60,20,5
Player B,20,10,30,80,15,8
Player C,5,8,13,40,5,2
Player D,12,18,30,70,22,7
Player E,8,10,18,50,10,3
"""
        df = pd.read_csv(StringIO(csv_data))
        return df
    except Exception as e:
        st.error(f"Failed to fetch NHL stats: {e}")
        return pd.DataFrame()  # empty df on failure

# -----------------------------
# Fetch Data
# -----------------------------
if fetch_button or 'nhl_data' not in st.session_state:
    st.session_state['nhl_data'] = fetch_nhl_stats()

df = st.session_state.get('nhl_data', pd.DataFrame())

if df.empty:
    st.warning("No NHL data available yet. Please fetch data.")
    st.stop()

# -----------------------------
# League Settings
# -----------------------------
# Use mock league settings for replacement-level calculation
league_size = 12
roster_size = 15
numeric_cols = [col for col in df.columns if col != "name"]

# -----------------------------
# Replacement-level calculation
# -----------------------------
def get_replacement_level(df, league_size, roster_size):
    # Sort players by points
    df_sorted = df.sort_values(by='points', ascending=False)
    num_starters = league_size * roster_size
    replacement_pool = df_sorted.iloc[num_starters:]
    return replacement_pool

replacement_pool = get_replacement_level(df, league_size, roster_size)

# -----------------------------
# Z-score calculation
# -----------------------------
def compute_z_scores(df, numeric_cols, replacement_pool):
    mean_vals = replacement_pool[numeric_cols].mean()
    std_vals = replacement_pool[numeric_cols].std().replace(0, 1)  # avoid div by zero
    z_scores = (df[numeric_cols] - mean_vals) / std_vals
    return z_scores.fillna(0)

z_scores_df = compute_z_scores(df, numeric_cols, replacement_pool)

# -----------------------------
# Main App Layout
# -----------------------------
st.title("Fantasy Hockey Player Comparison Tool")

st.markdown("Select players for Side A and Side B:")

# -----------------------------
# Player Selection (main area)
# -----------------------------
side_a_selected = st.multiselect("Side A Player(s)", options=df['name'].tolist(), default=[df['name'].iloc[0]])
side_b_selected = st.multiselect("Side B Player(s)", options=df['name'].tolist(), default=[df['name'].iloc[1]])

# -----------------------------
# Category selection
# -----------------------------
selected_categories = st.multiselect("Select Categories", options=numeric_cols, default=numeric_cols)

# -----------------------------
# Compute Side Aggregates
# -----------------------------
side_a_mask = df['name'].isin(side_a_selected)
side_b_mask = df['name'].isin(side_b_selected)

side_a_stats = df.loc[side_a_mask, selected_categories].sum()
side_b_stats = df.loc[side_b_mask, selected_categories].sum()

side_a_z = z_scores_df.loc[side_a_mask, selected_categories].sum()
side_b_z = z_scores_df.loc[side_b_mask, selected_categories].sum()

# Percentiles
side_a_percentiles = [(df[col] <= side_a_stats[col]).mean()*100 for col in selected_categories]
side_b_percentiles = [(df[col] <= side_b_stats[col]).mean()*100 for col in selected_categories]

# -----------------------------
# Display Comparison Table
# -----------------------------
comparison_df = pd.DataFrame({
    "Category": selected_categories,
    "Side A": side_a_stats.values,
    "Side B": side_b_stats.values,
    "Side A Z": side_a_z.values,
    "Side B Z": side_b_z.values,
    "Side A %ile": side_a_percentiles,
    "Side B %ile": side_b_percentiles
})

def highlight_comparison(row):
    return ['background-color: lightgreen' if row["Side A"] > row["Side B"] else
            'background-color: lightcoral' if row["Side B"] > row["Side A"] else '' 
            for _ in row]

st.dataframe(comparison_df.style.apply(highlight_comparison, axis=1))

# -----------------------------
# Side-by-side bar chart
# -----------------------------
import altair as alt

chart_data = pd.DataFrame({
    "Category": selected_categories * 2,
    "Side": ["Side A"]*len(selected_categories) + ["Side B"]*len(selected_categories),
    "Value": list(side_a_stats.values) + list(side_b_stats.values)
})

chart = alt.Chart(chart_data).mark_bar().encode(
    x=alt.X('Category:N', sort=None),
    y='Value:Q',
    color='Side:N',
    column='Side:N'
)

st.altair_chart(chart, use_container_width=True)
