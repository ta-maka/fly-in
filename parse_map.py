"""Command-line entry point to parse a map file and inspect the result.

Usage:
    python3 parse_map.py <path_to_map_file>
"""

from __future__ import annotations

import sys

from parser.map_parser import MapParser, ParseError


def main() -> int:
    """Parse the map file given as the first CLI argument.

    Returns:
        int: Process exit code (0 on success, 1 on failure).
    """
    if len(sys.argv) != 2:
        print("usage: python3 parse_map.py <path_to_map_file>", file=sys.stderr)
        return 1

    path = sys.argv[1]

    try:
        graph, nb_drones = MapParser().parse(path)
    except ParseError as exc:
        print(f"parse error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"could not read file: {exc}", file=sys.stderr)
        return 1

    print(f"nb_drones: {nb_drones}")
    print(f"start: {graph.get_start().name}")
    print(f"end: {graph.get_end().name}")
    print(f"zones ({len(graph.zones)}):")
    for zone in graph.zones.values():
        print(f"  {zone}")
    print(f"connections ({len(graph.connections)}):")
    for connection in graph.connections:
        print(f"  {connection}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
