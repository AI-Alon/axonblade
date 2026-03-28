"""
core/errors.py — AxonBlade error hierarchy (Week 7, Phase 7.1).

All runtime and parse errors derive from AxonError.  Every error carries
line/col and formats a readable message per ProjectPlan.md §11.

Error hierarchy:
    AxonError (base)
    ├── AxonParseError      — syntax errors during lexing/parsing
    ├── AxonRuntimeError    — general runtime failure
    ├── AxonNameError       — undefined variable or attribute
    ├── AxonTypeError       — type annotation mismatch or bad operation
    ├── AxonIndexError      — list/dict index out of bounds
    ├── AxonImportError     — module not found or circular import
    └── AxonDivisionError   — division by zero
"""


class AxonError(Exception):
    """Base class for all AxonBlade errors."""

    error_name: str = "AxonError"

    def __init__(self, message: str, line: int = 0, col: int = 0,
                 source_line: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.line = line
        self.col = col
        self.source_line = source_line

    def format(self) -> str:
        """
        Format the error per §11.2:
            AxonTypeError on line 12, col 8:
              Parameter 'age' expected int, got str

                >> result = greet("Ada", "thirty")
                                            ^
        """
        loc = f" on line {self.line}, col {self.col}" if self.line else ""
        lines = [f"{self.error_name}{loc}:", f"  {self.message}"]
        if self.source_line:
            lines.append("")
            lines.append(f"    {self.source_line}")
            if self.col > 0:
                lines.append("    " + " " * (self.col - 1) + "^")
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.format()

    def to_axon_dict(self) -> dict:
        """Convert to an AxonBlade error dict for catch blocks per §11.3."""
        return {
            "type": self.error_name,
            "message": self.message,
            "line": self.line,
        }


class AxonParseError(AxonError):
    error_name = "AxonParseError"


class AxonRuntimeError(AxonError):
    error_name = "AxonRuntimeError"


class AxonNameError(AxonError):
    error_name = "AxonNameError"


class AxonTypeError(AxonError):
    error_name = "AxonTypeError"


class AxonIndexError(AxonError):
    error_name = "AxonIndexError"


class AxonImportError(AxonError):
    error_name = "AxonImportError"


class AxonDivisionError(AxonError):
    error_name = "AxonDivisionError"
