"""PathResult: the outcome of a pathfinding search."""

from __future__ import annotations

from typing import List

from models.connection import Connection
from models.zone import Zone


class PathResult:
    """Holds a single computed route through the graph.

    Attributes:
        zones: The ordered sequence of zones from start to end,
            inclusive of both endpoints.
        connections: The ordered sequence of connections traversed
            to move between consecutive zones in `zones`. Has
            exactly one fewer item than `zones`.
        total_cost: The total number of turns this route costs.
    """

    def __init__(
        self,
        zones: List[Zone],
        connections: List[Connection],
        total_cost: int,
    ) -> None:
        """Initialize a PathResult.

        Args:
            zones: Ordered zones from start to end.
            connections: Ordered connections linking those zones.
            total_cost: Total turn cost of this route.
        """
        self.zones = zones
        self.connections = connections
        self.total_cost = total_cost

    @property
    def zone_names(self) -> List[str]:
        """Return the route as a list of zone names, for display/testing.

        Returns:
            List[str]: The zone names in travel order.
        """
        return [zone.name for zone in self.zones]

    def __repr__(self) -> str:
        """Return a debug representation of the path result."""
        route = " -> ".join(self.zone_names)
        return f"PathResult(route={route}, total_cost={self.total_cost})"
