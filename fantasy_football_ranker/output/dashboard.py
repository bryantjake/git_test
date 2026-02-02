"""
Premium Streamlit Dashboard for Fantasy Football Rankings.

A beautiful, interactive web dashboard built entirely in Python.
Features:
- Modern dark theme with gradients
- Interactive player cards
- Filterable/sortable tables
- Visual tier breakdowns
- Player comparison tool
- Charts and visualizations
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Optional
from datetime import datetime

from ranking.engine import PlayerRanking, RankingResults

# Page configuration
def configure_page():
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title="Fantasy Football Ranker",
        page_icon="🏈",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom CSS for premium styling
    st.markdown("""
    <style>
    /* Main theme */
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    }

    /* Headers */
    h1, h2, h3 {
        background: linear-gradient(90deg, #00d4ff, #7c3aed);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
    }

    /* Cards */
    .player-card {
        background: linear-gradient(145deg, #1e1e2e, #2d2d44);
        border-radius: 16px;
        padding: 20px;
        margin: 10px 0;
        border: 1px solid rgba(255,255,255,0.1);
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }

    /* Tier badges */
    .tier-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 14px;
    }
    .tier-1 { background: linear-gradient(135deg, #00ff88, #00d4ff); color: #000; }
    .tier-2 { background: linear-gradient(135deg, #00d4ff, #7c3aed); color: #fff; }
    .tier-3 { background: linear-gradient(135deg, #ffd700, #ff8c00); color: #000; }
    .tier-4 { background: linear-gradient(135deg, #ff8c00, #ff4444); color: #fff; }
    .tier-5 { background: linear-gradient(135deg, #ff4444, #ff0000); color: #fff; }

    /* Position badges */
    .pos-qb { background: #e91e63; color: white; }
    .pos-rb { background: #2196f3; color: white; }
    .pos-wr { background: #4caf50; color: white; }
    .pos-te { background: #ff9800; color: white; }

    /* Metrics */
    .metric-box {
        background: rgba(255,255,255,0.05);
        border-radius: 12px;
        padding: 15px;
        text-align: center;
    }
    .metric-value {
        font-size: 28px;
        font-weight: bold;
        background: linear-gradient(90deg, #00d4ff, #7c3aed);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-label {
        font-size: 12px;
        color: #888;
        text-transform: uppercase;
    }

    /* Trend indicators */
    .trend-up { color: #00ff88; }
    .trend-down { color: #ff4444; }
    .trend-stable { color: #888; }

    /* Tables */
    .dataframe {
        background: rgba(255,255,255,0.02) !important;
    }
    .dataframe th {
        background: rgba(124, 58, 237, 0.3) !important;
    }

    /* Sidebar */
    .css-1d391kg {
        background: linear-gradient(180deg, #1a1a2e, #16213e);
    }
    </style>
    """, unsafe_allow_html=True)


def render_header(results: RankingResults):
    """Render the dashboard header."""
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.markdown("# 🏈 Fantasy Football Ranker")
        st.markdown(f"**Week {results.week}** | Season {results.season} | {results.league_format.upper()}")

    with col2:
        st.metric("Total Players", results.total_players)

    with col3:
        st.metric("Last Updated", results.generated_at[:10])


def render_sidebar(results: RankingResults) -> Dict:
    """Render sidebar filters and return selections."""
    st.sidebar.markdown("## 🎛️ Filters")

    # Position filter
    positions = st.sidebar.multiselect(
        "Positions",
        ["QB", "RB", "WR", "TE"],
        default=["QB", "RB", "WR", "TE"]
    )

    # Tier filter
    tiers = st.sidebar.multiselect(
        "Tiers",
        [1, 2, 3, 4, 5, 6],
        default=[1, 2, 3]
    )

    # Team filter
    all_teams = sorted(set(r.team for r in results.overall_rankings))
    teams = st.sidebar.multiselect(
        "Teams",
        all_teams,
        default=[]
    )

    # Risk filter
    max_risk = st.sidebar.slider(
        "Max Risk Score",
        0, 100, 70
    )

    # Injury filter
    healthy_only = st.sidebar.checkbox("Healthy Players Only", value=False)

    st.sidebar.markdown("---")
    st.sidebar.markdown("## 📊 View Options")

    show_details = st.sidebar.checkbox("Show Detailed Metrics", value=True)
    compare_mode = st.sidebar.checkbox("Enable Comparison Mode", value=False)

    return {
        "positions": positions,
        "tiers": tiers,
        "teams": teams,
        "max_risk": max_risk,
        "healthy_only": healthy_only,
        "show_details": show_details,
        "compare_mode": compare_mode,
    }


def filter_rankings(
    rankings: List[PlayerRanking],
    filters: Dict
) -> List[PlayerRanking]:
    """Apply filters to rankings."""
    filtered = rankings

    if filters["positions"]:
        filtered = [r for r in filtered if r.position in filters["positions"]]

    if filters["tiers"]:
        filtered = [r for r in filtered if r.tier in filters["tiers"]]

    if filters["teams"]:
        filtered = [r for r in filtered if r.team in filters["teams"]]

    filtered = [r for r in filtered if r.risk_score <= filters["max_risk"]]

    if filters["healthy_only"]:
        filtered = [r for r in filtered if r.injury_status == "Healthy"]

    return filtered


def render_player_card(ranking: PlayerRanking):
    """Render a premium player card."""
    tier_class = f"tier-{min(ranking.tier, 5)}"
    pos_class = f"pos-{ranking.position.lower()}"

    trend_icon = {"up": "▲", "down": "▼", "stable": "━"}.get(ranking.trending, "━")
    trend_class = f"trend-{ranking.trending}"

    st.markdown(f"""
    <div class="player-card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <span class="tier-badge {tier_class}">Tier {ranking.tier}</span>
                <span class="tier-badge {pos_class}" style="margin-left: 8px;">{ranking.position}</span>
            </div>
            <div style="font-size: 24px; font-weight: bold;">#{ranking.overall_rank}</div>
        </div>
        <h3 style="margin: 15px 0 5px 0;">{ranking.name}</h3>
        <p style="color: #888; margin: 0;">{ranking.team} | Pos Rank #{ranking.position_rank}</p>

        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-top: 20px;">
            <div class="metric-box">
                <div class="metric-value">{ranking.projected_points:.1f}</div>
                <div class="metric-label">Projected</div>
            </div>
            <div class="metric-box">
                <div class="metric-value">{ranking.composite_score:.0f}</div>
                <div class="metric-label">Score</div>
            </div>
            <div class="metric-box">
                <div class="metric-value">{ranking.floor:.1f}-{ranking.ceiling:.1f}</div>
                <div class="metric-label">Range</div>
            </div>
            <div class="metric-box">
                <div class="metric-value {trend_class}">{trend_icon}</div>
                <div class="metric-label">Trend</div>
            </div>
        </div>

        <div style="margin-top: 15px; display: flex; gap: 20px; color: #888; font-size: 14px;">
            <span>VORP: {ranking.vorp_score:.0f}</span>
            <span>Opportunity: {ranking.opportunity_score:.0f}</span>
            <span>Risk: {ranking.risk_score:.0f}</span>
            <span>Status: {ranking.injury_status}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_rankings_table(rankings: List[PlayerRanking], show_details: bool = True):
    """Render rankings as a styled dataframe."""
    data = []
    for r in rankings:
        row = {
            "Rank": r.overall_rank,
            "Tier": r.tier,
            "Player": r.name,
            "Pos": r.position,
            "Team": r.team,
            "Projected": r.projected_points,
            "Score": r.composite_score,
        }
        if show_details:
            row.update({
                "VORP": r.vorp_score,
                "Opp": r.opportunity_score,
                "Risk": r.risk_score,
                "Floor": r.floor,
                "Ceiling": r.ceiling,
                "Trend": r.trending.upper(),
                "Status": r.injury_status,
            })
        data.append(row)

    df = pd.DataFrame(data)

    # Style the dataframe
    def style_tier(val):
        colors = {1: "#00ff88", 2: "#00d4ff", 3: "#ffd700", 4: "#ff8c00", 5: "#ff4444", 6: "#ff0000"}
        return f"background-color: {colors.get(val, '#333')}20; color: {colors.get(val, '#fff')}"

    def style_position(val):
        colors = {"QB": "#e91e63", "RB": "#2196f3", "WR": "#4caf50", "TE": "#ff9800"}
        return f"background-color: {colors.get(val, '#333')}40"

    def style_trend(val):
        colors = {"UP": "#00ff88", "DOWN": "#ff4444", "STABLE": "#888"}
        return f"color: {colors.get(val, '#fff')}"

    styled = df.style.applymap(style_tier, subset=["Tier"])
    styled = styled.applymap(style_position, subset=["Pos"])
    if show_details and "Trend" in df.columns:
        styled = styled.applymap(style_trend, subset=["Trend"])

    st.dataframe(styled, use_container_width=True, height=600)


def render_tier_chart(results: RankingResults, position: str):
    """Render a visual tier breakdown chart."""
    rankings = results.get_position_rankings(position)
    if not rankings:
        return

    # Create scatter plot with tiers
    data = []
    for r in rankings[:30]:
        data.append({
            "Player": r.name,
            "Tier": r.tier,
            "Score": r.composite_score,
            "Projected": r.projected_points,
            "Risk": r.risk_score,
        })

    df = pd.DataFrame(data)

    fig = px.scatter(
        df,
        x="Score",
        y="Projected",
        color="Tier",
        size="Risk",
        hover_name="Player",
        color_continuous_scale="Viridis",
        title=f"{position} Tier Distribution",
    )

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#fff",
    )

    st.plotly_chart(fig, use_container_width=True)


def render_comparison(players: List[PlayerRanking]):
    """Render player comparison view."""
    if len(players) < 2:
        st.warning("Select at least 2 players to compare")
        return

    cols = st.columns(len(players))

    for col, player in zip(cols, players):
        with col:
            render_player_card(player)

    # Comparison chart
    metrics = ["composite_score", "vorp_score", "opportunity_score", "matchup_score", "risk_score"]
    metric_labels = ["Composite", "VORP", "Opportunity", "Matchup", "Risk"]

    fig = go.Figure()

    for player in players:
        values = [getattr(player, m) for m in metrics]
        values.append(values[0])  # Close the radar

        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=metric_labels + [metric_labels[0]],
            fill="toself",
            name=player.name,
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100]),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=True,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#fff",
    )

    st.plotly_chart(fig, use_container_width=True)


def run_dashboard(results: RankingResults):
    """Main dashboard entry point."""
    configure_page()

    # Header
    render_header(results)
    st.markdown("---")

    # Sidebar
    filters = render_sidebar(results)

    # Main content
    if filters["compare_mode"]:
        st.markdown("## 🔄 Player Comparison")
        st.info("Select players from the table below to compare")

        # Allow selection
        filtered = filter_rankings(results.overall_rankings, filters)
        player_names = [r.name for r in filtered[:50]]
        selected = st.multiselect("Select Players", player_names, max_selections=4)

        if selected:
            selected_players = [r for r in filtered if r.name in selected]
            render_comparison(selected_players)

    else:
        # Tab navigation
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Overall", "🎯 QBs", "🏃 RBs", "🙌 WRs", "🤲 TEs"])

        with tab1:
            st.markdown("## Overall Rankings")
            filtered = filter_rankings(results.overall_rankings, filters)
            render_rankings_table(filtered, filters["show_details"])

        with tab2:
            st.markdown("## Quarterback Rankings")
            filtered = filter_rankings(results.qb_rankings, {**filters, "positions": ["QB"]})
            render_rankings_table(filtered, filters["show_details"])
            render_tier_chart(results, "QB")

        with tab3:
            st.markdown("## Running Back Rankings")
            filtered = filter_rankings(results.rb_rankings, {**filters, "positions": ["RB"]})
            render_rankings_table(filtered, filters["show_details"])
            render_tier_chart(results, "RB")

        with tab4:
            st.markdown("## Wide Receiver Rankings")
            filtered = filter_rankings(results.wr_rankings, {**filters, "positions": ["WR"]})
            render_rankings_table(filtered, filters["show_details"])
            render_tier_chart(results, "WR")

        with tab5:
            st.markdown("## Tight End Rankings")
            filtered = filter_rankings(results.te_rankings, {**filters, "positions": ["TE"]})
            render_rankings_table(filtered, filters["show_details"])
            render_tier_chart(results, "TE")

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666;'>"
        "Fantasy Football Ranker | Built with Python 🐍"
        "</div>",
        unsafe_allow_html=True
    )


# Entry point for Streamlit
if __name__ == "__main__":
    # Demo with sample data
    st.error("Run with: streamlit run output/dashboard.py")
