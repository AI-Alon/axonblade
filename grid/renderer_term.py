"""
grid/renderer_term.py — ANSI terminal renderer for AxonGrid (Week 8, Phase 8.3).

Renders the grid to the terminal using ANSI background color codes.
Each tile is 2 characters wide (char + space).

In-place re-render uses cursor-up escape sequence: \033[{rows+1}A
"""

from __future__ import annotations

import sys


_RESET = "\033[0m"


def render_grid(grid: object, in_place: bool = False) -> None:
    """
    Print the full grid to stdout.

    Args:
        grid: An AxonGrid instance.
        in_place: If True, move the cursor up by (rows+1) lines first
                  so this render overwrites the previous one.
    """
    output_parts: list[str] = []

    rows = grid.rows  # type: ignore[attr-defined]
    cols = grid.cols  # type: ignore[attr-defined]
    tiles = grid._tiles  # type: ignore[attr-defined]

    if in_place:
        # Move cursor up to the first row of the previous render
        output_parts.append(f"\033[{rows}A")

    for row in tiles:
        for tile in row:
            color = tile["color"]
            char = tile["char"]
            # Each tile: background color, char, space, reset
            output_parts.append(f"{color}{char} {_RESET}")
        # Reset + carriage return so background doesn't bleed to end of terminal line
        output_parts.append(f"{_RESET}\r\n")

    sys.stdout.write("".join(output_parts))
    sys.stdout.flush()
