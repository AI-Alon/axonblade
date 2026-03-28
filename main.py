"""
main.py — AxonBlade CLI entry point (Week 7, Phase 7.5).

Usage:
    python main.py run <file.axb>    — execute an AxonBlade source file
    python main.py repl              — start the interactive REPL
    python main.py version           — print version info
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_VERSION = "1.0"


def cmd_run(args: argparse.Namespace) -> int:
    """Execute an AxonBlade source file."""
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"axb: file not found: {args.file}", file=sys.stderr)
        return 1
    if file_path.suffix != ".axb":
        print(f"axb: warning: expected .axb extension, got '{file_path.suffix}'",
              file=sys.stderr)

    from core.evaluator import Evaluator
    from core.errors import AxonError
    from core.module_loader import load_module
    from core.parser import parse_source, ParseError
    from stdlib.builtins import build_global_env

    source = file_path.read_text(encoding="utf-8")
    ev = Evaluator()
    global_env = build_global_env()

    # Wire module loader with the caller file for relative imports
    ev._module_loader = lambda name, _line: load_module(
        name, str(file_path.resolve()), ev, build_global_env
    )

    try:
        prog = parse_source(source)
        ev.eval(prog, global_env)
        return 0
    except (ParseError, SyntaxError) as e:
        print(f"ParseError: {e}", file=sys.stderr)
        return 1
    except AxonError as e:
        print(e.format(), file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Internal error: {e}", file=sys.stderr)
        return 1


def cmd_repl(_args: argparse.Namespace) -> int:
    """Start the interactive REPL."""
    from repl import run_repl
    run_repl()
    return 0


def cmd_version(_args: argparse.Namespace) -> int:
    """Print version info."""
    print(f"AxonBlade v{_VERSION}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="axb",
        description="AxonBlade language interpreter",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Execute an .axb file")
    run_p.add_argument("file", help="Path to the .axb source file")
    run_p.set_defaults(func=cmd_run)

    repl_p = sub.add_parser("repl", help="Start the interactive REPL")
    repl_p.set_defaults(func=cmd_repl)

    ver_p = sub.add_parser("version", help="Print version info")
    ver_p.set_defaults(func=cmd_version)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
