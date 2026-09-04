"""Drone: a single drone's position and transit state."""

from __future__ import annotations

from typing import Optional

from models.connection import Connection
from models.zone import Zone


class Drone:
    """Represents one drone moving through the zone network.

    A Drone is always in exactly one of two states:
      - "at a zone": `current_zone` is set, `transit_connection` is None.
      - "in transit": `current_zone` is None, `transit_connection` and
        `transit_destination` are set. This only happens while crossing
        into a restricted zone, which takes 2 turns and cannot be
        interrupted once started.

    Attributes:
        drone_id: Unique identifier, e.g. "D1".
        current_zone: The zone currently occupied, or None if in transit.
        transit_connection: The connection currently being crossed,
            or None if not in transit.
        transit_destination: The zone being traveled to, or None if
            not in transit.
        delivered: True once this drone has reached the end zone.
    """

    def __init__(self, drone_id: str, start_zone: Zone) -> None:
        """Initialize a Drone at its starting zone.

        Args:
            drone_id: Unique identifier for this drone, e.g. "D1".
            start_zone: The zone this drone begins in.
        """
        self.drone_id = drone_id
        self.current_zone: Optional[Zone] = start_zone
        self.transit_connection: Optional[Connection] = None
        self.transit_destination: Optional[Zone] = None
        self.delivered = False
        start_zone.add_occupant(drone_id)

    @property
    def is_in_transit(self) -> bool:
        """Return whether this drone is mid-crossing a restricted connection.

        Returns:
            bool: True if the drone is currently on a connection,
            not occupying any zone.
        """
        return self.transit_connection is not None

    def move_to_adjacent_zone(self, zone: Zone) -> None:
        """Move directly into a zone in a single turn.

        Used for normal-cost and priority-cost destinations, which
        both take exactly 1 turn to enter.

        Args:
            zone: The destination zone.

        Raises:
            ValueError: If this drone is currently in transit (it
                must finish that transit before making a new move).
        """
        if self.is_in_transit:
            raise ValueError(
                f"drone '{self.drone_id}' is in transit, cannot move directly"
            )
        if self.current_zone is not None:
            self.current_zone.remove_occupant(self.drone_id)
        zone.add_occupant(self.drone_id)
        self.current_zone = zone

    def enter_restricted_transit(
        self, connection: Connection, destination: Zone
    ) -> None:
        """Begin a 2-turn crossing into a restricted zone.

        This is the first of the two turns: the drone leaves its
        current zone and occupies the connection itself. It cannot
        be interrupted; `complete_restricted_transit` must be called
        on the very next turn.

        Args:
            connection: The connection being crossed.
            destination: The restricted zone being traveled to.

        Raises:
            ValueError: If this drone is already in transit.
        """
        if self.is_in_transit:
            raise ValueError(
                f"drone '{self.drone_id}' is already in transit"
            )
        if self.current_zone is not None:
            self.current_zone.remove_occupant(self.drone_id)
        connection.add_traveler(self.drone_id)
        self.transit_connection = connection
        self.transit_destination = destination
        self.current_zone = None

    def complete_restricted_transit(self) -> None:
        """Finish a 2-turn crossing, arriving at the restricted zone.

        This is the second, mandatory turn of the transit: the drone
        leaves the connection and occupies the destination zone.

        Raises:
            ValueError: If this drone is not currently in transit.
        """
        if self.transit_connection is None or self.transit_destination is None:
            raise ValueError(
                f"drone '{self.drone_id}' is not in transit, cannot complete one"
            )
        self.transit_connection.remove_traveler(self.drone_id)
        self.transit_destination.add_occupant(self.drone_id)
        self.current_zone = self.transit_destination
        self.transit_connection = None
        self.transit_destination = None

    def mark_delivered(self) -> None:
        """Mark this drone as having reached the end zone.

        Raises:
            ValueError: If this drone is still in transit.
        """
        if self.is_in_transit:
            raise ValueError(
                f"drone '{self.drone_id}' cannot be delivered while in transit"
            )
        self.delivered = True

    def __repr__(self) -> str:
        """Return a debug representation of the drone."""
        if self.is_in_transit:
            assert self.transit_connection is not None
            location = f"in transit on {self.transit_connection.name}"
        elif self.current_zone is not None:
            location = f"at {self.current_zone.name}"
        else:
            location = "nowhere (invalid state)"
        return f"Drone({self.drone_id}, {location}, delivered={self.delivered})"
