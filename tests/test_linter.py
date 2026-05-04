"""
tests/test_linter.py — Unit tests for tools/linter.py

Each test class covers one linter diagnostic. Tests verify that the
expected diagnostic is emitted (or absent) for specific source patterns.

Run with:  python -m pytest tests/test_linter.py  (or python tests/test_linter.py)
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.parser import parse_source
from tools.linter import Linter, Diagnostic


def lint(source: str) -> list[Diagnostic]:
    prog = parse_source(source.strip())
    return Linter(filename="test.axb").lint(prog)


def errors(source: str) -> list[str]:
    return [d.message for d in lint(source) if d.level == "error"]


def warnings(source: str) -> list[str]:
    return [d.message for d in lint(source) if d.level == "warning"]


# ---------------------------------------------------------------------------
# Undefined variable (error)
# ---------------------------------------------------------------------------

class TestUndefinedVariable(unittest.TestCase):

    def test_bare_undefined(self):
        msgs = errors("write(x)")
        self.assertTrue(any("undefined variable 'x'" in m for m in msgs))

    def test_declared_is_not_undefined(self):
        msgs = errors(">> x = 5\nwrite(x)")
        self.assertFalse(any("undefined variable 'x'" in m for m in msgs))

    def test_builtin_not_undefined(self):
        msgs = errors("write(len([1, 2, 3]))")
        self.assertFalse(any("undefined" in m for m in msgs))

    def test_function_name_declared(self):
        src = "bladeFN f() +/\nreturn 1\nECB\nf()"
        msgs = errors(src)
        self.assertFalse(any("undefined variable 'f'" in m for m in msgs))

    def test_param_not_undefined_in_body(self):
        src = "bladeFN greet(name#str) +/\nwrite(name)\nECB"
        msgs = errors(src)
        self.assertFalse(any("undefined" in m for m in msgs))

    def test_undefined_inside_function(self):
        src = "bladeFN f() +/\nwrite(missing)\nECB"
        msgs = errors(src)
        self.assertTrue(any("undefined variable 'missing'" in m for m in msgs))

    def test_for_loop_var_scoped(self):
        src = "for i in range(5) +/\nwrite(i)\nECB"
        msgs = errors(src)
        self.assertFalse(any("undefined variable 'i'" in m for m in msgs))

    def test_catch_var_scoped(self):
        src = 'try +/\nwrite("ok")\nECB\ncatch e +/\nwrite(e)\nECB'
        msgs = errors(src)
        self.assertFalse(any("undefined variable 'e'" in m for m in msgs))

    def test_closure_captures_outer(self):
        src = ("bladeFN outer() +/\n"
               "    >> x = 10\n"
               "    bladeFN inner() +/\n"
               "        write(x)\n"
               "    ECB\n"
               "    inner()\n"
               "ECB")
        msgs = errors(src)
        self.assertFalse(any("undefined variable 'x'" in m for m in msgs))


# ---------------------------------------------------------------------------
# Wrong argument count (error)
# ---------------------------------------------------------------------------

class TestWrongArgCount(unittest.TestCase):

    def test_too_few_args(self):
        src = "bladeFN add(a#int, b#int) +/\nreturn a + b\nECB\nadd(1)"
        msgs = errors(src)
        self.assertTrue(any("'add' called with 1 argument(s), expected 2" in m for m in msgs))

    def test_too_many_args(self):
        src = "bladeFN f(x#int) +/\nreturn x\nECB\nf(1, 2, 3)"
        msgs = errors(src)
        self.assertTrue(any("'f' called with 3 argument(s), expected 1" in m for m in msgs))

    def test_correct_arg_count_no_error(self):
        src = "bladeFN add(a#int, b#int) +/\nreturn a + b\nECB\nadd(1, 2)"
        msgs = errors(src)
        self.assertFalse(any("'add' called" in m for m in msgs))

    def test_zero_arg_call_correct(self):
        src = "bladeFN hello() +/\nwrite(\"hi\")\nECB\nhello()"
        msgs = errors(src)
        self.assertFalse(any("'hello' called" in m for m in msgs))

    def test_pipeline_skips_arity_check(self):
        # pipeline prepends one arg — fn(x) called as x |> fn() should not error
        src = ("bladeFN double(x#int) +/\nreturn x * 2\nECB\n"
               ">> r = 5 |> double()")
        msgs = errors(src)
        self.assertFalse(any("'double' called" in m for m in msgs))

    def test_rebound_name_skips_arity_check(self):
        # >> f = something rebinds f; subsequent calls should not trigger arity check
        src = ("bladeFN f(x#int) +/\nreturn x\nECB\n"
               ">> f = f\n"
               "f()")   # 0 args — but f was rebound, so no error
        msgs = errors(src)
        self.assertFalse(any("'f' called" in m for m in msgs))


# ---------------------------------------------------------------------------
# Unused variable (warning)
# ---------------------------------------------------------------------------

class TestUnusedVariable(unittest.TestCase):

    def test_declared_never_read(self):
        msgs = warnings(">> x = 5")
        self.assertTrue(any("'x' is declared but never read" in m for m in msgs))

    def test_declared_and_read(self):
        msgs = warnings(">> x = 5\nwrite(x)")
        self.assertFalse(any("'x' is declared" in m for m in msgs))

    def test_underscore_prefix_suppresses(self):
        msgs = warnings(">> _tmp = 99")
        self.assertFalse(any("'_tmp' is declared" in m for m in msgs))

    def test_function_param_not_warned(self):
        src = "bladeFN f(x#int) +/\nwrite(\"ok\")\nECB"
        msgs = warnings(src)
        self.assertFalse(any("'x' is declared" in m for m in msgs))

    def test_unused_inside_function(self):
        src = "bladeFN f() +/\n>> local = 99\nECB"
        msgs = warnings(src)
        self.assertTrue(any("'local' is declared but never read" in m for m in msgs))

    def test_multiple_unused(self):
        msgs = warnings(">> a = 1\n>> b = 2\n>> c = 3")
        names = [m for m in msgs if "declared but never read" in m]
        self.assertEqual(len(names), 3)


# ---------------------------------------------------------------------------
# Unreachable code after return (warning)
# ---------------------------------------------------------------------------

class TestUnreachableCode(unittest.TestCase):

    def test_stmt_after_return(self):
        src = ("bladeFN f() +/\n"
               "    return 1\n"
               "    write(\"dead\")\n"
               "ECB")
        msgs = warnings(src)
        self.assertTrue(any("unreachable" in m for m in msgs))

    def test_no_code_after_return(self):
        src = "bladeFN f() +/\n    return 1\nECB"
        msgs = warnings(src)
        self.assertFalse(any("unreachable" in m for m in msgs))

    def test_code_before_return_not_warned(self):
        src = ("bladeFN f() +/\n"
               "    write(\"alive\")\n"
               "    return 1\n"
               "ECB")
        msgs = warnings(src)
        self.assertFalse(any("unreachable" in m for m in msgs))

    def test_stmt_after_raise(self):
        src = ("bladeFN f() +/\n"
               '    raise "err"\n'
               "    write(\"dead\")\n"
               "ECB")
        msgs = warnings(src)
        self.assertTrue(any("unreachable" in m for m in msgs))

    def test_only_first_dead_stmt_warned(self):
        src = ("bladeFN f() +/\n"
               "    return 1\n"
               "    write(\"dead1\")\n"
               "    write(\"dead2\")\n"
               "ECB")
        msgs = warnings(src)
        unreachable = [m for m in msgs if "unreachable" in m]
        self.assertEqual(len(unreachable), 1)


# ---------------------------------------------------------------------------
# Variable shadowing (warning)
# ---------------------------------------------------------------------------

class TestShadowing(unittest.TestCase):

    def test_param_shadows_outer(self):
        src = (">> x = 10\n"
               "bladeFN f(x#int) +/\n"
               "    return x\n"
               "ECB")
        msgs = warnings(src)
        self.assertTrue(any("shadows" in m and "'x'" in m for m in msgs))

    def test_inner_decl_shadows_outer(self):
        src = (">> x = 10\n"
               "bladeFN f() +/\n"
               "    >> x = 20\n"
               "    write(x)\n"
               "ECB")
        msgs = warnings(src)
        self.assertTrue(any("shadows" in m and "'x'" in m for m in msgs))

    def test_no_shadow_different_name(self):
        src = (">> x = 10\n"
               "bladeFN f(y#int) +/\n"
               "    return y\n"
               "ECB")
        msgs = warnings(src)
        self.assertFalse(any("shadows" in m for m in msgs))

    def test_for_var_shadows_outer(self):
        src = (">> i = 99\n"
               "for i in range(3) +/\n"
               "    write(i)\n"
               "ECB")
        msgs = warnings(src)
        self.assertTrue(any("shadows" in m and "'i'" in m for m in msgs))


# ---------------------------------------------------------------------------
# Clean source produces no diagnostics
# ---------------------------------------------------------------------------

class TestCleanSource(unittest.TestCase):

    def test_fibonacci_clean(self):
        src = (
            "bladeFN fib(n#int) +/\n"
            "    if n <= 1 +/\n"
            "        return n\n"
            "    ECB\n"
            "    return fib(n - 1) + fib(n - 2)\n"
            "ECB\n"
            "write(fib(10))\n"
        )
        diags = lint(src)
        self.assertEqual(diags, [])

    def test_clean_class(self):
        src = (
            "bladeGRP Counter +/\n"
            "    bladeFN init(self, start#int) +/\n"
            "        self.count = start\n"
            "    ECB\n"
            "    bladeFN inc(self) +/\n"
            "        self.count = self.count + 1\n"
            "    ECB\n"
            "    bladeFN get(self) +/\n"
            "        return self.count\n"
            "    ECB\n"
            "ECB\n"
            ">> c = Counter(0)\n"
            "c.inc()\n"
            "write(c.get())\n"
        )
        diags = lint(src)
        self.assertEqual(diags, [])


# ---------------------------------------------------------------------------
# Exit code helpers
# ---------------------------------------------------------------------------

class TestExitCode(unittest.TestCase):

    def test_exit_0_clean(self):
        from tools.linter import lint_file
        import tempfile, os
        src = ">> x = 1\nwrite(x)\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".axb", delete=False) as f:
            f.write(src)
            path = f.name
        try:
            _, code = lint_file(path)
            self.assertEqual(code, 0)
        finally:
            os.unlink(path)

    def test_exit_1_on_error(self):
        from tools.linter import lint_file
        import tempfile, os
        src = "write(undefined_var)\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".axb", delete=False) as f:
            f.write(src)
            path = f.name
        try:
            _, code = lint_file(path)
            self.assertEqual(code, 1)
        finally:
            os.unlink(path)

    def test_exit_2_on_warning_only(self):
        from tools.linter import lint_file
        import tempfile, os
        src = ">> unused = 42\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".axb", delete=False) as f:
            f.write(src)
            path = f.name
        try:
            _, code = lint_file(path)
            self.assertEqual(code, 2)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
