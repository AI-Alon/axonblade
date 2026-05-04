"""
tests/test_formatter.py — Unit tests for core/formatter.py

Run with:  python -m pytest tests/test_formatter.py  (or python tests/test_formatter.py)
"""

import sys
import os
import unittest

# Ensure project root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.parser import parse_source
from core.formatter import Formatter


def fmt(source: str) -> str:
    return Formatter().format(parse_source(source.strip()))


class TestFormatterIndentation(unittest.TestCase):

    def test_function_body_indented_4_spaces(self):
        src = """
bladeFN greet(name#str) +/
return name
ECB
"""
        out = fmt(src)
        self.assertIn("    return name", out)

    def test_nested_block_double_indent(self):
        src = """
bladeFN outer() +/
if true +/
return 1
ECB
ECB
"""
        out = fmt(src)
        self.assertIn("    if true +/", out)
        self.assertIn("        return 1", out)

    def test_while_body_indented(self):
        src = "while x < 10 +/\nx = x + 1\nECB"
        out = fmt(src)
        self.assertIn("    x = x + 1", out)

    def test_for_body_indented(self):
        src = "for i in range(5) +/\nwrite(i)\nECB"
        out = fmt(src)
        self.assertIn("    write(i)", out)


class TestFormatterOperatorSpacing(unittest.TestCase):

    def test_binary_op_spaces(self):
        out = fmt(">> x = 1+2")
        self.assertIn("1 + 2", out)

    def test_comparison_spaces(self):
        out = fmt(">> b = a==b")
        self.assertIn("a == b", out)

    def test_multiply_spaces(self):
        out = fmt(">> r = 3*4")
        self.assertIn("3 * 4", out)

    def test_pipeline_spaces(self):
        out = fmt(">> r = x|>double()")
        self.assertIn("|>", out)


class TestFormatterBlankLines(unittest.TestCase):

    def test_blank_line_between_top_level_fns(self):
        src = """
bladeFN a() +/
return 1
ECB
bladeFN b() +/
return 2
ECB
"""
        out = fmt(src)
        lines = out.splitlines()
        a_idx = next(i for i, l in enumerate(lines) if l.startswith("bladeFN a"))
        b_idx = next(i for i, l in enumerate(lines) if l.startswith("bladeFN b"))
        # There must be at least one blank line between ECB and bladeFN b
        between = lines[a_idx + 1 : b_idx]
        self.assertTrue(any(l.strip() == "" for l in between),
                        f"Expected blank line between fns, got: {between}")

    def test_blank_line_between_class_methods(self):
        src = """
bladeGRP Foo +/
bladeFN init(self) +/
return 1
ECB
bladeFN go(self) +/
return 2
ECB
ECB
"""
        out = fmt(src)
        # Methods inside class should have blank line between them
        lines = out.splitlines()
        init_idx = next(i for i, l in enumerate(lines) if "bladeFN init" in l)
        go_idx   = next(i for i, l in enumerate(lines) if "bladeFN go" in l)
        between  = lines[init_idx + 1 : go_idx]
        self.assertTrue(any(l.strip() == "" for l in between),
                        f"Expected blank line between methods, got: {between}")


class TestFormatterNoTrailingWhitespace(unittest.TestCase):

    def test_no_trailing_spaces(self):
        src = ">> x = 1   \nbladeFN f() +/   \nreturn x   \nECB   "
        out = fmt(src)
        for line in out.splitlines():
            self.assertEqual(line, line.rstrip(),
                             f"Trailing whitespace on line: {line!r}")

    def test_ends_with_newline(self):
        out = fmt(">> x = 1")
        self.assertTrue(out.endswith("\n"))


class TestFormatterStatements(unittest.TestCase):

    def test_declaration_uses_arrows(self):
        out = fmt(">> count = 0")
        self.assertIn(">> count = 0", out)

    def test_reassignment_no_arrows(self):
        src = ">> x = 0\nx = 5"
        out = fmt(src)
        lines = out.splitlines()
        reassign = [l for l in lines if "x = 5" in l]
        self.assertTrue(reassign)
        self.assertFalse(reassign[0].lstrip().startswith(">>"))

    def test_return_statement(self):
        src = "bladeFN f() +/\nreturn 42\nECB"
        out = fmt(src)
        self.assertIn("    return 42", out)

    def test_raise_statement(self):
        src = 'bladeFN f() +/\nraise "oops"\nECB'
        out = fmt(src)
        self.assertIn('    raise "oops"', out)

    def test_uselib_statement(self):
        out = fmt("uselib -math-")
        self.assertIn("uselib -math-", out)

    def test_if_elif_else(self):
        src = """
if x == 1 +/
write("one")
ECB
elif x == 2 +/
write("two")
ECB
else +/
write("other")
ECB
"""
        out = fmt(src)
        self.assertIn("if x == 1 +/", out)
        self.assertIn("elif x == 2 +/", out)
        self.assertIn("else +/", out)
        self.assertIn("    write", out)

    def test_try_catch(self):
        # syntax: try +/ body ECB catch var +/ body ECB
        src = 'try +/\nwrite("ok")\nECB\ncatch err +/\nwrite("err")\nECB'
        out = fmt(src)
        self.assertIn("try +/", out)
        self.assertIn("catch err +/", out)
        self.assertIn("ECB", out)


class TestFormatterExpressions(unittest.TestCase):

    def test_color_literal(self):
        out = fmt('write(-*cyan*-)')
        self.assertIn("-*cyan*-", out)

    def test_fstring(self):
        out = fmt('write("hi &{name}!")')
        self.assertIn("&{name}", out)

    def test_list_literal(self):
        out = fmt(">> lst = [1, 2, 3]")
        self.assertIn("[1, 2, 3]", out)

    def test_empty_list(self):
        out = fmt(">> lst = []")
        self.assertIn("[]", out)

    def test_dict_literal(self):
        out = fmt('>> d = {"a": 1}')
        self.assertIn('"a": 1', out)

    def test_index_access(self):
        out = fmt(">> v = lst~0~")
        self.assertIn("~0~", out)

    def test_dot_access(self):
        out = fmt(">> v = obj.field")
        self.assertIn("obj.field", out)

    def test_call_expr(self):
        out = fmt("write(42)")
        self.assertIn("write(42)", out)

    def test_bool_literals(self):
        out = fmt(">> a = true\n>> b = false")
        self.assertIn("true", out)
        self.assertIn("false", out)

    def test_null_literal(self):
        out = fmt(">> x = null")
        self.assertIn("null", out)

    def test_unary_neg(self):
        out = fmt(">> x = -5")
        self.assertIn("-5", out)

    def test_unary_not(self):
        out = fmt(">> b = -n true")
        self.assertIn("-n true", out)


class TestFormatterIdempotent(unittest.TestCase):
    """Formatting already-formatted source must produce identical output."""

    def _check(self, source: str):
        first  = fmt(source)
        second = fmt(first)
        self.assertEqual(first, second, "Formatter is not idempotent")

    def test_idempotent_simple(self):
        self._check(">> x = 1 + 2")

    def test_idempotent_function(self):
        self._check("bladeFN f(x#int) +/\n    return x * 2\nECB")

    def test_idempotent_if(self):
        self._check("if x > 0 +/\n    write(x)\nECB")

    def test_idempotent_class(self):
        src = ("bladeGRP Point +/\n"
               "    bladeFN init(self, x#int, y#int) +/\n"
               "        self.x = x\n"
               "        self.y = y\n"
               "    ECB\n"
               "ECB")
        self._check(src)


if __name__ == "__main__":
    unittest.main()
