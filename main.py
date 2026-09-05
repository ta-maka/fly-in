"""Fly-in: main entry point.

Usage:
    python3 main.py <path_to_map_file>
"""

from __future__ import annotations

import sys

from typing import List

from engine.simulation import SimulationEngine
from parser.map_parser import MapParser, ParseError
from pathfinding.dijkstra import Dijkstra
from visual.terminal_visualizer import TerminalVisualizer


class Application:
    """The Fly-in command-line application.

    Wraps the full parse -> pathfind -> simulate -> display pipeline
    as a single object, so the entry point itself is object-oriented
    rather than a bare module-level function containing all the logic.
    """

    def __init__(self) -> None:
        """Initialize the application's collaborators."""
        self.parser = MapParser()
        self.pathfinder = Dijkstra()
        self.visualizer = TerminalVisualizer()

    def run(self, argv: List[str]) -> int:
        """Run the application with the given command-line arguments.

        Args:
            argv: The full argument list, as from sys.argv (argv[0]
                is the script name, argv[1] is expected to be the
                map file path).

        Returns:
            int: Process exit code (0 on success, 1 on any failure).
        """
        if len(argv) != 2:
            print("usage: python3 main.py <path_to_map_file>", file=sys.stderr)
            return 1

        map_path = argv[1]

        try:
            graph, nb_drones = self.parser.parse(map_path)
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
        paths = self.pathfinder.find_multiple_paths(graph, start, end, max_paths)
        if not paths:
            print(
                f"error: no route exists from '{start.name}' to '{end.name}'",
                file=sys.stderr,
            )
            return 1

        self.visualizer.print_legend(graph)
        print(f"{len(paths)} route(s) found, drones distributed across them:")
        for i, path in enumerate(paths, start=1):
            print(f"  Route {i} (cost {path.total_cost}): ", end="")
            self.visualizer.print_route_summary(graph, path.zone_names)
        print(f"\nDrones: {nb_drones}\n")

        try:
            engine = SimulationEngine(paths, nb_drones)
            turns = engine.run()
        except (ValueError, RuntimeError) as exc:
            print(f"simulation error: {exc}", file=sys.stderr)
            return 1

        print("Simulation output:")
        for turn_tokens in turns:
            print(" ".join(turn_tokens))

        print("\nSimulation output (colorized):")
        for turn_tokens in turns:
            print(self.visualizer.colorize_turn_line(graph, turn_tokens))

        print()
        print(f"Total simulation turns: {len(turns)}")

        return 0


if __name__ == "__main__":
    sys.exit(Application().run(sys.argv))
