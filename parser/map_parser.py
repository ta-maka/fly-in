"""Parser for the Fly-in map file format.

Converts a text description of zones and connections into a
validated Graph object, or raises ParseError with a precise
line number and reason if the file is malformed.
"""

from __future__ import annotations

from typing import Dict, Tuple

from models.connection import Connection
from models.graph import Graph
from models.zone import Zone
from models.zone_type import ZoneType

# Allowed section order in the file: drone count, then zones, then connections.
_STAGE_BEFORE_DRONES = "before_drones"
_STAGE_ZONES = "zones"
_STAGE_CONNECTIONS = "connections"

# The only metadata keys allowed inside each kind of [...] block.
_ZONE_METADATA_KEYS = ("zone", "color", "max_drones")
_CONNECTION_METADATA_KEYS = ("max_link_capacity",)


class ParseError(Exception):
    """Raised when the map file is malformed.

    Attributes:
        line_number: The 1-indexed line where the problem occurred.
        reason: A human-readable explanation of the problem.
    """

    def __init__(self, line_number: int, reason: str) -> None:
        """Initialize a ParseError.

        Args:
            line_number: The 1-indexed offending line.
            reason: Description of what went wrong.
        """
        self.line_number = line_number
        self.reason = reason
        super().__init__(f"line {line_number}: {reason}")


class MapParser:
    """Parses a Fly-in map file into a Graph and a drone count.

    Every piece of parsing logic lives as a method on this class,
    including the small string-handling helpers, so the parser is
    fully object-oriented rather than a class wrapping standalone
    module-level functions.
    """

    def parse(self, path: str) -> Tuple[Graph, int]:
        """Parse the map file at the given path.

        Args:
            path: Filesystem path to the map file.

        Returns:
            Tuple[Graph, int]: The validated graph and the number
            of drones declared in the file.

        Raises:
            ParseError: If the file is malformed at any point.
            OSError: If the file cannot be read.
        """
        graph = Graph()
        nb_drones = None
        stage = _STAGE_BEFORE_DRONES

        with open(path, "r", encoding="utf-8") as handle:
            raw_lines = handle.readlines()

        for line_number, raw_line in enumerate(raw_lines, start=1):
            line = self._strip_comment(raw_line).strip()
            if not line:
                continue

            is_zone_line = (
                line.startswith("start_hub:")
                or line.startswith("end_hub:")
                or line.startswith("hub:")
            )
            is_connection_line = line.startswith("connection:")

            if line.startswith("nb_drones:"):
                if stage != _STAGE_BEFORE_DRONES:
                    raise ParseError(
                        line_number,
                        "'nb_drones:' must appear exactly once, as the "
                        "first declaration in the file",
                    )
                nb_drones = self._parse_drone_count(line, line_number)
                stage = _STAGE_ZONES

            elif is_zone_line:
                if stage == _STAGE_BEFORE_DRONES:
                    raise ParseError(
                        line_number,
                        "'nb_drones:' must be declared before any zone",
                    )
                if stage == _STAGE_CONNECTIONS:
                    raise ParseError(
                        line_number,
                        "all zones must be declared before any connection",
                    )
                if line.startswith("start_hub:"):
                    self._parse_zone_line(
                        line, "start_hub:", graph, line_number, is_start=True
                    )
                elif line.startswith("end_hub:"):
                    self._parse_zone_line(
                        line, "end_hub:", graph, line_number, is_end=True
                    )
                else:
                    self._parse_zone_line(line, "hub:", graph, line_number)

            elif is_connection_line:
                if stage == _STAGE_BEFORE_DRONES:
                    raise ParseError(
                        line_number,
                        "'nb_drones:' must be declared before any connection",
                    )
                stage = _STAGE_CONNECTIONS
                self._parse_connection_line(line, graph, line_number)

            else:
                raise ParseError(line_number, f"unrecognized line '{line}'")

        if nb_drones is None:
            raise ParseError(1, "missing required 'nb_drones:' declaration")

        # These raise ParseError-equivalent info via ValueError from Graph;
        # translate to ParseError with a clear top-level message.
        try:
            graph.get_start()
        except ValueError as exc:
            raise ParseError(0, str(exc)) from exc
        try:
            graph.get_end()
        except ValueError as exc:
            raise ParseError(0, str(exc)) from exc

        return graph, nb_drones

    @staticmethod
    def _strip_comment(line: str) -> str:
        """Remove a trailing '#' comment from a line.

        Args:
            line: The raw line, possibly containing a comment.

        Returns:
            str: The line with any comment removed.
        """
        idx = line.find("#")
        if idx == -1:
            return line
        return line[:idx]

    @staticmethod
    def _parse_drone_count(line: str, line_number: int) -> int:
        """Parse the 'nb_drones: <n>' declaration line.

        Args:
            line: The full line, e.g. "nb_drones: 5".
            line_number: The line number, for error reporting.

        Returns:
            int: The number of drones.

        Raises:
            ParseError: If the value is missing or not a positive integer.
        """
        _, _, value = line.partition(":")
        value = value.strip()
        if not value:
            raise ParseError(line_number, "'nb_drones:' requires a value")
        return MapParser._positive_int(value, "nb_drones", line_number)

    def _parse_zone_line(
        self,
        line: str,
        prefix: str,
        graph: Graph,
        line_number: int,
        is_start: bool = False,
        is_end: bool = False,
    ) -> None:
        """Parse a zone definition line and add it to the graph.

        Args:
            line: The full line, e.g. "hub: roof1 3 4 [zone=restricted]".
            prefix: The type prefix already matched ("hub:", etc.).
            graph: The Graph to add the resulting Zone to.
            line_number: The line number, for error reporting.
            is_start: Whether this line defines the start zone.
            is_end: Whether this line defines the end zone.

        Raises:
            ParseError: If the line is malformed or fails validation.
        """
        body = line[len(prefix):].strip()
        main_part, metadata = self._split_metadata(body, line_number)
        self._validate_metadata_keys(metadata, _ZONE_METADATA_KEYS, line_number)

        tokens = main_part.split()
        if len(tokens) != 3:
            raise ParseError(
                line_number,
                f"expected '<name> <x> <y>', got '{main_part}'",
            )
        name, x_str, y_str = tokens
        self._validate_zone_name(name, line_number)

        try:
            x, y = int(x_str), int(y_str)
        except ValueError as exc:
            raise ParseError(
                line_number, f"coordinates must be integers, got '{x_str} {y_str}'"
            ) from exc

        zone_type_str = metadata.get("zone", "normal")
        try:
            zone_type = ZoneType.from_string(zone_type_str)
        except ValueError as exc:
            raise ParseError(line_number, str(exc)) from exc

        color = metadata.get("color")

        if "max_drones" in metadata and not (is_start or is_end):
            max_drones = self._positive_int(
                metadata["max_drones"], "max_drones", line_number
            )
        else:
            # Ignored (not an error) on start/end zones per spec.
            max_drones = 1

        zone = Zone(
            name=name,
            x=x,
            y=y,
            zone_type=zone_type,
            color=color,
            max_drones=max_drones,
            is_start=is_start,
            is_end=is_end,
        )
        try:
            graph.add_zone(zone)
        except ValueError as exc:
            raise ParseError(line_number, str(exc)) from exc

    def _parse_connection_line(
        self, line: str, graph: Graph, line_number: int
    ) -> None:
        """Parse a connection definition line and add it to the graph.

        Args:
            line: The full line, e.g. "connection: hub-roof1 [max_link_capacity=2]".
            graph: The Graph to add the resulting Connection to.
            line_number: The line number, for error reporting.

        Raises:
            ParseError: If the line is malformed or references unknown zones.
        """
        body = line[len("connection:"):].strip()
        main_part, metadata = self._split_metadata(body, line_number)
        self._validate_metadata_keys(
            metadata, _CONNECTION_METADATA_KEYS, line_number
        )

        if "-" not in main_part:
            raise ParseError(
                line_number, f"expected '<zone1>-<zone2>', got '{main_part}'"
            )
        name_a, _, name_b = main_part.partition("-")
        name_a, name_b = name_a.strip(), name_b.strip()

        if name_a not in graph.zones:
            raise ParseError(line_number, f"unknown zone '{name_a}' in connection")
        if name_b not in graph.zones:
            raise ParseError(line_number, f"unknown zone '{name_b}' in connection")

        if name_a == name_b:
            raise ParseError(
                line_number,
                f"a connection cannot link a zone to itself ('{name_a}')",
            )

        if "max_link_capacity" in metadata:
            capacity = self._positive_int(
                metadata["max_link_capacity"], "max_link_capacity", line_number
            )
        else:
            capacity = 1

        connection = Connection(
            zone_a=graph.zones[name_a],
            zone_b=graph.zones[name_b],
            max_link_capacity=capacity,
        )
        try:
            graph.add_connection(connection)
        except ValueError as exc:
            raise ParseError(line_number, str(exc)) from exc

    @staticmethod
    def _parse_metadata(raw: str, line_number: int) -> Dict[str, str]:
        """Parse a bracketed metadata block into a key-value dict.

        Args:
            raw: The text found between '[' and ']', e.g.
                "zone=restricted color=red max_drones=2".
            line_number: The line this metadata came from, for errors.

        Returns:
            Dict[str, str]: Metadata keys mapped to their raw string values.

        Raises:
            ParseError: If a token inside the brackets is not valid key=value.
        """
        metadata: Dict[str, str] = {}
        tokens = raw.split()

        for token in tokens:
            equals_count = token.count("=")

            if equals_count != 1:
                raise ParseError(line_number, f"invalid metadata token '{token}'")

            parts = token.split("=")
            key = parts[0]
            value = parts[1]

            if len(key) == 0:
                raise ParseError(line_number, f"invalid metadata token '{token}'")

            if len(value) == 0:
                raise ParseError(line_number, f"invalid metadata token '{token}'")

            metadata[key] = value

        return metadata

    @staticmethod
    def _split_metadata(line: str, line_number: int) -> Tuple[str, Dict[str, str]]:
        """Split a line into its main content and optional metadata dict.

        Args:
            line: The full line content after the type prefix.
            line_number: The line number, for error reporting.

        Returns:
            Tuple[str, Dict[str, str]]: The content before any '[...]'
            block, and the parsed metadata (empty dict if none present).

        Raises:
            ParseError: If brackets are unbalanced or malformed.
        """
        if "[" not in line:
            if "]" in line:
                raise ParseError(line_number, "unmatched ']' with no opening '['")
            return line.strip(), {}

        open_idx = line.index("[")
        if not line.rstrip().endswith("]"):
            raise ParseError(line_number, "metadata block missing closing ']'")
        close_idx = line.rindex("]")
        if close_idx < open_idx:
            raise ParseError(line_number, "metadata block missing opening '['")

        main_part = line[:open_idx].strip()
        meta_part = line[open_idx + 1:close_idx].strip()
        metadata = MapParser._parse_metadata(meta_part, line_number)
        return main_part, metadata

    @staticmethod
    def _positive_int(value: str, field_name: str, line_number: int) -> int:
        """Parse a string as a positive integer.

        Args:
            value: The raw string to parse.
            field_name: The metadata field name, for error messages.
            line_number: The line number, for error reporting.

        Returns:
            int: The parsed positive integer.

        Raises:
            ParseError: If the value is not a positive integer.
        """
        try:
            parsed = int(value)
        except ValueError as exc:
            raise ParseError(
                line_number, f"'{field_name}' must be an integer, got '{value}'"
            ) from exc
        if parsed <= 0:
            raise ParseError(
                line_number, f"'{field_name}' must be a positive integer, got {parsed}"
            )
        return parsed

    @staticmethod
    def _validate_metadata_keys(
        metadata: Dict[str, str], allowed_keys: Tuple[str, ...], line_number: int
    ) -> None:
        """Check that every metadata key is one of the allowed keys.

        Args:
            metadata: The parsed key-value metadata dict.
            allowed_keys: The only keys permitted in this context.
            line_number: The line number, for error reporting.

        Raises:
            ParseError: If any key in `metadata` is not in `allowed_keys`.
        """
        for key in metadata:
            if key not in allowed_keys:
                allowed_list = ", ".join(allowed_keys)
                raise ParseError(
                    line_number,
                    f"unknown metadata key '{key}', expected one of: {allowed_list}",
                )

    @staticmethod
    def _validate_zone_name(name: str, line_number: int) -> None:
        """Validate that a zone name uses only allowed characters.

        Zone names must consist only of letters, digits, and underscores.
        This is stricter than just forbidding dashes and spaces: it also
        keeps out characters like '[', ']', '=', and '#' that would
        otherwise break bracket or comment parsing elsewhere in the file.

        Args:
            name: The zone name to validate.
            line_number: The line number, for error reporting.

        Raises:
            ParseError: If the name is empty or contains a disallowed character.
        """
        if len(name) == 0:
            raise ParseError(line_number, "zone name cannot be empty")

        for character in name:
            is_dash = character == "-"
            is_space = character == " "
            if is_dash or is_space:
                raise ParseError(
                    line_number,
                    f"invalid zone name '{name}': only letters, digits",
                )
