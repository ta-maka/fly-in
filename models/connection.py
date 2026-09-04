"""Connection: a bidirectional edge between two zones."""

from __future__ import annotations

from typing import Set

from models.zone import Zone


class Connection:
    """Represents a bidirectional connection (edge) between two zones.

    Attributes:
        zone_a: One endpoint of the connection.
        zone_b: The other endpoint of the connection.
        max_link_capacity: Maximum drones allowed to traverse
            this connection simultaneously.
    """

    def __init__(
        self,
        zone_a: Zone,
        zone_b: Zone,
        max_link_capacity: int = 1,
    ) -> None:
        """Initialize a Connection.

        Args:
            zone_a: One endpoint zone.
            zone_b: The other endpoint zone.
            max_link_capacity: Maximum simultaneous travelers.
        """
        self.zone_a = zone_a
        self.zone_b = zone_b
        self.max_link_capacity = max_link_capacity
        self._travelers: Set[str] = set()

    @property
    def name(self) -> str:
        """Return the canonical display name of this connection.

        Returns:
            str: A string like "zoneA-zoneB", ordered as defined.
        """
        return f"{self.zone_a.name}-{self.zone_b.name}"

    def other_end(self, zone: Zone) -> Zone:
        """Return the endpoint opposite the given zone.

        Args:
            zone: One of this connection's two endpoints.

        Returns:
            Zone: The other endpoint.

        Raises:
            ValueError: If `zone` is not part of this connection.
        """
        if zone is self.zone_a:
            return self.zone_b
        if zone is self.zone_b:
            return self.zone_a
        raise ValueError(f"zone '{zone.name}' is not part of connection {self.name}")

    def connects(self, zone_a_name: str, zone_b_name: str) -> bool:
        """Check whether this connection links the two named zones.

        Args:
            zone_a_name: Name of one zone.
            zone_b_name: Name of the other zone.

        Returns:
            bool: True regardless of the order the names are given in.
        """
        names = {self.zone_a.name, self.zone_b.name}
        return names == {zone_a_name, zone_b_name}

    @property
    def traveler_count(self) -> int:
        """Return how many drones are currently traversing this connection.

        Returns:
            int: Number of drones mid-transit on this connection.
        """
        return len(self._travelers)

    def has_capacity_for(self, extra: int = 1) -> bool:
        """Check whether `extra` more drones can start traversing now.

        Args:
            extra: Number of additional drones attempting to enter.

        Returns:
            bool: True if the connection can accommodate them.
        """
        return self.traveler_count + extra <= self.max_link_capacity

    def add_traveler(self, drone_id: str) -> None:
        """Register a drone as currently traversing this connection.

        Args:
            drone_id: The identifier of the entering drone.

        Raises:
            ValueError: If the connection has no room for this drone.
        """
        if not self.has_capacity_for(1) and drone_id not in self._travelers:
            raise ValueError(
                f"connection '{self.name}' is at capacity "
                f"({self.traveler_count}/{self.max_link_capacity})"
            )
        self._travelers.add(drone_id)

    def remove_traveler(self, drone_id: str) -> None:
        """Remove a drone from this connection's travelers, if present.

        Args:
            drone_id: The identifier of the drone leaving transit.
        """
        self._travelers.discard(drone_id)

    def __repr__(self) -> str:
        """Return a debug representation of the connection."""
        return (
            f"Connection({self.name}, cap={self.max_link_capacity}, "
            f"travelers={self.traveler_count})"
        )
