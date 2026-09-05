"""Dijkstra shortest-path search over the drone zone graph.

Built from scratch using only the standard library's heapq module
(a general-purpose priority queue, not a graph library), per the
subject's constraint forbidding graph libraries like networkx.
"""

from __future__ import annotations

import heapq
from typing import Dict, List, Optional, Set, Tuple

from models.connection import Connection
from models.graph import Graph
from models.zone import Zone
from models.zone_type import ZoneType
from pathfinding.path_result import PathResult


class Dijkstra:
    """Computes the lowest-cost route between two zones in a Graph."""

    def find_path(
        self,
        graph: Graph,
        start: Zone,
        end: Zone,
        excluded_connections: Optional[Set[Connection]] = None,
    ) -> Optional[PathResult]:
        """Find the lowest-cost route from `start` to `end`.

        Uses zone movement cost as edge weight. Blocked zones are
        never expanded. Among routes with equal real cost, the
        route passing through more priority zones is preferred.

        Args:
            graph: The graph to search within.
            start: The zone to start from.
            end: The zone to reach.
            excluded_connections: Connections to treat as if they
                did not exist. Used by `find_multiple_paths` to force
                genuinely different routes on each call.

        Returns:
            Optional[PathResult]: The best route found, or None if
            `end` is unreachable from `start`.
        """
        if excluded_connections is None:
            excluded_connections = set()

        best_cost: Dict[str, int] = {start.name: 0}
        best_priority_count: Dict[str, int] = {start.name: 0}
        came_from: Dict[str, Tuple[str, Connection]] = {}
        visited: Set[str] = set()

        # Heap entries: (cost, -priority_count, zone_name)
        # Lower cost wins first; among equal costs, more priority
        # zones visited (larger priority_count, so more negative
        # -priority_count) wins next.
        heap: List[Tuple[int, int, str]] = [(0, 0, start.name)]

        while heap:
            current_cost, neg_priority_count, current_name = heapq.heappop(heap)

            if current_name in visited:
                continue
            visited.add(current_name)

            if current_name == end.name:
                break

            current_zone = graph.zones[current_name]

            for connection in graph.neighbors(current_name):
                if connection in excluded_connections:
                    continue

                neighbor_zone = connection.other_end(current_zone)

                if not neighbor_zone.zone_type.is_passable:
                    continue

                edge_cost = neighbor_zone.zone_type.movement_cost
                candidate_cost = current_cost + edge_cost

                candidate_priority_count = -neg_priority_count
                if neighbor_zone.zone_type is ZoneType.PRIORITY:
                    candidate_priority_count += 1

                is_better = self._is_better_candidate(
                    neighbor_zone.name,
                    candidate_cost,
                    candidate_priority_count,
                    best_cost,
                    best_priority_count,
                )

                if is_better:
                    best_cost[neighbor_zone.name] = candidate_cost
                    best_priority_count[neighbor_zone.name] = candidate_priority_count
                    came_from[neighbor_zone.name] = (current_name, connection)
                    heapq.heappush(
                        heap,
                        (candidate_cost, -candidate_priority_count, neighbor_zone.name),
                    )

        if end.name not in best_cost:
            return None

        return self._build_path_result(graph, start, end, came_from, best_cost[end.name])

    def find_multiple_paths(
        self, graph: Graph, start: Zone, end: Zone, max_paths: int
    ) -> List[PathResult]:
        """Find up to `max_paths` distinct routes from `start` to `end`.

        Each call finds the best remaining route while excluding every
        connection already used by a previously found route, forcing
        genuinely different paths (edge-disjoint where possible) rather
        than the same shortest path repeated. This lets drones be
        distributed across multiple routes instead of all queuing on
        a single shared bottleneck.

        Args:
            graph: The graph to search within.
            start: The zone to start from.
            end: The zone to reach.
            max_paths: The maximum number of distinct routes to find.

        Returns:
            List[PathResult]: Between 0 and `max_paths` routes, ordered
            from best (lowest cost) to worst. Returns fewer than
            `max_paths` if the graph does not have that many distinct
            routes available.
        """
        found_paths: List[PathResult] = []
        excluded_connections: Set[Connection] = set()

        for _ in range(max_paths):
            path = self.find_path(graph, start, end, excluded_connections)
            if path is None:
                break
            found_paths.append(path)
            excluded_connections.update(path.connections)

        return found_paths

    @staticmethod
    def _is_better_candidate(
        zone_name: str,
        candidate_cost: int,
        candidate_priority_count: int,
        best_cost: Dict[str, int],
        best_priority_count: Dict[str, int],
    ) -> bool:
        """Check whether a candidate route to a zone beats the best known one.

        Args:
            zone_name: The zone being reached.
            candidate_cost: Real turn cost of the candidate route.
            candidate_priority_count: Priority zones visited by the candidate.
            best_cost: Best known real cost per zone name so far.
            best_priority_count: Best known priority count per zone name so far.

        Returns:
            bool: True if the candidate route should replace the current best.
        """
        if zone_name not in best_cost:
            return True
        if candidate_cost < best_cost[zone_name]:
            return True
        if candidate_cost > best_cost[zone_name]:
            return False
        # Equal real cost: prefer the route with more priority zones.
        return candidate_priority_count > best_priority_count[zone_name]

    @staticmethod
    def _build_path_result(
        graph: Graph,
        start: Zone,
        end: Zone,
        came_from: Dict[str, Tuple[str, Connection]],
        total_cost: int,
    ) -> PathResult:
        """Reconstruct the full route by walking `came_from` backwards.

        Args:
            graph: The graph the route belongs to.
            start: The route's starting zone.
            end: The route's ending zone.
            came_from: Maps each zone name to (previous zone name,
                connection used to reach it).
            total_cost: The total cost already computed for this route.

        Returns:
            PathResult: The reconstructed route, start to end.
        """
        zones: List[Zone] = [end]
        connections: List[Connection] = []

        current_name = end.name
        while current_name != start.name:
            previous_name, connection = came_from[current_name]
            connections.append(connection)
            zones.append(graph.zones[previous_name])
            current_name = previous_name

        zones.reverse()
        connections.reverse()

        return PathResult(zones=zones, connections=connections, total_cost=total_cost)
