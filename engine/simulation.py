"""SimulationEngine: turn-based simulation for multiple drones."""

from __future__ import annotations

from typing import Dict, List, Optional

from models.drone import Drone
from pathfinding.path_result import PathResult


class SimulationEngine:
    """Simulates multiple drones, distributed across one or more routes.

    Drones are assigned to the available routes round-robin (D1 on
    route 0, D2 on route 1, D3 back to route 0 if only 2 routes exist,
    and so on), so traffic is spread out instead of every drone
    queuing on a single shared path. Zone and connection capacity are
    still respected exactly as before: a drone that cannot advance
    because its next zone or connection is full simply waits (produces
    no output token) that turn. Since every route shares the same
    underlying Zone and Connection objects, capacity is enforced
    correctly across all drones regardless of which route each one
    is following.

    Drones are processed in a fixed, deterministic order (by
    drone_id) each turn, which is also how "moving out of a zone
    frees capacity the same turn" (per the subject) naturally falls
    out of the implementation: an earlier drone's departure is
    visible to a later drone's capacity check within the same turn.
    """

    def __init__(self, paths: List[PathResult], nb_drones: int) -> None:
        """Initialize the engine with one or more routes and a drone count.

        Args:
            paths: One or more routes drones will be distributed
                across, round-robin, in the order given.
            nb_drones: How many drones to simulate.

        Raises:
            ValueError: If nb_drones is not positive, if `paths` is
                empty, or if any path has no zones.
        """
        if nb_drones <= 0:
            raise ValueError(f"nb_drones must be positive, got {nb_drones}")
        if len(paths) == 0:
            raise ValueError("at least one path is required")
        for path in paths:
            if len(path.zones) == 0:
                raise ValueError("a path has no zones to simulate")

        self.paths = paths
        self.nb_drones = nb_drones
        self.drones: List[Drone] = []
        self._drone_path: Dict[str, PathResult] = {}
        self._path_index: Dict[str, int] = {}

        for i in range(nb_drones):
            drone_id = f"D{i + 1}"
            assigned_path = paths[i % len(paths)]##################
            drone = Drone(drone_id, assigned_path.zones[0])
            self.drones.append(drone)
            self._drone_path[drone_id] = assigned_path
            self._path_index[drone_id] = 0

        self._delivered_count = 0

    def run(self) -> List[List[str]]:
        """Run the simulation to completion.

        Returns:
            List[List[str]]: One entry per simulation turn, each a
            list of movement tokens (e.g. "D1-roof1") for the drones
            that moved that turn, in the exact order they moved.

        Raises:
            RuntimeError: If a turn produces no movement at all while
                drones remain undelivered (an unexpected deadlock).
        """
        turns: List[List[str]] = []

        while self._delivered_count < self.nb_drones:
            turn_tokens = self._simulate_one_turn()
            if not turn_tokens and self._delivered_count < self.nb_drones:
                raise RuntimeError(
                    "deadlock detected: no drone could move this turn"
                )
            turns.append(turn_tokens)

        return turns

    def _simulate_one_turn(self) -> List[str]:
        """Advance every eligible drone by exactly one turn.

        Returns:
            List[str]: The movement tokens produced this turn.
        """
        turn_tokens: List[str] = []

        for drone in self.drones:
            if drone.delivered:
                continue

            if drone.is_in_transit:
                arrival_token = self._complete_transit(drone)
                turn_tokens.append(arrival_token)
                continue

            move_token = self._attempt_move(drone)
            if move_token is not None:
                turn_tokens.append(move_token)

        return turn_tokens

    def _complete_transit(self, drone: Drone) -> str:
        """Finish a drone's mandatory 2-turn restricted-zone crossing.

        Args:
            drone: The drone currently in transit.

        Returns:
            str: The movement token for this turn (the arrival zone name).
        """
        drone.complete_restricted_transit()
        assert drone.current_zone is not None
        self._mark_delivered_if_at_end(drone)
        return f"{drone.drone_id}-{drone.current_zone.name}"

    def _attempt_move(self, drone: Drone) -> Optional[str]:
        """Attempt to advance a drone one step along its path.

        Args:
            drone: The drone to attempt to move.

        Returns:
            str | None: The movement token if the drone moved, or
            None if it had to wait (no capacity available).
        """
        index = self._path_index[drone.drone_id]
        drone_path = self._drone_path[drone.drone_id]
        next_zone = drone_path.zones[index + 1]
        connection = drone_path.connections[index]
        cost = next_zone.zone_type.movement_cost

        if cost == 1:
            if not next_zone.has_capacity_for(1):
                return None
            drone.move_to_adjacent_zone(next_zone)
            self._path_index[drone.drone_id] = index + 1
            self._mark_delivered_if_at_end(drone)
            return f"{drone.drone_id}-{next_zone.name}"

        # Restricted zone: needs both connection capacity AND a
        # reserved seat in the destination zone for the full transit.
        if not connection.has_capacity_for(1) or not next_zone.has_capacity_for(1):
            return None
        drone.enter_restricted_transit(connection, next_zone)
        next_zone.add_occupant(drone.drone_id)  # reserve for the 2-turn crossing
        self._path_index[drone.drone_id] = index + 1
        return f"{drone.drone_id}-{connection.name}"

    def _mark_delivered_if_at_end(self, drone: Drone) -> None:
        """Mark a drone delivered if it has reached its path's final zone.

        Args:
            drone: The drone to check.
        """
        drone_path = self._drone_path[drone.drone_id]
        if drone.current_zone is drone_path.zones[-1]:
            drone.mark_delivered()
            self._delivered_count += 1
