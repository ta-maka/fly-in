"""TerminalVisualizer: colored terminal output for the simulation."""

from __future__ import annotations

from typing import Dict, List

from models.graph import Graph
from models.zone import Zone
from models.zone_type import ZoneType

_RESET = "\033[0m"
_BOLD = "\033[1m"

# Maps the free-form color names a map file may declare (e.g. "color=red")
# to actual ANSI foreground color codes.
_NAMED_COLORS: Dict[str, str] = {
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "gray": "\033[90m",
    "grey": "\033[90m",
}

# Fallback color per zone type, used whenever a zone did not declare
# its own color= metadata.
_ZONE_TYPE_COLORS: Dict[ZoneType, str] = {
    ZoneType.NORMAL: "\033[32m",       # green
    ZoneType.PRIORITY: "\033[36m",     # cyan
    ZoneType.RESTRICTED: "\033[33m",   # yellow
    ZoneType.BLOCKED: "\033[90m",      # gray
}

_DRONE_ID_COLOR = "\033[1;35m"  # bold magenta


class TerminalVisualizer:
    """Renders colored terminal output for zones and simulation turns."""

    def zone_color(self, zone: Zone) -> str:
        """Return the ANSI color code that represents a zone.

        Uses the zone's declared color if it's a recognized name,
        otherwise falls back to a color based on the zone's type.

        Args:
            zone: The zone to pick a color for.

        Returns:
            str: An ANSI color escape code.
        """
        if zone.color is not None:
            named = _NAMED_COLORS.get(zone.color.lower())
            if named is not None:
                return named
        return _ZONE_TYPE_COLORS[zone.zone_type]

    def colorize_zone_name(self, zone: Zone) -> str:
        """Return a zone's name wrapped in its ANSI color code.

        Args:
            zone: The zone to render.

        Returns:
            str: The colorized zone name, reset afterward.
        """
        return f"{self.zone_color(zone)}{zone.name}{_RESET}"

    def print_legend(self, graph: Graph) -> None:
        """Print a legend explaining zone type colors.

        Args:
            graph: The graph being visualized (unused directly, kept
                for a consistent visualizer interface).
        """
        print(f"{_BOLD}Legend:{_RESET}")
        for zone_type, color in _ZONE_TYPE_COLORS.items():
            print(f"  {color}{zone_type.value}{_RESET}")
        print(f"  {_DRONE_ID_COLOR}D<id>{_RESET}  drone identifier")
        print()

    def print_route_summary(self, graph: Graph, route_zone_names: List[str]) -> None:
        """Print one route as an arrow-joined, colorized chain of zones.

        Args:
            graph: The graph the route belongs to.
            route_zone_names: The ordered zone names making up the route.
        """
        colored_parts = [
            self.colorize_zone_name(graph.zones[name]) for name in route_zone_names
        ]
        print(" -> ".join(colored_parts))

    def colorize_turn_line(
        self, graph: Graph, tokens: List[str]
    ) -> str:
        """Return one turn's movement tokens, colorized.

        Each token has the form "D<id>-<target>", where <target> is
        either a zone name or, for a drone still crossing into a
        restricted zone, a connection name. Zone-name targets are
        colored by zone; connection-name targets are shown in gray
        to visually distinguish "still in flight" from "arrived".

        Args:
            graph: The graph the tokens' targets belong to.
            tokens: The raw movement tokens for this turn.

        Returns:
            str: The turn's tokens, space-separated, colorized.
        """
        rendered = []
        for token in tokens:
            drone_id, _, target = token.partition("-")
            colored_target = self._colorize_target(graph, target)
            rendered.append(f"{_DRONE_ID_COLOR}{drone_id}{_RESET}-{colored_target}")
        return " ".join(rendered)

    def _colorize_target(self, graph: Graph, target: str) -> str:
        """Colorize a single movement token's target (zone or connection).

        Args:
            graph: The graph the target belongs to.
            target: Either a zone name or a connection name.

        Returns:
            str: The colorized target text.
        """
        zone = graph.zones.get(target)
        if zone is not None:
            return self.colorize_zone_name(zone)
        # Not a zone name: this is a connection name (drone still in
        # flight toward a restricted zone). Render it in gray.
        return f"{_NAMED_COLORS['gray']}{target}{_RESET}"
