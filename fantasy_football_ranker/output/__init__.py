"""
Output module for Fantasy Football Ranker.

Premium output options:
- Rich: Beautiful terminal output with colors, tables, and styling
- Streamlit: Interactive web dashboard with charts and filters
"""
from .console import (
    PremiumConsole,
    display_rankings,
    display_position,
)

__all__ = [
    "PremiumConsole",
    "display_rankings",
    "display_position",
]

# Note: Streamlit dashboard should be run via:
#   streamlit run fantasy_football_ranker/output/dashboard.py
