"""
main.py — AxonBlade CLI entry point.

Usage:
    ablade run <file.axb>          — execute an AxonBlade source file
    ablade repl                    — start the interactive REPL
    ablade fmt <file.axb>          — print formatted source to stdout
    ablade fmt --in-place <file>   — overwrite file with formatted source
    ablade fmt --check <file>      — exit 1 if file would change (CI)
    ablade lint <file.axb>         — run static analysis
    ablade test [dir]              — discover and run *_test.axb files
    ablade version                 — print version info
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_VERSION = "2.0"


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


def cmd_fmt(args: argparse.Namespace) -> int:
    """Format an AxonBlade source file."""
    from core.formatter import Formatter
    from core.parser import parse_source, ParseError

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"ablade fmt: file not found: {args.file}", file=sys.stderr)
        return 1

    source = file_path.read_text(encoding="utf-8")
    try:
        prog = parse_source(source)
    except (ParseError, SyntaxError) as e:
        print(f"ablade fmt: parse error: {e}", file=sys.stderr)
        return 1

    formatted = Formatter().format(prog)

    if args.check:
        if formatted != source:
            print(f"ablade fmt: {args.file}: would reformat", file=sys.stderr)
            return 1
        return 0

    if args.in_place:
        file_path.write_text(formatted, encoding="utf-8")
        return 0

    print(formatted, end="")
    return 0


def cmd_lint(args: argparse.Namespace) -> int:
    """Run static analysis on an AxonBlade source file."""
    from tools.linter import lint_file

    diags, code = lint_file(args.file)
    for d in sorted(diags, key=lambda x: (x.line, x.col)):
        print(d.format())
    return code


def cmd_test(args: argparse.Namespace) -> int:
    """Discover and run *_test.axb files."""
    from tools.test_runner import run_tests

    root = args.dir if args.dir else "."
    if not Path(root).exists():
        print(f"ablade test: directory not found: {root}", file=sys.stderr)
        return 1
    return run_tests(root)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ablade",
        description="AxonBlade language toolchain",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Execute an .axb file")
    run_p.add_argument("file", help="Path to the .axb source file")
    run_p.set_defaults(func=cmd_run)

    repl_p = sub.add_parser("repl", help="Start the interactive REPL")
    repl_p.set_defaults(func=cmd_repl)

    fmt_p = sub.add_parser("fmt", help="Format an .axb source file")
    fmt_p.add_argument("file", help="Path to the .axb source file")
    fmt_p.add_argument("--in-place", action="store_true",
                       help="Overwrite the file with formatted output")
    fmt_p.add_argument("--check", action="store_true",
                       help="Exit 1 if the file would be reformatted (CI mode)")
    fmt_p.set_defaults(func=cmd_fmt)

    lint_p = sub.add_parser("lint", help="Run static analysis on an .axb file")
    lint_p.add_argument("file", help="Path to the .axb source file")
    lint_p.set_defaults(func=cmd_lint)

    test_p = sub.add_parser("test", help="Discover and run *_test.axb files")
    test_p.add_argument("dir", nargs="?", default=".",
                        help="Root directory to search (default: current directory)")
    test_p.set_defaults(func=cmd_test)

    ver_p = sub.add_parser("version", help="Print version info")
    ver_p.set_defaults(func=cmd_version)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
