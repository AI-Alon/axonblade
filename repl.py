"""
repl.py — AxonBlade interactive REPL (V2 — compiler + VM).

Compiles each input line and executes it through the VM.
State persists across inputs via the shared globals dict.
"""

from __future__ import annotations

import sys

from core.errors import AxonError
from core.module_loader import load_module
from core.parser import parse_source, ParseError
from core.runtime import AxonFunction, AxonBladeGRP, AxonInstance
from stdlib.builtins import build_global_dict

_CYAN   = "\033[36m"
_YELLOW = "\033[33m"
_RED    = "\033[31m"
_RESET  = "\033[0m"

_VERSION = "2.0"
_PROMPT  = f"{_CYAN}>>{_RESET} "


def _format_value(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (AxonFunction, AxonBladeGRP, AxonInstance)):
        return f"{_YELLOW}{repr(value)}{_RESET}"
    if isinstance(value, str) and not value.startswith("\033"):
        return f'"{value}"'
    return str(value)


def run_repl() -> None:
    from core.compiler import Compiler
    from core.vm import VM

    global_env = build_global_dict()
    vm = VM(global_env)
    vm._module_loader = lambda name: load_module(name, None, vm)

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
            code = Compiler().compile(prog)
            result = vm.run(code)
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
