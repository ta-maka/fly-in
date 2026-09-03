"""Zone type definitions and their movement semantics."""

from __future__ import annotations

from enum import Enum


class ZoneType(Enum):
    """Enumerates the possible types a Zone can have.

    Each type carries its own movement cost (in simulation turns)
    and passability rule, which the pathfinding and simulation
    engine both rely on.
    """

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"

    @property
    def movement_cost(self) -> int:
        """Return the number of turns required to move into this zone.

        Returns:
            int: Turn cost to enter a zone of this type.

        Raises:
            ValueError: If called on BLOCKED, which has no valid cost.
        """
        if self is ZoneType.NORMAL:
            return 1
        if self is ZoneType.RESTRICTED:
            return 2
        if self is ZoneType.PRIORITY:
            return 1
        raise ValueError("Blocked zones have no movement cost; they are impassable.")

    @property
    def is_passable(self) -> bool:
        """Return whether a drone may ever enter a zone of this type.

        Returns:
            bool: True if drones can enter, False if the zone is blocked.
        """
        return self is not ZoneType.BLOCKED

    @property
    def is_multi_turn(self) -> bool:
        """Return whether entering this zone requires more than one turn.

        Returns:
            bool: True for RESTRICTED zones (2-turn transit), else False.
        """
        return self is ZoneType.RESTRICTED

    @classmethod
    def from_string(cls, value: str) -> "ZoneType":
        """Parse a zone type from its textual representation.

        Args:
            value: The raw string found in the map file (e.g. "restricted").

        Returns:
            ZoneType: The matching enum member.

        Raises:
            ValueError: If the string does not match a known zone type.
        """
        cleaned_value = value.strip().lower()

        if cleaned_value == "normal":
            return ZoneType.NORMAL
        if cleaned_value == "blocked":
            return ZoneType.BLOCKED
        if cleaned_value == "restricted":
            return ZoneType.RESTRICTED
        if cleaned_value == "priority":
            return ZoneType.PRIORITY

        raise ValueError(
            f"invalid zone type '{value}', "
            "expected one of: normal, blocked, restricted, priority"
        )
