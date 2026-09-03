"""Zone: a node in the drone network graph."""

from __future__ import annotations

from typing import Optional, Set

from models.zone_type import ZoneType


class Zone:
    """Represents a single zone (node) in the drone routing graph.

    A Zone knows its static definition (name, coordinates, type,
    capacity) and also tracks which drones currently occupy it,
    since occupancy is inherently a property of the zone itself.

    Attributes:
        name: Unique identifier for this zone.
        x: X coordinate (used for display only).
        y: Y coordinate (used for display only).
        zone_type: The ZoneType governing cost/passability.
        color: Optional display color, or None.
        max_drones: Maximum simultaneous occupants (ignored for
            start/end zones, which are uncapped).
        is_start: True if this is the unique start_hub.
        is_end: True if this is the unique end_hub.
    """

    UNLIMITED_CAPACITY = 10**9

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        zone_type: ZoneType = ZoneType.NORMAL,
        color: Optional[str] = None,
        max_drones: int = 1,
        is_start: bool = False,
        is_end: bool = False,
    ) -> None:
        """Initialize a Zone.

        Args:
            name: Unique zone name.
            x: X coordinate.
            y: Y coordinate.
            zone_type: The type governing cost/passability.
            color: Optional display color.
            max_drones: Occupancy cap (ignored if is_start/is_end,
                which are always treated as having unlimited capacity).
            is_start: Whether this zone is the start hub.
            is_end: Whether this zone is the end hub.
        """
        self.name = name
        self.x = x
        self.y = y
        self.zone_type = zone_type
        self.color = color
        self.is_start = is_start
        self.is_end = is_end
        if is_start or is_end:
            self.max_drones = Zone.UNLIMITED_CAPACITY
        else:
            self.max_drones = max_drones
        self._occupants: Set[str] = set()

    @property
    def is_capacity_unlimited(self) -> bool:
        """Return whether this zone ignores max_drones (start/end zones).

        Returns:
            bool: True if this zone has no effective occupancy cap.
        """
        return self.is_start or self.is_end

    @property
    def occupant_count(self) -> int:
        """Return the current number of drones occupying this zone.

        Returns:
            int: Number of drones currently inside the zone.
        """
        return len(self._occupants)

    def has_capacity_for(self, extra: int = 1) -> bool:
        """Check whether `extra` more drones can enter this zone right now.

        Args:
            extra: Number of additional drones attempting to enter.

        Returns:
            bool: True if the zone can accommodate them.
        """
        if self.is_capacity_unlimited:
            return True
        if not self.zone_type.is_passable:
            return False
        return self.occupant_count + extra <= self.max_drones

    def add_occupant(self, drone_id: str) -> None:
        """Register a drone as currently occupying this zone.

        Args:
            drone_id: The identifier of the entering drone.

        Raises:
            ValueError: If the zone has no room for this drone.
        """
        if not self.has_capacity_for(1) and drone_id not in self._occupants:
            raise ValueError(
                f"zone '{self.name}' is at capacity "
                f"({self.occupant_count}/{self.max_drones})"
            )
        self._occupants.add(drone_id)

    def remove_occupant(self, drone_id: str) -> None:
        """Remove a drone from this zone's occupants, if present.

        Args:
            drone_id: The identifier of the leaving drone.
        """
        self._occupants.discard(drone_id)

    def __repr__(self) -> str:
        """Return a debug representation of the zone."""
        return (
            f"Zone(name={self.name!r}, type={self.zone_type.value}, "
            f"pos=({self.x},{self.y}), max_drones={self.max_drones}, "
            f"occupants={self.occupant_count})"
        )
