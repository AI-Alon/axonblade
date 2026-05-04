"""
tools/test_runner.py — AxonBlade test runner (V2 Phase 2.3, updated for VM).

Discovers all *_test.axb files under a directory tree, compiles and runs
them through the VM, and collects pass/fail results per test() call.

Built-ins injected into test files:
  test(name, fn)      — register and immediately run a named test case
  assert_eq(a, b)     — raise if a != b (with diff message)
  assert_true(val)    — raise if val is falsy
  assert_raises(fn)   — raise if fn() does NOT throw

Output:
  ✓ math_test.axb :: addition works
  ✗ math_test.axb :: subtraction works
      AssertionError: expected 3, got 4

Exit code: 0 if all pass, 1 if any fail.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class TestResult:
    name: str
    file: str
    passed: bool
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Test builtins factory
# ---------------------------------------------------------------------------

class _TestAssertionError(Exception):
    pass


def _make_test_builtins(results: list[TestResult], current_file: str,
                        vm: object) -> dict:
    """Return a dict of test built-in callables for injection into globals."""
    from core.runtime import AxonFunction

    def _call_axon(fn: object) -> None:
        if isinstance(fn, AxonFunction):
            vm.call(fn, [])  # type: ignore[attr-defined]
        elif callable(fn):
            fn()
        else:
            raise _TestAssertionError("expected a function (bladeFN)")

    def _assert_eq(a: object, b: object) -> None:
        if a != b:
            raise _TestAssertionError(f"expected {_axon_repr(b)}, got {_axon_repr(a)}")

    def _assert_true(val: object) -> None:
        if not (val is not None and val is not False):
            raise _TestAssertionError(f"expected truthy value, got {_axon_repr(val)}")

    def _assert_raises(fn: object) -> None:
        from core.errors import AxonError
        try:
            _call_axon(fn)
        except _TestAssertionError:
            raise
        except (AxonError, Exception):
            return
        raise _TestAssertionError("expected an exception to be raised, but none was")

    def _test(name: object, fn: object) -> None:
        name_str = str(name)
        from core.errors import AxonError
        try:
            _call_axon(fn)
            results.append(TestResult(name=name_str, file=current_file, passed=True))
        except _TestAssertionError as e:
            results.append(TestResult(name=name_str, file=current_file, passed=False, error=str(e)))
        except AxonError as e:
            results.append(TestResult(name=name_str, file=current_file, passed=False, error=e.message))
        except Exception as e:
            results.append(TestResult(name=name_str, file=current_file, passed=False, error=str(e)))

    return {
        "test":          _test,
        "assert_eq":     _assert_eq,
        "assert_true":   _assert_true,
        "assert_raises": _assert_raises,
    }


def _axon_repr(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return repr(value)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

class TestRunner:
    def __init__(self) -> None:
        self.results: list[TestResult] = []

    def discover(self, root: str) -> list[Path]:
        return sorted(Path(root).rglob("*_test.axb"))

    def run_file(self, path: Path) -> None:
        from core.compiler import compile_source
        from core.errors import AxonError
        from core.module_loader import load_module
        from core.parser import ParseError
        from core.vm import VM
        from stdlib.builtins import build_global_dict

        file_results: list[TestResult] = []
        source = path.read_text(encoding="utf-8")

        global_env = build_global_dict()
        vm = VM(global_env)
        vm._module_loader = lambda name: load_module(name, str(path.resolve()), vm)

        # Inject test builtins into the VM's globals
        for name, fn in _make_test_builtins(file_results, str(path), vm).items():
            global_env[name] = fn

        try:
            code = compile_source(source)
            vm.run(code)
        except (ParseError, SyntaxError) as e:
            self.results.append(TestResult(
                name="<parse>", file=str(path), passed=False,
                error=f"ParseError: {e}",
            ))
            return
        except AxonError as e:
            self.results.append(TestResult(
                name="<runtime>", file=str(path), passed=False, error=e.message,
            ))
            return
        except Exception as e:
            self.results.append(TestResult(
                name="<internal>", file=str(path), passed=False, error=str(e),
            ))
            return

        self.results.extend(file_results)

    def run_all(self, paths: list[Path]) -> None:
        for p in paths:
            self.run_file(p)

    def print_report(self) -> None:
        GREEN = "\033[32m"
        RED   = "\033[31m"
        RESET = "\033[0m"
        BOLD  = "\033[1m"

        passed = failed = 0
        for r in self.results:
            icon = f"{GREEN}✓{RESET}" if r.passed else f"{RED}✗{RESET}"
            try:
                rel = str(Path(r.file).relative_to(Path.cwd()))
            except ValueError:
                rel = r.file
            print(f"  {icon}  {rel} :: {r.name}")
            if not r.passed and r.error:
                print(f"       {RED}{r.error}{RESET}")
            if r.passed:
                passed += 1
            else:
                failed += 1

        total = passed + failed
        print()
        if total == 0:
            print(f"{BOLD}  No tests found.{RESET}")
            return

        p_str = f"{GREEN}✓ {passed} passed{RESET}"
        f_str = f"{RED}✗ {failed} failed{RESET}" if failed else "✗ 0 failed"
        print(f"  {BOLD}{p_str}   {f_str}{RESET}")

    def exit_code(self) -> int:
        return 0 if all(r.passed for r in self.results) else 1


def run_tests(root: str) -> int:
    runner = TestRunner()
    paths = runner.discover(root)
    if not paths:
        print("  No *_test.axb files found.")
        return 0
    runner.run_all(paths)
    runner.print_report()
    return runner.exit_code()
