"""Fly-in: main entry point.

Usage:
    python3 main.py <path_to_map_file>
"""

from __future__ import annotations

import sys

from engine.simulation import SimulationEngine
from parser.map_parser import MapParser, ParseError
from pathfinding.dijkstra import Dijkstra


def main() -> int:
    """Parse a map file, compute a route, simulate all drones, print output.

    Returns:
        int: Process exit code (0 on success, 1 on any failure).
    """
    if len(sys.argv) != 2:
        print("usage: python3 main.py <path_to_map_file>", file=sys.stderr)
        return 1

    map_path = sys.argv[1]

    try:
        graph, nb_drones = MapParser().parse(map_path)
    except ParseError as exc:
        print(f"parse error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"could not read map file: {exc}", file=sys.stderr)
        return 1

    start = graph.get_start()
    end = graph.get_end()

    # Look for several distinct routes (capped at 5, and never more
    # than there are drones to spread across them) so drones can be
    # distributed instead of all queuing on one shared bottleneck.
    max_paths = min(nb_drones, 5)
    paths = Dijkstra().find_multiple_paths(graph, start, end, max_paths)
    if not paths:
        print(
            f"error: no route exists from '{start.name}' to '{end.name}'",
            file=sys.stderr,
        )
        return 1

    for i, path in enumerate(paths, start=1):
        print(f"Route {i}: {' -> '.join(path.zone_names)} (cost: {path.total_cost})")
    print(f"Drones: {nb_drones}")
    print()

    try:
        engine = SimulationEngine(paths, nb_drones)
        turns = engine.run()
    except (ValueError, RuntimeError) as exc:
        print(f"simulation error: {exc}", file=sys.stderr)
        return 1

    for turn_tokens in turns:
        print(" ".join(turn_tokens))

    print()
    print(f"Total simulation turns: {len(turns)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
