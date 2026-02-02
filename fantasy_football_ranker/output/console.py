"""
Premium Console Output using Rich.

Beautiful terminal-based display of fantasy football rankings with:
- Styled tables with colors and formatting
- Progress bars and spinners
- Player cards with detailed stats
- Tier visualizations
- Live updating dashboards
"""
from typing import List, Dict, Optional, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.layout import Layout
from rich.live import Live
from rich.style import Style
from rich.box import ROUNDED, HEAVY, DOUBLE_EDGE, MINIMAL
from rich import box

from ranking.engine import PlayerRanking, RankingResults


# Premium color scheme
COLORS = {
    "gold": "#FFD700",
    "silver": "#C0C0C0",
    "bronze": "#CD7F32",
    "tier1": "#00FF00",  # Elite - Green
    "tier2": "#90EE90",  # Great - Light Green
    "tier3": "#FFFF00",  # Good - Yellow
    "tier4": "#FFA500",  # Average - Orange
    "tier5": "#FF6347",  # Below Avg - Tomato
    "tier6": "#FF0000",  # Risky - Red
    "up": "#00FF00",
    "down": "#FF0000",
    "stable": "#808080",
    "qb": "#E91E63",
    "rb": "#2196F3",
    "wr": "#4CAF50",
    "te": "#FF9800",
    "header": "#9C27B0",
    "accent": "#00BCD4",
}

POSITION_STYLES = {
    "QB": Style(color=COLORS["qb"], bold=True),
    "RB": Style(color=COLORS["rb"], bold=True),
    "WR": Style(color=COLORS["wr"], bold=True),
    "TE": Style(color=COLORS["te"], bold=True),
}

TIER_COLORS = {
    1: COLORS["tier1"],
    2: COLORS["tier2"],
    3: COLORS["tier3"],
    4: COLORS["tier4"],
    5: COLORS["tier5"],
    6: COLORS["tier6"],
}


class PremiumConsole:
    """Premium console output for fantasy rankings."""

    def __init__(self):
        """Initialize console."""
        self.console = Console()

    def print_header(self, text: str, subtitle: str = "") -> None:
        """Print a styled header."""
        header_text = Text()
        header_text.append("🏈 ", style="bold")
        header_text.append(text, style=f"bold {COLORS['header']}")

        if subtitle:
            header_text.append(f"\n{subtitle}", style="dim italic")

        panel = Panel(
            header_text,
            box=DOUBLE_EDGE,
            border_style=COLORS["accent"],
            padding=(1, 2),
        )
        self.console.print(panel)
        self.console.print()

    def print_rankings_table(
        self,
        rankings: List[PlayerRanking],
        title: str = "Player Rankings",
        show_details: bool = True,
    ) -> None:
        """
        Print a premium styled rankings table.

        Args:
            rankings: List of PlayerRanking objects
            title: Table title
            show_details: Whether to show detailed columns
        """
        table = Table(
            title=f"[bold {COLORS['header']}]{title}[/]",
            box=ROUNDED,
            header_style=f"bold {COLORS['accent']}",
            border_style=COLORS["accent"],
            show_lines=True,
            padding=(0, 1),
        )

        # Add columns
        table.add_column("Rank", justify="center", style="bold", width=6)
        table.add_column("Tier", justify="center", width=5)
        table.add_column("Player", justify="left", min_width=20)
        table.add_column("Pos", justify="center", width=5)
        table.add_column("Team", justify="center", width=6)
        table.add_column("Proj", justify="right", width=7)

        if show_details:
            table.add_column("Score", justify="right", width=7)
            table.add_column("VORP", justify="right", width=6)
            table.add_column("Opp", justify="right", width=6)
            table.add_column("Risk", justify="right", width=6)
            table.add_column("Floor", justify="right", width=6)
            table.add_column("Ceil", justify="right", width=6)

        table.add_column("Trend", justify="center", width=6)
        table.add_column("Status", justify="center", width=10)

        for ranking in rankings[:50]:  # Limit to top 50
            # Rank styling (gold/silver/bronze for top 3)
            if ranking.overall_rank == 1:
                rank_style = f"bold {COLORS['gold']}"
                rank_text = "🥇 1"
            elif ranking.overall_rank == 2:
                rank_style = f"bold {COLORS['silver']}"
                rank_text = "🥈 2"
            elif ranking.overall_rank == 3:
                rank_style = f"bold {COLORS['bronze']}"
                rank_text = "🥉 3"
            else:
                rank_style = "bold white"
                rank_text = str(ranking.overall_rank)

            # Tier badge
            tier_color = TIER_COLORS.get(ranking.tier, COLORS["tier4"])
            tier_text = f"[bold {tier_color}]T{ranking.tier}[/]"

            # Position styling
            pos_style = POSITION_STYLES.get(ranking.position, Style())

            # Trend indicator
            if ranking.trending == "up":
                trend = f"[bold {COLORS['up']}]▲ UP[/]"
            elif ranking.trending == "down":
                trend = f"[bold {COLORS['down']}]▼ DN[/]"
            else:
                trend = f"[{COLORS['stable']}]━[/]"

            # Injury status
            status_colors = {
                "Healthy": "green",
                "Questionable": "yellow",
                "Doubtful": "orange1",
                "Out": "red",
                "IR": "red",
            }
            status_color = status_colors.get(ranking.injury_status, "white")
            status = f"[{status_color}]{ranking.injury_status[:8]}[/]"

            # Build row
            row = [
                f"[{rank_style}]{rank_text}[/]",
                tier_text,
                f"[bold]{ranking.name}[/]",
                Text(ranking.position, style=pos_style),
                ranking.team,
                f"[bold cyan]{ranking.projected_points:.1f}[/]",
            ]

            if show_details:
                # Color-code scores
                score_color = self._score_color(ranking.composite_score)
                vorp_color = self._score_color(ranking.vorp_score)
                opp_color = self._score_color(ranking.opportunity_score)
                risk_color = self._risk_color(ranking.risk_score)

                row.extend([
                    f"[{score_color}]{ranking.composite_score:.0f}[/]",
                    f"[{vorp_color}]{ranking.vorp_score:.0f}[/]",
                    f"[{opp_color}]{ranking.opportunity_score:.0f}[/]",
                    f"[{risk_color}]{ranking.risk_score:.0f}[/]",
                    f"{ranking.floor:.1f}",
                    f"[bold]{ranking.ceiling:.1f}[/]",
                ])

            row.extend([trend, status])

            table.add_row(*row)

        self.console.print(table)
        self.console.print()

    def print_position_rankings(
        self,
        results: RankingResults,
        positions: List[str] = None,
    ) -> None:
        """
        Print rankings split by position.

        Args:
            results: RankingResults object
            positions: Positions to display (default: all)
        """
        if positions is None:
            positions = ["QB", "RB", "WR", "TE"]

        for pos in positions:
            rankings = results.get_position_rankings(pos)
            if rankings:
                emoji = {"QB": "🎯", "RB": "🏃", "WR": "🙌", "TE": "🤲"}.get(pos, "🏈")
                self.print_rankings_table(
                    rankings[:20],
                    title=f"{emoji} {pos} Rankings",
                    show_details=True,
                )

    def print_player_card(self, ranking: PlayerRanking) -> None:
        """
        Print a detailed player card.

        Args:
            ranking: PlayerRanking object
        """
        pos_color = COLORS.get(ranking.position.lower(), COLORS["accent"])
        tier_color = TIER_COLORS.get(ranking.tier, COLORS["tier4"])

        # Header
        header = Text()
        header.append(f"{ranking.name}", style=f"bold {pos_color}")
        header.append(f"  #{ranking.overall_rank}", style="dim")

        # Build card content
        content = Text()

        # Basic info line
        content.append(f"{ranking.position} | {ranking.team}", style="bold")
        content.append(f"  Tier {ranking.tier}\n", style=f"bold {tier_color}")

        # Projection line
        content.append("\n📊 Projection: ", style="dim")
        content.append(f"{ranking.projected_points:.1f}", style="bold cyan")
        content.append(f"  (Floor: {ranking.floor:.1f} | Ceiling: {ranking.ceiling:.1f})\n", style="dim")

        # Score breakdown
        content.append("\n📈 Scores:\n", style="bold")
        content.append(f"   Composite: ")
        content.append(f"{ranking.composite_score:.0f}", style=f"bold {self._score_color(ranking.composite_score)}")
        content.append(f"\n   VORP: ")
        content.append(f"{ranking.vorp_score:.0f}", style=f"{self._score_color(ranking.vorp_score)}")
        content.append(f"  |  Opportunity: ")
        content.append(f"{ranking.opportunity_score:.0f}", style=f"{self._score_color(ranking.opportunity_score)}")
        content.append(f"  |  Matchup: ")
        content.append(f"{ranking.matchup_score:.0f}", style=f"{self._score_color(ranking.matchup_score)}")
        content.append(f"\n   Risk: ")
        content.append(f"{ranking.risk_score:.0f}", style=f"{self._risk_color(ranking.risk_score)}")

        # Trend
        content.append(f"\n\n🔥 Trending: ", style="bold")
        if ranking.trending == "up":
            content.append("▲ UP", style=f"bold {COLORS['up']}")
        elif ranking.trending == "down":
            content.append("▼ DOWN", style=f"bold {COLORS['down']}")
        else:
            content.append("━ STABLE", style=COLORS["stable"])

        # Status
        content.append(f"  |  Status: ", style="dim")
        status_color = "green" if ranking.injury_status == "Healthy" else "yellow"
        content.append(f"{ranking.injury_status}", style=status_color)

        panel = Panel(
            content,
            title=header,
            box=ROUNDED,
            border_style=pos_color,
            padding=(1, 2),
        )

        self.console.print(panel)
        self.console.print()

    def print_tier_visualization(
        self,
        results: RankingResults,
        position: str = "RB",
    ) -> None:
        """
        Print a visual tier breakdown.

        Args:
            results: RankingResults object
            position: Position to show tiers for
        """
        tiers = results.tiers.get(position, [])

        self.console.print(f"\n[bold {COLORS['header']}]📊 {position} Tier Breakdown[/]\n")

        for tier_num, tier_players in enumerate(tiers, 1):
            if not tier_players:
                continue

            tier_color = TIER_COLORS.get(tier_num, COLORS["tier4"])

            # Tier header
            avg_score = sum(p.composite_score for p in tier_players) / len(tier_players)
            self.console.print(
                f"[bold {tier_color}]━━━ TIER {tier_num} ━━━[/] "
                f"[dim]({len(tier_players)} players, avg score: {avg_score:.0f})[/]"
            )

            # Player list
            for player in tier_players:
                trend_icon = {"up": "▲", "down": "▼", "stable": "━"}.get(player.trending, "━")
                trend_color = {"up": COLORS["up"], "down": COLORS["down"]}.get(player.trending, COLORS["stable"])

                self.console.print(
                    f"  [{tier_color}]●[/] "
                    f"[bold]{player.name}[/] "
                    f"[dim]({player.team})[/] "
                    f"- [cyan]{player.projected_points:.1f}[/] pts "
                    f"[{trend_color}]{trend_icon}[/]"
                )

            self.console.print()

    def print_comparison(
        self,
        players: List[PlayerRanking],
    ) -> None:
        """
        Print side-by-side player comparison.

        Args:
            players: List of PlayerRanking objects to compare
        """
        panels = []

        for player in players[:4]:  # Max 4 players
            pos_color = COLORS.get(player.position.lower(), COLORS["accent"])

            content = Text()
            content.append(f"Rank #{player.overall_rank}\n", style="bold")
            content.append(f"Tier {player.tier}\n\n", style=f"bold {TIER_COLORS.get(player.tier)}")
            content.append(f"Projected: {player.projected_points:.1f}\n", style="cyan")
            content.append(f"Floor: {player.floor:.1f}\n", style="dim")
            content.append(f"Ceiling: {player.ceiling:.1f}\n\n", style="bold")
            content.append(f"Score: {player.composite_score:.0f}\n", style=self._score_color(player.composite_score))
            content.append(f"Risk: {player.risk_score:.0f}\n", style=self._risk_color(player.risk_score))

            panel = Panel(
                content,
                title=f"[bold {pos_color}]{player.name}[/]",
                subtitle=f"[dim]{player.position} - {player.team}[/]",
                box=ROUNDED,
                border_style=pos_color,
            )
            panels.append(panel)

        self.console.print(Columns(panels))

    def print_summary(self, results: RankingResults) -> None:
        """Print a summary dashboard."""
        self.print_header(
            f"Fantasy Rankings - Week {results.week}",
            f"Season {results.season} | Format: {results.league_format.upper()}"
        )

        # Quick stats
        stats_table = Table(box=MINIMAL, show_header=False, padding=(0, 2))
        stats_table.add_column("Stat", style="dim")
        stats_table.add_column("Value", style="bold cyan")

        stats_table.add_row("Total Players", str(results.total_players))
        stats_table.add_row("QBs Ranked", str(len(results.qb_rankings)))
        stats_table.add_row("RBs Ranked", str(len(results.rb_rankings)))
        stats_table.add_row("WRs Ranked", str(len(results.wr_rankings)))
        stats_table.add_row("TEs Ranked", str(len(results.te_rankings)))
        stats_table.add_row("Generated", results.generated_at[:19])

        self.console.print(Panel(stats_table, title="[bold]Summary[/]", box=ROUNDED))
        self.console.print()

    def _score_color(self, score: float) -> str:
        """Get color for a score value."""
        if score >= 80:
            return COLORS["tier1"]
        elif score >= 65:
            return COLORS["tier2"]
        elif score >= 50:
            return COLORS["tier3"]
        elif score >= 35:
            return COLORS["tier4"]
        else:
            return COLORS["tier5"]

    def _risk_color(self, risk: float) -> str:
        """Get color for risk value (inverted - low is good)."""
        if risk <= 25:
            return COLORS["tier1"]
        elif risk <= 40:
            return COLORS["tier2"]
        elif risk <= 55:
            return COLORS["tier3"]
        elif risk <= 70:
            return COLORS["tier4"]
        else:
            return COLORS["tier5"]


def display_rankings(results: RankingResults) -> None:
    """Quick function to display rankings."""
    console = PremiumConsole()
    console.print_summary(results)
    console.print_rankings_table(results.overall_rankings[:30], "Overall Rankings")


def display_position(results: RankingResults, position: str) -> None:
    """Quick function to display position rankings."""
    console = PremiumConsole()
    rankings = results.get_position_rankings(position)
    console.print_rankings_table(rankings, f"{position} Rankings")
