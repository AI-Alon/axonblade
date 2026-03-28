"""
playground/bridge.py — Pyodide bridge for running AxonBlade in the browser
(Week 9, Phases 9.2–9.3).

Exposes a single function:

    run(source: str) -> dict

which returns:
    {
        "output":     str   — captured stdout from the program
        "error":      str   — formatted error message, or "" if no error
        "grid_state": list  — list of {x, y, color_name, char} dicts, or None
    }

Usage in JavaScript via Pyodide:
    const result = await pyodide.runPythonAsync(`
        from playground.bridge import run
        run(source_code)
    `)
    console.log(result.output)
    renderGrid(result.grid_state, canvas)

Grid state serialisation (Phase 9.3):
  Each tile is serialised as {x, y, color_name, char}.
  ANSI background codes are reverse-mapped to AxonBlade color names.
"""

from __future__ import annotations

import io
import sys

from core.errors import AxonError
from core.evaluator import Evaluator
from core.module_loader import load_module
from core.parser import parse_source, ParseError
from stdlib.builtins import build_global_env


# ---------------------------------------------------------------------------
# §9.3 — Reverse map: ANSI background → color name
# ---------------------------------------------------------------------------

_BG_TO_NAME: dict[str, str] = {
    "\033[40m": "black",
    "\033[41m": "red",
    "\033[42m": "green",
    "\033[43m": "yellow",
    "\033[44m": "blue",
    "\033[45m": "magenta",
    "\033[46m": "cyan",
    "\033[47m": "white",
    "\033[0m":  "reset",
}


def _serialize_grid(grid: object) -> list[dict]:
    """
    Serialise an AxonGrid to a JSON-friendly list of tile dicts.

    Each entry: {"x": int, "y": int, "color_name": str, "char": str}
    """
    from grid.grid_object import AxonGrid
    if not isinstance(grid, AxonGrid):
        return []
    tiles: list[dict] = []
    for y in range(grid.rows):
        for x in range(grid.cols):
            ansi = grid.get(x, y)
            char = grid.get_char(x, y)
            color_name = _BG_TO_NAME.get(ansi, "black")
            tiles.append({"x": x, "y": y, "color_name": color_name, "char": char})
    return tiles


def _find_grid(env: object) -> object:
    """Return the first AxonGrid value found in the environment, or None."""
    from grid.grid_object import AxonGrid
    from core.environment import Environment
    if not isinstance(env, Environment):
        return None
    for value in env.store.values():
        if isinstance(value, AxonGrid):
            return value
    return None


# ---------------------------------------------------------------------------
# Phase 9.2 — Main bridge function
# ---------------------------------------------------------------------------

def run(source: str) -> dict:
    """
    Execute AxonBlade source code and return a result dict.

    Returns:
        {
            "output":     str,
            "error":      str,
            "grid_state": list | None,
        }
    """
    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    grid_state = None
    error_str = ""

    try:
        ev = Evaluator()
        global_env = build_global_env()

        # Wire module loader
        ev._module_loader = lambda name, _line: load_module(
            name, None, ev, build_global_env
        )

        prog = parse_source(source)
        ev.eval(prog, global_env)

        # Look for a grid object in the global environment
        grid_obj = _find_grid(global_env)
        if grid_obj is not None:
            grid_state = _serialize_grid(grid_obj)

    except (ParseError, SyntaxError) as e:
        error_str = f"ParseError: {e}"
    except AxonError as e:
        error_str = e.format()
    except Exception as e:
        error_str = f"Internal error: {e}"
    finally:
        output = sys.stdout.getvalue()
        sys.stdout = old_stdout

    return {
        "output": output,
        "error": error_str,
        "grid_state": grid_state,
    }
