"""
repl.py — AxonBlade interactive REPL (Week 7, Phase 7.5).

Provides a readline-style loop with a styled ">>" prompt.
Return values are pretty-printed; errors are caught and displayed
without crashing the session.
"""

from __future__ import annotations

import sys

from core.evaluator import Evaluator, AxonFunction, AxonBladeGRP, AxonInstance
from core.errors import AxonError
from core.module_loader import load_module
from core.parser import parse_source, ParseError
from stdlib.builtins import build_global_env

# ANSI color helpers for the REPL prompt and output
_CYAN = "\033[36m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_RESET = "\033[0m"

_VERSION = "1.0"
_PROMPT = f"{_CYAN}>>{_RESET} "


def _format_value(value: object) -> str | None:
    """Convert an AxonBlade value to a display string for the REPL."""
    if value is None:
        return None  # don't print null from statements
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (AxonFunction, AxonBladeGRP, AxonInstance)):
        return f"{_YELLOW}{repr(value)}{_RESET}"
    if isinstance(value, str) and not value.startswith("\033"):
        return f'"{value}"'
    return str(value)


def run_repl() -> None:
    """Start the interactive REPL."""
    ev = Evaluator()
    global_env = build_global_env()

    # Wire module loader
    ev._module_loader = lambda name, _line: load_module(
        name, None, ev, build_global_env
    )

    print(f"{_CYAN}AxonBlade v{_VERSION} — type 'exit' or Ctrl+D to quit{_RESET}")

    while True:
        try:
            line = input(_PROMPT)
        except (EOFError, KeyboardInterrupt):
            print()
            break

        line = line.strip()
        if not line:
            continue
        if line in ("exit", "quit"):
            break

        try:
            prog = parse_source(line + "\n")
            result = ev.eval(prog, global_env)
            display = _format_value(result)
            if display is not None:
                print(display)
        except (ParseError, SyntaxError) as e:
            print(f"{_RED}ParseError: {e}{_RESET}", file=sys.stderr)
        except AxonError as e:
            print(f"{_RED}{e.format()}{_RESET}", file=sys.stderr)
        except Exception as e:
            print(f"{_RED}Internal error: {e}{_RESET}", file=sys.stderr)


if __name__ == "__main__":
    run_repl()
