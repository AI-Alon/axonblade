"""
tests/test_parser.py — Week 3 + Week 4 parser tests (Phases 3.1-4.5).

Covers all expression types and all statement types:
  - Correct AST node construction
  - Operator precedence and associativity
  - Pretty-writer output for parsed trees
  - Edge cases (empty collections, chained ops, nested exprs)
  - Variable declarations and re-assignments
  - bladeFN function definitions (including nested closures)
  - bladeGRP class definitions
  - Control flow: if/elif/else, while, for
  - try/catch, uselib, raise, return
  - Full Program node
"""

import pytest

from core.ast_nodes import (
    AssignStmt,
    BladeGRPDef,
    BinaryOp,
    BoolLiteral,
    CallExpr,
    ColorLiteral,
    DictLiteral,
    DotAccess,
    FnDef,
    ForStmt,
    FStringLiteral,
    Identifier,
    IfStmt,
    IndexAccess,
    ListLiteral,
    NullLiteral,
    NumberLiteral,
    Param,
    PipelineExpr,
    Program,
    RaiseStmt,
    ReturnStmt,
    SliceAccess,
    StringLiteral,
    TryCatch,
    UnaryOp,
    UselibStmt,
    WhileStmt,
    pretty_write,
)
from core.parser import ParseError, Parser, parse_expr_source, parse_source
from core.lexer import Lexer


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def lex_parse(source: str):
    """Lex source and return the parsed expression AST node."""
    return parse_expr_source(source)


# ===========================================================================
# Phase 3.2 — Literal & grouping expressions
# ===========================================================================

class TestNumberLiterals:
    def test_integer(self):
        node = lex_parse("42")
        assert isinstance(node, NumberLiteral)
        assert node.value == 42

    def test_float(self):
        node = lex_parse("3.14")
        assert isinstance(node, NumberLiteral)
        assert node.value == pytest.approx(3.14)

    def test_zero(self):
        node = lex_parse("0")
        assert isinstance(node, NumberLiteral)
        assert node.value == 0

    def test_large_number(self):
        node = lex_parse("1000000")
        assert isinstance(node, NumberLiteral)
        assert node.value == 1_000_000


class TestStringLiterals:
    def test_simple_string(self):
        node = lex_parse('"hello"')
        assert isinstance(node, StringLiteral)
        assert node.value == "hello"

    def test_empty_string(self):
        node = lex_parse('""')
        assert isinstance(node, StringLiteral)
        assert node.value == ""

    def test_string_with_escape(self):
        node = lex_parse(r'"line1\nline2"')
        assert isinstance(node, StringLiteral)
        assert node.value == "line1\nline2"


class TestFStringLiterals:
    def test_fstring_simple_interpolation(self):
        node = lex_parse('"Hello &{name}"')
        assert isinstance(node, FStringLiteral)
        # parts: ["Hello ", Identifier("name")]
        assert len(node.parts) == 2
        assert node.parts[0] == "Hello "
        assert isinstance(node.parts[1], Identifier)
        assert node.parts[1].name == "name"

    def test_fstring_expression_interpolation(self):
        node = lex_parse('"Result: &{a + b}"')
        assert isinstance(node, FStringLiteral)
        # parts: ["Result: ", BinaryOp(a, +, b)]
        assert node.parts[0] == "Result: "
        expr = node.parts[1]
        assert isinstance(expr, BinaryOp)
        assert expr.op == "+"

    def test_fstring_multiple_interpolations(self):
        node = lex_parse('"&{x} + &{y}"')
        assert isinstance(node, FStringLiteral)
        # parts: ["", Identifier(x), " + ", Identifier(y)]
        assert isinstance(node.parts[1], Identifier)
        assert node.parts[1].name == "x"
        assert node.parts[2] == " + "
        assert isinstance(node.parts[3], Identifier)
        assert node.parts[3].name == "y"

    def test_fstring_no_interpolation_is_string(self):
        # A string with no &{} is a plain STRING token, not FSTRING
        node = lex_parse('"plain string"')
        assert isinstance(node, StringLiteral)
        assert node.value == "plain string"


class TestColorLiterals:
    def test_color_red(self):
        node = lex_parse("-*red*-")
        assert isinstance(node, ColorLiteral)
        assert node.name == "red"

    def test_color_cyan(self):
        node = lex_parse("-*cyan*-")
        assert isinstance(node, ColorLiteral)
        assert node.name == "cyan"

    def test_color_reset(self):
        node = lex_parse("-*reset*-")
        assert isinstance(node, ColorLiteral)
        assert node.name == "reset"


class TestBoolAndNull:
    def test_true(self):
        node = lex_parse("true")
        assert isinstance(node, BoolLiteral)
        assert node.value is True

    def test_false(self):
        node = lex_parse("false")
        assert isinstance(node, BoolLiteral)
        assert node.value is False

    def test_null(self):
        node = lex_parse("null")
        assert isinstance(node, NullLiteral)


class TestListLiterals:
    def test_empty_list(self):
        node = lex_parse("[]")
        assert isinstance(node, ListLiteral)
        assert node.elements == []

    def test_list_with_numbers(self):
        node = lex_parse("[1, 2, 3]")
        assert isinstance(node, ListLiteral)
        assert len(node.elements) == 3
        assert all(isinstance(e, NumberLiteral) for e in node.elements)
        assert [e.value for e in node.elements] == [1, 2, 3]

    def test_list_with_mixed_types(self):
        node = lex_parse('[42, "hello", true]')
        assert isinstance(node, ListLiteral)
        assert len(node.elements) == 3
        assert isinstance(node.elements[0], NumberLiteral)
        assert isinstance(node.elements[1], StringLiteral)
        assert isinstance(node.elements[2], BoolLiteral)

    def test_nested_list(self):
        node = lex_parse("[[1, 2], [3, 4]]")
        assert isinstance(node, ListLiteral)
        assert len(node.elements) == 2
        assert isinstance(node.elements[0], ListLiteral)


class TestDictLiterals:
    def test_empty_dict(self):
        node = lex_parse("{}")
        assert isinstance(node, DictLiteral)
        assert node.pairs == []

    def test_dict_bare_identifier_keys(self):
        node = lex_parse('{name: "Ada", hp: 100}')
        assert isinstance(node, DictLiteral)
        assert len(node.pairs) == 2
        # Bare identifier keys become StringLiterals
        key0, val0 = node.pairs[0]
        assert isinstance(key0, StringLiteral)
        assert key0.value == "name"
        assert isinstance(val0, StringLiteral)
        key1, val1 = node.pairs[1]
        assert isinstance(key1, StringLiteral)
        assert key1.value == "hp"
        assert isinstance(val1, NumberLiteral)
        assert val1.value == 100

    def test_dict_string_keys(self):
        node = lex_parse('{"x": 1, "y": 2}')
        assert isinstance(node, DictLiteral)
        assert len(node.pairs) == 2
        key0, val0 = node.pairs[0]
        assert isinstance(key0, StringLiteral)
        assert key0.value == "x"


class TestGroupedExpressions:
    def test_grouped_simple(self):
        node = lex_parse("(42)")
        assert isinstance(node, NumberLiteral)
        assert node.value == 42

    def test_grouped_changes_precedence(self):
        # (1 + 2) * 3  should give BinaryOp(BinaryOp(1+2), *, 3)
        node = lex_parse("(1 + 2) * 3")
        assert isinstance(node, BinaryOp)
        assert node.op == "*"
        assert isinstance(node.left, BinaryOp)
        assert node.left.op == "+"

    def test_nested_grouping(self):
        node = lex_parse("((5))")
        assert isinstance(node, NumberLiteral)
        assert node.value == 5


# ===========================================================================
# Phase 3.3 — Prefix & postfix operators
# ===========================================================================

class TestUnaryOperators:
    def test_unary_minus_number(self):
        node = lex_parse("-5")
        assert isinstance(node, UnaryOp)
        assert node.op == "-"
        assert isinstance(node.operand, NumberLiteral)
        assert node.operand.value == 5

    def test_unary_minus_identifier(self):
        node = lex_parse("-x")
        assert isinstance(node, UnaryOp)
        assert node.op == "-"
        assert isinstance(node.operand, Identifier)
        assert node.operand.name == "x"

    def test_unary_not_bool(self):
        node = lex_parse("-n true")
        assert isinstance(node, UnaryOp)
        assert node.op == "-n"
        assert isinstance(node.operand, BoolLiteral)

    def test_unary_not_identifier(self):
        node = lex_parse("-n active")
        assert isinstance(node, UnaryOp)
        assert node.op == "-n"
        assert isinstance(node.operand, Identifier)

    def test_double_unary_not(self):
        node = lex_parse("-n -n a")
        assert isinstance(node, UnaryOp)
        assert node.op == "-n"
        assert isinstance(node.operand, UnaryOp)
        assert node.operand.op == "-n"


class TestFunctionCalls:
    def test_call_no_args(self):
        node = lex_parse("foo()")
        assert isinstance(node, CallExpr)
        assert isinstance(node.callee, Identifier)
        assert node.callee.name == "foo"
        assert node.args == []

    def test_call_single_arg(self):
        node = lex_parse("write(42)")
        assert isinstance(node, CallExpr)
        assert len(node.args) == 1
        assert isinstance(node.args[0], NumberLiteral)
        assert node.args[0].value == 42

    def test_call_multiple_args(self):
        node = lex_parse('greet("Ada", 30)')
        assert isinstance(node, CallExpr)
        assert len(node.args) == 2
        assert isinstance(node.args[0], StringLiteral)
        assert isinstance(node.args[1], NumberLiteral)

    def test_chained_calls(self):
        # f(a)(b) → CallExpr(CallExpr(f, [a]), [b])
        node = lex_parse("f(a)(b)")
        assert isinstance(node, CallExpr)
        assert isinstance(node.callee, CallExpr)
        assert node.callee.callee.name == "f"

    def test_call_with_expression_arg(self):
        node = lex_parse("write(1 + 2)")
        assert isinstance(node, CallExpr)
        assert isinstance(node.args[0], BinaryOp)


class TestDotAccess:
    def test_dot_access(self):
        node = lex_parse("obj.attr")
        assert isinstance(node, DotAccess)
        assert isinstance(node.obj, Identifier)
        assert node.obj.name == "obj"
        assert node.attr == "attr"

    def test_method_call(self):
        node = lex_parse("obj.method()")
        assert isinstance(node, CallExpr)
        assert isinstance(node.callee, DotAccess)
        assert node.callee.obj.name == "obj"
        assert node.callee.attr == "method"
        assert node.args == []

    def test_method_call_with_args(self):
        node = lex_parse("items.append(50)")
        assert isinstance(node, CallExpr)
        assert isinstance(node.callee, DotAccess)
        assert node.callee.attr == "append"
        assert len(node.args) == 1

    def test_chained_dot_access(self):
        # a.b.c → DotAccess(DotAccess(a, b), c)
        node = lex_parse("a.b.c")
        assert isinstance(node, DotAccess)
        assert node.attr == "c"
        assert isinstance(node.obj, DotAccess)
        assert node.obj.attr == "b"


class TestSubscriptAccess:
    def test_index_access(self):
        node = lex_parse("items~0~")
        assert isinstance(node, IndexAccess)
        assert isinstance(node.obj, Identifier)
        assert node.obj.name == "items"
        assert isinstance(node.index, NumberLiteral)
        assert node.index.value == 0

    def test_index_access_with_expr(self):
        node = lex_parse("items~i + 1~")
        assert isinstance(node, IndexAccess)
        assert isinstance(node.index, BinaryOp)
        assert node.index.op == "+"

    def test_slice_access_both_bounds(self):
        node = lex_parse("items~1:3~")
        assert isinstance(node, SliceAccess)
        assert isinstance(node.start, NumberLiteral)
        assert node.start.value == 1
        assert isinstance(node.end, NumberLiteral)
        assert node.end.value == 3

    def test_slice_omit_end(self):
        node = lex_parse("items~2:~")
        assert isinstance(node, SliceAccess)
        assert isinstance(node.start, NumberLiteral)
        assert node.end is None

    def test_slice_omit_start(self):
        node = lex_parse("items~:3~")
        assert isinstance(node, SliceAccess)
        assert node.start is None
        assert isinstance(node.end, NumberLiteral)
        assert node.end.value == 3

    def test_dict_index_string_key(self):
        node = lex_parse('player~"name"~')
        assert isinstance(node, IndexAccess)
        assert isinstance(node.index, StringLiteral)
        assert node.index.value == "name"


# ===========================================================================
# Phase 3.4 — Binary operators & complex expressions
# ===========================================================================

class TestArithmeticOperators:
    def test_addition(self):
        node = lex_parse("a + b")
        assert isinstance(node, BinaryOp)
        assert node.op == "+"

    def test_subtraction(self):
        node = lex_parse("a - b")
        assert isinstance(node, BinaryOp)
        assert node.op == "-"

    def test_multiplication(self):
        node = lex_parse("a * b")
        assert isinstance(node, BinaryOp)
        assert node.op == "*"

    def test_division(self):
        node = lex_parse("a / b")
        assert isinstance(node, BinaryOp)
        assert node.op == "/"

    def test_modulo(self):
        node = lex_parse("a % b")
        assert isinstance(node, BinaryOp)
        assert node.op == "%"

    def test_power(self):
        node = lex_parse("a ** b")
        assert isinstance(node, BinaryOp)
        assert node.op == "**"


class TestComparisonOperators:
    @pytest.mark.parametrize("src, op", [
        ("a == b", "=="),
        ("a != b", "!="),
        ("a < b", "<"),
        ("a > b", ">"),
        ("a <= b", "<="),
        ("a >= b", ">="),
    ])
    def test_comparison(self, src, op):
        node = lex_parse(src)
        assert isinstance(node, BinaryOp)
        assert node.op == op


class TestLogicalOperators:
    def test_and(self):
        node = lex_parse("a -a b")
        assert isinstance(node, BinaryOp)
        assert node.op == "-a"

    def test_or(self):
        node = lex_parse("a -o b")
        assert isinstance(node, BinaryOp)
        assert node.op == "-o"

    def test_not_with_comparison(self):
        # -n a == b  →  -n (a == b)
        node = lex_parse("-n a == b")
        assert isinstance(node, UnaryOp)
        assert node.op == "-n"
        assert isinstance(node.operand, BinaryOp)
        assert node.operand.op == "=="

    def test_not_stops_at_and(self):
        # -n a -a b  →  (-n a) -a b
        node = lex_parse("-n a -a b")
        assert isinstance(node, BinaryOp)
        assert node.op == "-a"
        assert isinstance(node.left, UnaryOp)
        assert node.left.op == "-n"

    def test_and_over_or(self):
        # a -o b -a c  →  a -o (b -a c)
        node = lex_parse("a -o b -a c")
        assert isinstance(node, BinaryOp)
        assert node.op == "-o"
        assert isinstance(node.right, BinaryOp)
        assert node.right.op == "-a"


class TestPrecedence:
    def test_mul_over_add(self):
        # 1 + 2 * 3  →  1 + (2 * 3)
        node = lex_parse("1 + 2 * 3")
        assert isinstance(node, BinaryOp)
        assert node.op == "+"
        assert isinstance(node.right, BinaryOp)
        assert node.right.op == "*"

    def test_add_left_associative(self):
        # 1 + 2 + 3  →  (1 + 2) + 3
        node = lex_parse("1 + 2 + 3")
        assert isinstance(node, BinaryOp)
        assert node.op == "+"
        assert isinstance(node.left, BinaryOp)
        assert node.left.op == "+"

    def test_power_right_associative(self):
        # 2 ** 3 ** 4  →  2 ** (3 ** 4)
        node = lex_parse("2 ** 3 ** 4")
        assert isinstance(node, BinaryOp)
        assert node.op == "**"
        assert isinstance(node.right, BinaryOp)
        assert node.right.op == "**"

    def test_unary_minus_and_power(self):
        # -2 ** 2  →  -(2 ** 2)
        node = lex_parse("-2 ** 2")
        assert isinstance(node, UnaryOp)
        assert node.op == "-"
        assert isinstance(node.operand, BinaryOp)
        assert node.operand.op == "**"

    def test_comparison_over_logical(self):
        # a == b -a c  →  (a == b) -a c
        node = lex_parse("a == b -a c")
        assert isinstance(node, BinaryOp)
        assert node.op == "-a"
        assert isinstance(node.left, BinaryOp)
        assert node.left.op == "=="

    def test_complex_precedence(self):
        # a + b * c - d  →  (a + (b * c)) - d
        node = lex_parse("a + b * c - d")
        assert isinstance(node, BinaryOp)
        assert node.op == "-"
        assert isinstance(node.left, BinaryOp)
        assert node.left.op == "+"
        assert isinstance(node.left.right, BinaryOp)
        assert node.left.right.op == "*"


class TestComplexExpressions:
    def test_color_concatenation(self):
        # -*red*- + "Error" + -*reset*-
        node = lex_parse('-*red*- + "Error" + -*reset*-')
        assert isinstance(node, BinaryOp)
        assert node.op == "+"
        assert isinstance(node.left, BinaryOp)
        assert node.left.op == "+"
        assert isinstance(node.left.left, ColorLiteral)
        assert node.left.left.name == "red"

    def test_dot_then_subscript(self):
        # obj.items~0~
        node = lex_parse("obj.items~0~")
        assert isinstance(node, IndexAccess)
        assert isinstance(node.obj, DotAccess)

    def test_nested_function_calls(self):
        # f(g(x))
        node = lex_parse("f(g(x))")
        assert isinstance(node, CallExpr)
        assert isinstance(node.args[0], CallExpr)
        assert node.args[0].callee.name == "g"

    def test_method_chain(self):
        # obj.foo().bar()  →  CallExpr(DotAccess(CallExpr(DotAccess(obj, foo), []), bar), [])
        node = lex_parse("obj.foo().bar()")
        assert isinstance(node, CallExpr)
        assert isinstance(node.callee, DotAccess)
        assert node.callee.attr == "bar"
        assert isinstance(node.callee.obj, CallExpr)

    def test_blade_dot_access(self):
        node = lex_parse("blade.name")
        assert isinstance(node, DotAccess)
        assert isinstance(node.obj, Identifier)
        assert node.obj.name == "blade"
        assert node.attr == "name"


# ===========================================================================
# Phase 3.5 — Pipeline operator
# ===========================================================================

class TestPipelineOperator:
    def test_pipeline_basic(self):
        # x |> f()  →  PipelineExpr(Identifier(x), CallExpr(f, []))
        node = lex_parse("x |> f()")
        assert isinstance(node, PipelineExpr)
        assert isinstance(node.left, Identifier)
        assert node.left.name == "x"
        assert isinstance(node.right, CallExpr)
        assert node.right.callee.name == "f"

    def test_pipeline_with_existing_args(self):
        # x |> f(y)  →  PipelineExpr(x, CallExpr(f, [y]))
        node = lex_parse("x |> f(y)")
        assert isinstance(node, PipelineExpr)
        assert isinstance(node.right, CallExpr)
        assert len(node.right.args) == 1

    def test_pipeline_left_associative(self):
        # a |> f() |> g()  →  (a |> f()) |> g()
        node = lex_parse("a |> f() |> g()")
        assert isinstance(node, PipelineExpr)
        assert isinstance(node.left, PipelineExpr)

    def test_pipeline_lower_than_arithmetic(self):
        # 1 + 2 |> f()  →  (1 + 2) |> f()
        node = lex_parse("1 + 2 |> f()")
        assert isinstance(node, PipelineExpr)
        assert isinstance(node.left, BinaryOp)
        assert node.left.op == "+"

    def test_pipeline_identifier(self):
        # items |> len
        # Note: right side doesn't have to be a call for parsing purposes
        node = lex_parse("items |> process()")
        assert isinstance(node, PipelineExpr)
        assert node.left.name == "items"


# ===========================================================================
# Pretty-writer integration (Phase 3.5 — verify output via pretty-writer)
# ===========================================================================

class TestPrettyWriter:
    def test_pretty_write_number(self):
        node = lex_parse("42")
        output = pretty_write(node)
        assert "NumberLiteral(42)" in output

    def test_pretty_write_binary_op(self):
        node = lex_parse("a + b")
        output = pretty_write(node)
        assert "BinaryOp(" in output
        assert "op='+'" in output
        assert "Identifier(a)" in output
        assert "Identifier(b)" in output

    def test_pretty_write_call_expr(self):
        node = lex_parse("write(42)")
        output = pretty_write(node)
        assert "CallExpr(" in output
        assert "Identifier(write)" in output
        assert "NumberLiteral(42)" in output

    def test_pretty_write_list(self):
        node = lex_parse("[1, 2, 3]")
        output = pretty_write(node)
        assert "ListLiteral([" in output
        assert "NumberLiteral(1)" in output

    def test_pretty_write_pipeline(self):
        node = lex_parse("x |> f()")
        output = pretty_write(node)
        assert "PipelineExpr(" in output
        assert "|>" in output

    def test_pretty_write_dot_access(self):
        node = lex_parse("obj.attr")
        output = pretty_write(node)
        assert "DotAccess(" in output
        assert ".attr" in output

    def test_pretty_write_index_access(self):
        node = lex_parse("items~0~")
        output = pretty_write(node)
        assert "IndexAccess(" in output
        assert "NumberLiteral(0)" in output

    def test_pretty_write_color(self):
        node = lex_parse("-*red*-")
        output = pretty_write(node)
        assert "ColorLiteral(-*red*-)" in output

    def test_pretty_write_program(self):
        prog = parse_source("42\n")
        output = pretty_write(prog)
        assert "Program(" in output
        assert "NumberLiteral(42)" in output


# ===========================================================================
# Edge cases & error handling
# ===========================================================================

class TestEdgeCases:
    def test_identifier(self):
        node = lex_parse("my_var")
        assert isinstance(node, Identifier)
        assert node.name == "my_var"

    def test_trailing_comma_in_list(self):
        # Trailing comma should be accepted
        node = lex_parse("[1, 2, 3,]")
        assert isinstance(node, ListLiteral)
        assert len(node.elements) == 3

    def test_trailing_comma_in_call(self):
        node = lex_parse("f(a, b,)")
        assert isinstance(node, CallExpr)
        assert len(node.args) == 2

    def test_deeply_nested_expr(self):
        node = lex_parse("((((42))))")
        assert isinstance(node, NumberLiteral)
        assert node.value == 42

    def test_line_col_preserved(self):
        node = lex_parse("42")
        assert node.line == 1
        assert node.col == 1

    def test_parse_error_on_invalid_token(self):
        with pytest.raises((ParseError, SyntaxError)):
            lex_parse("@invalid")


# ===========================================================================
# Week 4 — Statement Parser Tests (Phases 4.1–4.5)
# ===========================================================================

def parse_stmts(source: str) -> list:
    """Lex and parse source, returning the list of top-level statements."""
    prog = parse_source(source)
    return prog.statements


def first_stmt(source: str) -> object:
    """Return the first top-level statement from source."""
    return parse_stmts(source)[0]


# ---------------------------------------------------------------------------
# Phase 4.1 — Variable declaration and assignment
# ---------------------------------------------------------------------------

class TestVariableDeclaration:
    def test_simple_declaration(self):
        node = first_stmt(">> x = 42\n")
        assert isinstance(node, AssignStmt)
        assert node.name == "x"
        assert node.is_declaration is True
        assert isinstance(node.value, NumberLiteral)
        assert node.value.value == 42

    def test_string_declaration(self):
        node = first_stmt('>> name = "AxonBlade"\n')
        assert isinstance(node, AssignStmt)
        assert node.name == "name"
        assert node.is_declaration is True
        assert isinstance(node.value, StringLiteral)
        assert node.value.value == "AxonBlade"

    def test_bool_declaration(self):
        node = first_stmt(">> active = true\n")
        assert isinstance(node, AssignStmt)
        assert isinstance(node.value, BoolLiteral)
        assert node.value.value is True

    def test_null_declaration(self):
        node = first_stmt(">> nothing = null\n")
        assert isinstance(node, AssignStmt)
        assert isinstance(node.value, NullLiteral)

    def test_expression_declaration(self):
        node = first_stmt(">> result = 3 + 4\n")
        assert isinstance(node, AssignStmt)
        assert isinstance(node.value, BinaryOp)
        assert node.value.op == "+"

    def test_declaration_line_col(self):
        node = first_stmt(">> x = 1\n")
        assert node.line == 1

    def test_list_declaration(self):
        node = first_stmt(">> items = [1, 2, 3]\n")
        assert isinstance(node, AssignStmt)
        assert isinstance(node.value, ListLiteral)
        assert len(node.value.elements) == 3

    def test_dict_declaration(self):
        node = first_stmt(">> d = {a: 1, b: 2}\n")
        assert isinstance(node, AssignStmt)
        assert isinstance(node.value, DictLiteral)
        assert len(node.value.pairs) == 2


class TestReassignment:
    def test_bare_reassignment(self):
        node = first_stmt("x = 99\n")
        assert isinstance(node, AssignStmt)
        assert node.name == "x"
        assert node.is_declaration is False

    def test_reassignment_with_expr(self):
        node = first_stmt("count = count + 1\n")
        assert isinstance(node, AssignStmt)
        assert node.is_declaration is False
        assert isinstance(node.value, BinaryOp)

    def test_subscript_assignment(self):
        node = first_stmt('player~"hp"~ = 90\n')
        assert isinstance(node, AssignStmt)
        assert node.is_declaration is False
        assert isinstance(node.name, IndexAccess)

    def test_multiple_declarations(self):
        stmts = parse_stmts(">> a = 1\n>> b = 2\n>> c = 3\n")
        assert len(stmts) == 3
        assert all(isinstance(s, AssignStmt) for s in stmts)
        assert all(s.is_declaration for s in stmts)


# ---------------------------------------------------------------------------
# Phase 4.2 — Function definitions
# ---------------------------------------------------------------------------

class TestFunctionDefinition:
    def test_no_params(self):
        src = "bladeFN greet() +/\n    return 42\nECB\n"
        node = first_stmt(src)
        assert isinstance(node, FnDef)
        assert node.name == "greet"
        assert node.params == []
        assert len(node.body) == 1

    def test_single_param(self):
        src = "bladeFN double(x) +/\n    return x * 2\nECB\n"
        node = first_stmt(src)
        assert isinstance(node, FnDef)
        assert len(node.params) == 1
        assert node.params[0].name == "x"
        assert node.params[0].type_ann is None

    def test_typed_param(self):
        src = "bladeFN greet(name#str) +/\n    return name\nECB\n"
        node = first_stmt(src)
        assert isinstance(node, FnDef)
        assert node.params[0].name == "name"
        assert node.params[0].type_ann == "str"

    def test_multiple_typed_params(self):
        src = "bladeFN add(a#int, b#int) +/\n    return a + b\nECB\n"
        node = first_stmt(src)
        assert len(node.params) == 2
        assert node.params[0].type_ann == "int"
        assert node.params[1].type_ann == "int"

    def test_mixed_params(self):
        src = "bladeFN f(x, y#float) +/\n    return x\nECB\n"
        node = first_stmt(src)
        assert node.params[0].type_ann is None
        assert node.params[1].type_ann == "float"

    def test_nested_fn_def(self):
        src = (
            "bladeFN outer() +/\n"
            "    bladeFN inner() +/\n"
            "        return 1\n"
            "    ECB\n"
            "    return inner\n"
            "ECB\n"
        )
        node = first_stmt(src)
        assert isinstance(node, FnDef)
        assert node.name == "outer"
        inner = node.body[0]
        assert isinstance(inner, FnDef)
        assert inner.name == "inner"

    def test_fn_body_multiple_stmts(self):
        src = (
            "bladeFN f(x) +/\n"
            "    >> y = x + 1\n"
            "    return y\n"
            "ECB\n"
        )
        node = first_stmt(src)
        assert len(node.body) == 2
        assert isinstance(node.body[0], AssignStmt)
        assert isinstance(node.body[1], ReturnStmt)

    def test_fn_line_col(self):
        src = "bladeFN f() +/\n    return 1\nECB\n"
        node = first_stmt(src)
        assert node.line == 1
        assert node.col == 1


class TestBladeGRPDefinition:
    def test_simple_class(self):
        src = (
            "bladeGRP Dog +/\n"
            "    bladeFN bark(blade) +/\n"
            "        return 1\n"
            "    ECB\n"
            "ECB\n"
        )
        node = first_stmt(src)
        assert isinstance(node, BladeGRPDef)
        assert node.name == "Dog"
        assert len(node.methods) == 1
        assert node.methods[0].name == "bark"

    def test_class_multiple_methods(self):
        src = (
            "bladeGRP Animal +/\n"
            "    bladeFN init(blade, name#str) +/\n"
            "        blade.name = name\n"
            "    ECB\n"
            "    bladeFN speak(blade) +/\n"
            "        return blade.name\n"
            "    ECB\n"
            "ECB\n"
        )
        node = first_stmt(src)
        assert isinstance(node, BladeGRPDef)
        assert len(node.methods) == 2
        assert node.methods[0].name == "init"
        assert node.methods[1].name == "speak"

    def test_class_line_col(self):
        src = (
            "bladeGRP Foo +/\n"
            "    bladeFN init(blade) +/\n"
            "        return 1\n"
            "    ECB\n"
            "ECB\n"
        )
        node = first_stmt(src)
        assert node.line == 1


# ---------------------------------------------------------------------------
# Phase 4.3 — Control flow statements
# ---------------------------------------------------------------------------

class TestIfStatement:
    def test_simple_if(self):
        src = "if x > 0 +/\n    write(x)\nECB\n"
        node = first_stmt(src)
        assert isinstance(node, IfStmt)
        assert isinstance(node.condition, BinaryOp)
        assert node.condition.op == ">"
        assert len(node.then_body) == 1
        assert node.elif_clauses == []
        assert node.else_body is None

    def test_if_else(self):
        src = (
            "if x > 0 +/\n"
            "    write(x)\n"
            "ECB\n"
            "else +/\n"
            "    write(0)\n"
            "ECB\n"
        )
        node = first_stmt(src)
        assert isinstance(node, IfStmt)
        assert node.else_body is not None
        assert len(node.else_body) == 1

    def test_if_elif_else(self):
        src = (
            "if score >= 90 +/\n"
            "    write(\"A\")\n"
            "ECB\n"
            "elif score >= 75 +/\n"
            "    write(\"B\")\n"
            "ECB\n"
            "else +/\n"
            "    write(\"C\")\n"
            "ECB\n"
        )
        node = first_stmt(src)
        assert isinstance(node, IfStmt)
        assert len(node.elif_clauses) == 1
        elif_cond, elif_body = node.elif_clauses[0]
        assert isinstance(elif_cond, BinaryOp)
        assert node.else_body is not None

    def test_multiple_elif(self):
        src = (
            "if a +/\n    write(1)\nECB\n"
            "elif b +/\n    write(2)\nECB\n"
            "elif c +/\n    write(3)\nECB\n"
        )
        node = first_stmt(src)
        assert len(node.elif_clauses) == 2

    def test_if_line_col(self):
        src = "if true +/\n    write(1)\nECB\n"
        node = first_stmt(src)
        assert node.line == 1

    def test_nested_if(self):
        src = (
            "if x +/\n"
            "    if y +/\n"
            "        write(1)\n"
            "    ECB\n"
            "ECB\n"
        )
        node = first_stmt(src)
        assert isinstance(node, IfStmt)
        inner = node.then_body[0]
        assert isinstance(inner, IfStmt)


class TestWhileStatement:
    def test_simple_while(self):
        src = "while i < 10 +/\n    i = i + 1\nECB\n"
        node = first_stmt(src)
        assert isinstance(node, WhileStmt)
        assert isinstance(node.condition, BinaryOp)
        assert node.condition.op == "<"
        assert len(node.body) == 1

    def test_while_line_col(self):
        src = "while true +/\n    write(1)\nECB\n"
        node = first_stmt(src)
        assert node.line == 1

    def test_while_complex_condition(self):
        src = "while i < 10 -a running +/\n    write(i)\nECB\n"
        node = first_stmt(src)
        assert isinstance(node.condition, BinaryOp)
        assert node.condition.op == "-a"


class TestForStatement:
    def test_simple_for(self):
        src = "for n in nums +/\n    write(n)\nECB\n"
        node = first_stmt(src)
        assert isinstance(node, ForStmt)
        assert node.var_name == "n"
        assert isinstance(node.iterable, Identifier)
        assert node.iterable.name == "nums"
        assert len(node.body) == 1

    def test_for_with_range(self):
        src = "for i in range(10) +/\n    write(i)\nECB\n"
        node = first_stmt(src)
        assert isinstance(node, ForStmt)
        assert isinstance(node.iterable, CallExpr)

    def test_for_line_col(self):
        src = "for x in items +/\n    write(x)\nECB\n"
        node = first_stmt(src)
        assert node.line == 1

    def test_for_nested(self):
        src = (
            "for row in board +/\n"
            "    for cell in row +/\n"
            "        write(cell)\n"
            "    ECB\n"
            "ECB\n"
        )
        node = first_stmt(src)
        assert isinstance(node, ForStmt)
        inner = node.body[0]
        assert isinstance(inner, ForStmt)


# ---------------------------------------------------------------------------
# Phase 4.4 — Error handling and special statements
# ---------------------------------------------------------------------------

class TestTryCatch:
    def test_basic_try_catch(self):
        src = (
            "try +/\n"
            "    >> x = 1 / 0\n"
            "ECB\n"
            "catch e +/\n"
            "    write(e)\n"
            "ECB\n"
        )
        node = first_stmt(src)
        assert isinstance(node, TryCatch)
        assert node.catch_var == "e"
        assert len(node.try_body) == 1
        assert len(node.catch_body) == 1

    def test_try_catch_line_col(self):
        src = (
            "try +/\n    write(1)\nECB\n"
            "catch err +/\n    write(err)\nECB\n"
        )
        node = first_stmt(src)
        assert node.line == 1

    def test_try_multiple_stmts(self):
        src = (
            "try +/\n"
            "    >> a = 1\n"
            "    >> b = 2\n"
            "ECB\n"
            "catch e +/\n"
            "    write(e)\n"
            "ECB\n"
        )
        node = first_stmt(src)
        assert len(node.try_body) == 2


class TestUselib:
    def test_uselib_simple(self):
        src = "uselib -math-\n"
        node = first_stmt(src)
        assert isinstance(node, UselibStmt)
        assert node.module_name == "math"

    def test_uselib_string_path(self):
        src = 'uselib -"./mymodule"-\n'
        node = first_stmt(src)
        assert isinstance(node, UselibStmt)
        assert node.module_name == "./mymodule"

    def test_uselib_line_col(self):
        src = "uselib -math-\n"
        node = first_stmt(src)
        assert node.line == 1


class TestRaiseStatement:
    def test_raise_string(self):
        src = 'raise "Something went wrong"\n'
        node = first_stmt(src)
        assert isinstance(node, RaiseStmt)
        assert isinstance(node.message, StringLiteral)
        assert node.message.value == "Something went wrong"

    def test_raise_expression(self):
        src = "raise msg\n"
        node = first_stmt(src)
        assert isinstance(node, RaiseStmt)
        assert isinstance(node.message, Identifier)

    def test_raise_line_col(self):
        src = 'raise "err"\n'
        node = first_stmt(src)
        assert node.line == 1


class TestReturnStatement:
    def test_return_value(self):
        src = "bladeFN f() +/\n    return 42\nECB\n"
        fn = first_stmt(src)
        ret = fn.body[0]
        assert isinstance(ret, ReturnStmt)
        assert isinstance(ret.value, NumberLiteral)
        assert ret.value.value == 42

    def test_return_expression(self):
        src = "bladeFN f(x) +/\n    return x * 2\nECB\n"
        fn = first_stmt(src)
        ret = fn.body[0]
        assert isinstance(ret, ReturnStmt)
        assert isinstance(ret.value, BinaryOp)

    def test_return_identifier(self):
        src = "bladeFN f() +/\n    return result\nECB\n"
        fn = first_stmt(src)
        ret = fn.body[0]
        assert isinstance(ret.value, Identifier)


# ---------------------------------------------------------------------------
# Phase 4.5 — Program node and comprehensive integration
# ---------------------------------------------------------------------------

class TestProgramNode:
    def test_empty_program(self):
        prog = parse_source("")
        assert isinstance(prog, Program)
        assert prog.statements == []

    def test_single_statement(self):
        prog = parse_source(">> x = 1\n")
        assert len(prog.statements) == 1

    def test_multiple_statements(self):
        src = ">> a = 1\n>> b = 2\nwrite(a + b)\n"
        prog = parse_source(src)
        assert len(prog.statements) == 3

    def test_expression_statement(self):
        stmts = parse_stmts("write(\"hello\")\n")
        assert len(stmts) == 1
        assert isinstance(stmts[0], CallExpr)

    def test_program_skips_blank_lines(self):
        src = ">> a = 1\n\n>> b = 2\n"
        prog = parse_source(src)
        assert len(prog.statements) == 2

    def test_complex_program(self):
        src = (
            ">> x = 10\n"
            ">> y = 20\n"
            "if x > y +/\n"
            "    write(x)\n"
            "ECB\n"
            "else +/\n"
            "    write(y)\n"
            "ECB\n"
        )
        prog = parse_source(src)
        assert len(prog.statements) == 3
        assert isinstance(prog.statements[0], AssignStmt)
        assert isinstance(prog.statements[2], IfStmt)

    def test_fibonacci_program(self):
        src = (
            "bladeFN fib(n#int) +/\n"
            "    if n <= 1 +/\n"
            "        return n\n"
            "    ECB\n"
            "    return fib(n - 1) + fib(n - 2)\n"
            "ECB\n"
            ">> i = 0\n"
            "while i < 10 +/\n"
            "    write(fib(i))\n"
            "    i = i + 1\n"
            "ECB\n"
        )
        prog = parse_source(src)
        assert len(prog.statements) == 3
        fn, decl, loop = prog.statements
        assert isinstance(fn, FnDef)
        assert isinstance(decl, AssignStmt)
        assert isinstance(loop, WhileStmt)

    def test_closure_program(self):
        src = (
            "bladeFN make_counter() +/\n"
            "    >> count = 0\n"
            "    bladeFN increment() +/\n"
            "        count = count + 1\n"
            "        return count\n"
            "    ECB\n"
            "    return increment\n"
            "ECB\n"
        )
        prog = parse_source(src)
        outer = prog.statements[0]
        assert isinstance(outer, FnDef)
        assert len(outer.body) == 3  # decl, inner fn, return
        inner = outer.body[1]
        assert isinstance(inner, FnDef)

    def test_class_program(self):
        src = (
            "bladeGRP Animal +/\n"
            "    bladeFN init(blade, name#str, sound#str) +/\n"
            "        blade.name = name\n"
            "        blade.sound = sound\n"
            "    ECB\n"
            "    bladeFN speak(blade) +/\n"
            "        write(blade.name)\n"
            "    ECB\n"
            "ECB\n"
            ">> dog = Animal(\"Rex\", \"woof\")\n"
            "dog.speak()\n"
        )
        prog = parse_source(src)
        assert len(prog.statements) == 3
        assert isinstance(prog.statements[0], BladeGRPDef)
        assert isinstance(prog.statements[1], AssignStmt)
        assert isinstance(prog.statements[2], CallExpr)

    def test_try_catch_program(self):
        src = (
            "try +/\n"
            "    >> x = 10 / 0\n"
            "ECB\n"
            "catch e +/\n"
            "    write(e)\n"
            "ECB\n"
        )
        prog = parse_source(src)
        assert len(prog.statements) == 1
        assert isinstance(prog.statements[0], TryCatch)

    def test_uselib_program(self):
        src = (
            "uselib -math-\n"
            ">> r = math.sqrt(25)\n"
        )
        prog = parse_source(src)
        assert len(prog.statements) == 2
        assert isinstance(prog.statements[0], UselibStmt)

    def test_pretty_write_assign_stmt(self):
        node = first_stmt(">> x = 42\n")
        output = pretty_write(node)
        assert "AssignStmt" in output

    def test_pretty_write_fn_def(self):
        src = "bladeFN f(x#int) +/\n    return x\nECB\n"
        node = first_stmt(src)
        output = pretty_write(node)
        assert "FnDef" in output

    def test_pretty_write_if_stmt(self):
        src = "if true +/\n    write(1)\nECB\n"
        node = first_stmt(src)
        output = pretty_write(node)
        assert "IfStmt" in output

    def test_for_with_list_literal(self):
        src = "for item in [1, 2, 3] +/\n    write(item)\nECB\n"
        node = first_stmt(src)
        assert isinstance(node, ForStmt)
        assert isinstance(node.iterable, ListLiteral)
