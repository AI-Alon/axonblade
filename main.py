"""
main.py — AxonBlade CLI entry point (V2).

Usage:
    ablade run <file.axb>            — execute an AxonBlade source file
    ablade run <file.axbc>           — execute a pre-compiled bytecode file
    ablade compile <file.axb>        — compile source to file.axbc
    ablade repl                      — start the interactive REPL
    ablade fmt <file.axb>            — print formatted source to stdout
    ablade fmt --in-place <file>     — overwrite file with formatted source
    ablade fmt --check <file>        — exit 1 if file would change (CI)
    ablade lint <file.axb>           — run static analysis
    ablade test [dir]                — discover and run *_test.axb files
    ablade version                   — print version info
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_VERSION = "2.0"


# ---------------------------------------------------------------------------
# Shared helper: build and wire the VM
# ---------------------------------------------------------------------------

def _make_vm(file_path: Path | None = None):
    """Return a wired-up VM with the global environment loaded."""
    from core.vm import VM
    from core.module_loader import load_module
    from stdlib.builtins import build_global_dict

    global_env = build_global_dict()
    vm = VM(global_env)

    caller = str(file_path.resolve()) if file_path else None
    vm._module_loader = lambda name: load_module(name, caller, vm)
    return vm


# ---------------------------------------------------------------------------
# ablade run
# ---------------------------------------------------------------------------

def cmd_run(args: argparse.Namespace) -> int:
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"ablade: file not found: {args.file}", file=sys.stderr)
        return 1

    from core.errors import AxonError
    from core.parser import ParseError

    try:
        if file_path.suffix == ".axbc":
            # Execute pre-compiled bytecode
            from core.serializer import deserialize
            data = file_path.read_bytes()
            code = deserialize(data)
        elif file_path.suffix == ".axb":
            from core.compiler import compile_source
            source = file_path.read_text(encoding="utf-8")
            code = compile_source(source)
        else:
            print(
                f"ablade: warning: expected .axb or .axbc extension, "
                f"got '{file_path.suffix}'",
                file=sys.stderr,
            )
            from core.compiler import compile_source
            source = file_path.read_text(encoding="utf-8")
            code = compile_source(source)

        vm = _make_vm(file_path)
        vm.run(code)
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


# ---------------------------------------------------------------------------
# ablade compile
# ---------------------------------------------------------------------------

def cmd_compile(args: argparse.Namespace) -> int:
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"ablade compile: file not found: {args.file}", file=sys.stderr)
        return 1
    if file_path.suffix != ".axb":
        print(
            f"ablade compile: expected .axb file, got '{file_path.suffix}'",
            file=sys.stderr,
        )
        return 1

    from core.compiler import compile_source
    from core.errors import AxonError
    from core.parser import ParseError
    from core.serializer import serialize

    try:
        source = file_path.read_text(encoding="utf-8")
        code = compile_source(source)
    except (ParseError, SyntaxError) as e:
        print(f"ablade compile: parse error: {e}", file=sys.stderr)
        return 1
    except AxonError as e:
        print(e.format(), file=sys.stderr)
        return 1

    out_path = file_path.with_suffix(".axbc")
    out_path.write_bytes(serialize(code))
    print(f"Compiled → {out_path}")
    return 0


# ---------------------------------------------------------------------------
# ablade repl
# ---------------------------------------------------------------------------

def cmd_repl(_args: argparse.Namespace) -> int:
    from repl import run_repl
    run_repl()
    return 0


# ---------------------------------------------------------------------------
# ablade version
# ---------------------------------------------------------------------------

def cmd_version(_args: argparse.Namespace) -> int:
    print(f"AxonBlade v{_VERSION}")
    return 0


# ---------------------------------------------------------------------------
# ablade fmt
# ---------------------------------------------------------------------------

def cmd_fmt(args: argparse.Namespace) -> int:
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


# ---------------------------------------------------------------------------
# ablade lint
# ---------------------------------------------------------------------------

def cmd_lint(args: argparse.Namespace) -> int:
    from tools.linter import lint_file

    diags, code = lint_file(args.file)
    for d in sorted(diags, key=lambda x: (x.line, x.col)):
        print(d.format())
    return code


# ---------------------------------------------------------------------------
# ablade test
# ---------------------------------------------------------------------------

def cmd_test(args: argparse.Namespace) -> int:
    from tools.test_runner import run_tests

    root = args.dir if args.dir else "."
    if not Path(root).exists():
        print(f"ablade test: directory not found: {root}", file=sys.stderr)
        return 1
    return run_tests(root)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ablade",
        description="AxonBlade language toolchain",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Execute an .axb or .axbc file")
    run_p.add_argument("file", help="Path to source or compiled file")
    run_p.set_defaults(func=cmd_run)

    compile_p = sub.add_parser("compile", help="Compile .axb source to .axbc bytecode")
    compile_p.add_argument("file", help="Path to the .axb source file")
    compile_p.set_defaults(func=cmd_compile)

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
