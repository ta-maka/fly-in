"""Graph: the full network of zones and connections."""

from __future__ import annotations

from typing import Dict, List, Optional

from models.connection import Connection
from models.zone import Zone


class Graph:
    """Holds the complete zone network and adjacency information.

    Attributes:
        zones: Mapping of zone name to Zone object.
        connections: List of all Connection objects in the graph.
    """

    def __init__(self) -> None:
        """Initialize an empty Graph."""
        self.zones: Dict[str, Zone] = {}
        self.connections: List[Connection] = []
        self._adjacency: Dict[str, List[Connection]] = {}
        self._start_name: Optional[str] = None
        self._end_name: Optional[str] = None

    def add_zone(self, zone: Zone) -> None:
        """Add a zone to the graph.

        Args:
            zone: The Zone to register.

        Raises:
            ValueError: If a zone with the same name already exists.
        """
        if zone.name in self.zones:
            raise ValueError(f"duplicate zone name '{zone.name}'")
        self.zones[zone.name] = zone
        self._adjacency[zone.name] = []
        if zone.is_start:
            if self._start_name is not None:
                raise ValueError("multiple start_hub zones defined")
            self._start_name = zone.name
        if zone.is_end:
            if self._end_name is not None:
                raise ValueError("multiple end_hub zones defined")
            self._end_name = zone.name

    def add_connection(self, connection: Connection) -> None:
        """Add a connection to the graph.

        Args:
            connection: The Connection to register.

        Raises:
            ValueError: If an identical connection already exists
                (order-independent, so a-b and b-a both count).
        """
        for existing in self.connections:
            if existing.connects(connection.zone_a.name, connection.zone_b.name):
                raise ValueError(
                    f"duplicate connection between "
                    f"'{connection.zone_a.name}' and '{connection.zone_b.name}'"
                )
        self.connections.append(connection)
        self._adjacency[connection.zone_a.name].append(connection)
        self._adjacency[connection.zone_b.name].append(connection)

    def neighbors(self, zone_name: str) -> List[Connection]:
        """Return the connections attached to a given zone.

        Args:
            zone_name: The zone whose connections to look up.

        Returns:
            List[Connection]: All connections touching this zone.
        """
        return self._adjacency.get(zone_name, [])

    def get_start(self) -> Zone:
        """Return the unique start zone.

        Returns:
            Zone: The start_hub zone.

        Raises:
            ValueError: If no start zone has been set.
        """
        if self._start_name is None:
            raise ValueError("graph has no start_hub zone")
        return self.zones[self._start_name]

    def get_end(self) -> Zone:
        """Return the unique end zone.

        Returns:
            Zone: The end_hub zone.

        Raises:
            ValueError: If no end zone has been set.
        """
        if self._end_name is None:
            raise ValueError("graph has no end_hub zone")
        return self.zones[self._end_name]

    def __repr__(self) -> str:
        """Return a debug representation of the graph."""
        return (
            f"Graph(zones={len(self.zones)}, "
            f"connections={len(self.connections)})"
        )
