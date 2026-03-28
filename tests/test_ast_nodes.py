"""
Test suite for AxonBlade AST Nodes (Phase 2.5).
Tests every node constructor for correct fields and the pretty-writer output.
"""

import pytest
from core.ast_nodes import (
    # Literals
    NumberLiteral, StringLiteral, FStringLiteral, ColorLiteral,
    BoolLiteral, NullLiteral, ListLiteral, DictLiteral,
    # Expressions
    Identifier, BinaryOp, UnaryOp, CallExpr, DotAccess,
    IndexAccess, SliceAccess, PipelineExpr,
    # Statements
    AssignStmt, Param, FnDef, ReturnStmt, RaiseStmt,
    IfStmt, WhileStmt, ForStmt, BladeGRPDef, TryCatch,
    UselibStmt, Program,
    # Pretty-writer
    pretty_write,
)


# ===========================================================================
# Helpers
# ===========================================================================

def num(v, line=1, col=1):
    return NumberLiteral(v, line, col)

def ident(name, line=1, col=1):
    return Identifier(name, line, col)


# ===========================================================================
# Phase 2.1 — Literal Node Constructors
# ===========================================================================

class TestNumberLiteral:
    def test_integer_value(self):
        node = NumberLiteral(42, 1, 5)
        assert node.value == 42
        assert node.line == 1
        assert node.col == 5

    def test_float_value(self):
        node = NumberLiteral(3.14, 2, 3)
        assert node.value == 3.14
        assert node.line == 2
        assert node.col == 3

    def test_zero(self):
        node = NumberLiteral(0, 1, 1)
        assert node.value == 0

    def test_negative_value(self):
        node = NumberLiteral(-7.5, 1, 1)
        assert node.value == -7.5


class TestStringLiteral:
    def test_basic_string(self):
        node = StringLiteral("hello", 1, 1)
        assert node.value == "hello"
        assert node.line == 1
        assert node.col == 1

    def test_empty_string(self):
        node = StringLiteral("", 3, 7)
        assert node.value == ""

    def test_string_with_spaces(self):
        node = StringLiteral("hello world", 1, 1)
        assert node.value == "hello world"


class TestFStringLiteral:
    def test_parts_list(self):
        expr = num(42)
        node = FStringLiteral(["Hello ", expr, "!"], 1, 1)
        assert len(node.parts) == 3
        assert node.parts[0] == "Hello "
        assert node.parts[1] is expr
        assert node.parts[2] == "!"

    def test_empty_parts(self):
        node = FStringLiteral([], 1, 1)
        assert node.parts == []

    def test_string_only_parts(self):
        node = FStringLiteral(["no interpolation"], 1, 1)
        assert node.parts == ["no interpolation"]

    def test_line_col(self):
        node = FStringLiteral([], 4, 9)
        assert node.line == 4
        assert node.col == 9


class TestColorLiteral:
    def test_color_name(self):
        node = ColorLiteral("red", 1, 1)
        assert node.name == "red"

    def test_various_colors(self):
        for color in ("blue", "green", "cyan", "reset", "black", "white"):
            node = ColorLiteral(color, 1, 1)
            assert node.name == color

    def test_line_col(self):
        node = ColorLiteral("magenta", 5, 12)
        assert node.line == 5
        assert node.col == 12


class TestBoolLiteral:
    def test_true(self):
        node = BoolLiteral(True, 1, 1)
        assert node.value is True

    def test_false(self):
        node = BoolLiteral(False, 2, 4)
        assert node.value is False

    def test_line_col(self):
        node = BoolLiteral(True, 3, 8)
        assert node.line == 3
        assert node.col == 8


class TestNullLiteral:
    def test_fields(self):
        node = NullLiteral(1, 1)
        assert node.line == 1
        assert node.col == 1

    def test_different_position(self):
        node = NullLiteral(7, 14)
        assert node.line == 7
        assert node.col == 14


class TestListLiteral:
    def test_empty_list(self):
        node = ListLiteral([], 1, 1)
        assert node.elements == []

    def test_with_elements(self):
        elems = [num(1), num(2), num(3)]
        node = ListLiteral(elems, 1, 1)
        assert len(node.elements) == 3
        assert node.elements[0].value == 1

    def test_line_col(self):
        node = ListLiteral([], 3, 5)
        assert node.line == 3
        assert node.col == 5


class TestDictLiteral:
    def test_empty_dict(self):
        node = DictLiteral([], 1, 1)
        assert node.pairs == []

    def test_with_pairs(self):
        pairs = [
            (StringLiteral("a", 1, 1), num(1)),
            (StringLiteral("b", 1, 1), num(2)),
        ]
        node = DictLiteral(pairs, 1, 1)
        assert len(node.pairs) == 2
        assert node.pairs[0][0].value == "a"
        assert node.pairs[0][1].value == 1

    def test_line_col(self):
        node = DictLiteral([], 2, 6)
        assert node.line == 2
        assert node.col == 6


# ===========================================================================
# Phase 2.2 — Expression Node Constructors
# ===========================================================================

class TestIdentifier:
    def test_name(self):
        node = Identifier("foo", 1, 1)
        assert node.name == "foo"

    def test_underscore_name(self):
        node = Identifier("my_var", 2, 3)
        assert node.name == "my_var"

    def test_line_col(self):
        node = Identifier("x", 5, 10)
        assert node.line == 5
        assert node.col == 10


class TestBinaryOp:
    def test_addition(self):
        left = num(1)
        right = num(2)
        node = BinaryOp(left, "+", right, 1, 1)
        assert node.left is left
        assert node.op == "+"
        assert node.right is right

    def test_all_operators(self):
        ops = ["+", "-", "*", "/", "**", "%", "==", "!=", "<", ">", "<=", ">="]
        for op in ops:
            node = BinaryOp(num(1), op, num(2), 1, 1)
            assert node.op == op

    def test_line_col(self):
        node = BinaryOp(num(1), "+", num(2), 4, 7)
        assert node.line == 4
        assert node.col == 7


class TestUnaryOp:
    def test_negation(self):
        operand = num(5)
        node = UnaryOp("-", operand, 1, 1)
        assert node.op == "-"
        assert node.operand is operand

    def test_not(self):
        operand = BoolLiteral(True, 1, 1)
        node = UnaryOp("-n", operand, 1, 1)
        assert node.op == "-n"
        assert node.operand is operand

    def test_line_col(self):
        node = UnaryOp("-", num(1), 2, 3)
        assert node.line == 2
        assert node.col == 3


class TestCallExpr:
    def test_no_args(self):
        callee = ident("foo")
        node = CallExpr(callee, [], 1, 1)
        assert node.callee is callee
        assert node.args == []

    def test_with_args(self):
        callee = ident("add")
        args = [num(1), num(2)]
        node = CallExpr(callee, args, 1, 1)
        assert len(node.args) == 2

    def test_dotaccess_callee(self):
        obj = ident("my_list")
        dot = DotAccess(obj, "append", 1, 1)
        node = CallExpr(dot, [num(5)], 1, 1)
        assert isinstance(node.callee, DotAccess)

    def test_line_col(self):
        node = CallExpr(ident("f"), [], 6, 2)
        assert node.line == 6
        assert node.col == 2


class TestDotAccess:
    def test_fields(self):
        obj = ident("player")
        node = DotAccess(obj, "hp", 1, 1)
        assert node.obj is obj
        assert node.attr == "hp"

    def test_line_col(self):
        node = DotAccess(ident("x"), "y", 3, 4)
        assert node.line == 3
        assert node.col == 4


class TestIndexAccess:
    def test_fields(self):
        obj = ident("items")
        idx = num(0)
        node = IndexAccess(obj, idx, 1, 1)
        assert node.obj is obj
        assert node.index is idx

    def test_line_col(self):
        node = IndexAccess(ident("a"), num(1), 2, 5)
        assert node.line == 2
        assert node.col == 5


class TestSliceAccess:
    def test_with_both_bounds(self):
        obj = ident("arr")
        start = num(1)
        end = num(3)
        node = SliceAccess(obj, start, end, 1, 1)
        assert node.obj is obj
        assert node.start is start
        assert node.end is end

    def test_with_none_bounds(self):
        node = SliceAccess(ident("arr"), None, None, 1, 1)
        assert node.start is None
        assert node.end is None

    def test_start_only(self):
        node = SliceAccess(ident("arr"), num(2), None, 1, 1)
        assert node.start.value == 2
        assert node.end is None

    def test_line_col(self):
        node = SliceAccess(ident("a"), num(0), num(5), 4, 8)
        assert node.line == 4
        assert node.col == 8


class TestPipelineExpr:
    def test_fields(self):
        left = ident("data")
        right = CallExpr(ident("process"), [], 1, 1)
        node = PipelineExpr(left, right, 1, 1)
        assert node.left is left
        assert node.right is right

    def test_right_is_call_expr(self):
        node = PipelineExpr(
            num(5),
            CallExpr(ident("double"), [], 1, 1),
            1, 1
        )
        assert isinstance(node.right, CallExpr)

    def test_line_col(self):
        node = PipelineExpr(ident("x"), CallExpr(ident("f"), [], 1, 1), 2, 9)
        assert node.line == 2
        assert node.col == 9


# ===========================================================================
# Phase 2.3 — Statement Node Constructors
# ===========================================================================

class TestAssignStmt:
    def test_declaration(self):
        value = num(10)
        node = AssignStmt("x", value, True, 1, 1)
        assert node.name == "x"
        assert node.value is value
        assert node.is_declaration is True

    def test_reassignment(self):
        node = AssignStmt("x", num(20), False, 2, 1)
        assert node.is_declaration is False

    def test_line_col(self):
        node = AssignStmt("v", num(0), True, 5, 3)
        assert node.line == 5
        assert node.col == 3


class TestParam:
    def test_no_type_annotation(self):
        p = Param("name", None)
        assert p.name == "name"
        assert p.type_ann is None

    def test_with_type_annotation(self):
        p = Param("age", "int")
        assert p.name == "age"
        assert p.type_ann == "int"

    def test_all_supported_types(self):
        for t in ("str", "int", "float", "bool", "list", "dict", "grid", "fn", "any"):
            p = Param("x", t)
            assert p.type_ann == t

    def test_no_line_col(self):
        # Param intentionally has no line/col per spec
        p = Param("x", None)
        assert not hasattr(p, "line")
        assert not hasattr(p, "col")


class TestFnDef:
    def test_basic_fields(self):
        params = [Param("a", None), Param("b", "int")]
        body = [ReturnStmt(BinaryOp(ident("a"), "+", ident("b"), 2, 1), 2, 1)]
        node = FnDef("add", params, body, 1, 1)
        assert node.name == "add"
        assert len(node.params) == 2
        assert len(node.body) == 1

    def test_no_params(self):
        node = FnDef("greet", [], [], 1, 1)
        assert node.params == []

    def test_line_col(self):
        node = FnDef("f", [], [], 3, 5)
        assert node.line == 3
        assert node.col == 5


class TestReturnStmt:
    def test_return_value(self):
        value = num(42)
        node = ReturnStmt(value, 1, 1)
        assert node.value is value

    def test_line_col(self):
        node = ReturnStmt(num(0), 7, 2)
        assert node.line == 7
        assert node.col == 2


class TestRaiseStmt:
    def test_message(self):
        msg = StringLiteral("bad input", 1, 1)
        node = RaiseStmt(msg, 1, 1)
        assert node.message is msg

    def test_line_col(self):
        node = RaiseStmt(StringLiteral("err", 1, 1), 4, 6)
        assert node.line == 4
        assert node.col == 6


class TestIfStmt:
    def test_if_only(self):
        cond = BoolLiteral(True, 1, 1)
        body = [ReturnStmt(num(1), 2, 1)]
        node = IfStmt(cond, body, [], None, 1, 1)
        assert node.condition is cond
        assert node.then_body is body
        assert node.elif_clauses == []
        assert node.else_body is None

    def test_with_elif_and_else(self):
        cond = BoolLiteral(True, 1, 1)
        elif_cond = BoolLiteral(False, 3, 1)
        elif_body = [ReturnStmt(num(2), 4, 1)]
        else_body = [ReturnStmt(num(3), 6, 1)]
        node = IfStmt(cond, [], [(elif_cond, elif_body)], else_body, 1, 1)
        assert len(node.elif_clauses) == 1
        assert node.elif_clauses[0][0] is elif_cond
        assert node.else_body is else_body

    def test_else_body_none_vs_empty(self):
        node_none = IfStmt(BoolLiteral(True, 1, 1), [], [], None, 1, 1)
        node_empty = IfStmt(BoolLiteral(True, 1, 1), [], [], [], 1, 1)
        assert node_none.else_body is None
        assert node_empty.else_body == []

    def test_line_col(self):
        node = IfStmt(BoolLiteral(True, 1, 1), [], [], None, 3, 1)
        assert node.line == 3


class TestWhileStmt:
    def test_fields(self):
        cond = BinaryOp(ident("i"), "<", num(10), 1, 1)
        body = [AssignStmt("i", BinaryOp(ident("i"), "+", num(1), 2, 1), False, 2, 1)]
        node = WhileStmt(cond, body, 1, 1)
        assert node.condition is cond
        assert len(node.body) == 1

    def test_line_col(self):
        node = WhileStmt(BoolLiteral(True, 1, 1), [], 5, 1)
        assert node.line == 5
        assert node.col == 1


class TestForStmt:
    def test_fields(self):
        iterable = ident("items")
        body = [ReturnStmt(ident("n"), 2, 1)]
        node = ForStmt("n", iterable, body, 1, 1)
        assert node.var_name == "n"
        assert node.iterable is iterable
        assert len(node.body) == 1

    def test_line_col(self):
        node = ForStmt("x", ident("lst"), [], 4, 1)
        assert node.line == 4
        assert node.col == 1


class TestBladeGRPDef:
    def test_fields(self):
        method = FnDef("speak", [Param("self", None)], [], 2, 1)
        node = BladeGRPDef("Animal", [method], 1, 1)
        assert node.name == "Animal"
        assert len(node.methods) == 1
        assert node.methods[0].name == "speak"

    def test_no_methods(self):
        node = BladeGRPDef("Empty", [], 1, 1)
        assert node.methods == []

    def test_line_col(self):
        node = BladeGRPDef("Foo", [], 6, 1)
        assert node.line == 6


class TestTryCatch:
    def test_fields(self):
        try_body = [AssignStmt("x", num(1), True, 2, 1)]
        catch_body = [ReturnStmt(ident("e"), 4, 1)]
        node = TryCatch(try_body, "e", catch_body, 1, 1)
        assert node.try_body is try_body
        assert node.catch_var == "e"
        assert node.catch_body is catch_body

    def test_line_col(self):
        node = TryCatch([], "err", [], 8, 1)
        assert node.line == 8
        assert node.col == 1


class TestUselibStmt:
    def test_module_name(self):
        node = UselibStmt("math", 1, 1)
        assert node.module_name == "math"

    def test_path_module(self):
        node = UselibStmt("./mymodule", 1, 1)
        assert node.module_name == "./mymodule"

    def test_line_col(self):
        node = UselibStmt("math", 3, 1)
        assert node.line == 3
        assert node.col == 1


class TestProgram:
    def test_empty(self):
        node = Program([])
        assert node.statements == []

    def test_with_statements(self):
        stmts = [
            AssignStmt("x", num(1), True, 1, 1),
            AssignStmt("y", num(2), True, 2, 1),
        ]
        node = Program(stmts)
        assert len(node.statements) == 2

    def test_no_line_col(self):
        # Program intentionally has no line/col per spec
        node = Program([])
        assert not hasattr(node, "line")
        assert not hasattr(node, "col")


# ===========================================================================
# Phase 2.4 — Pretty-writer Output
# ===========================================================================

class TestPrettyWriteLiterals:
    def test_number_int(self):
        assert pretty_write(num(42)) == "NumberLiteral(42)"

    def test_number_float(self):
        assert pretty_write(NumberLiteral(3.14, 1, 1)) == "NumberLiteral(3.14)"

    def test_string(self):
        assert pretty_write(StringLiteral("hi", 1, 1)) == "StringLiteral('hi')"

    def test_string_repr_escaping(self):
        # value with a quote should be repr'd
        node = StringLiteral("say \"hi\"", 1, 1)
        assert "say" in pretty_write(node)

    def test_color(self):
        assert pretty_write(ColorLiteral("red", 1, 1)) == "ColorLiteral(-*red*-)"

    def test_bool_true(self):
        assert pretty_write(BoolLiteral(True, 1, 1)) == "BoolLiteral(True)"

    def test_bool_false(self):
        assert pretty_write(BoolLiteral(False, 1, 1)) == "BoolLiteral(False)"

    def test_null(self):
        assert pretty_write(NullLiteral(1, 1)) == "NullLiteral()"

    def test_empty_list(self):
        assert pretty_write(ListLiteral([], 1, 1)) == "ListLiteral([])"

    def test_list_with_elements(self):
        result = pretty_write(ListLiteral([num(1), num(2)], 1, 1))
        assert "ListLiteral([" in result
        assert "NumberLiteral(1)" in result
        assert "NumberLiteral(2)" in result

    def test_empty_dict(self):
        result = pretty_write(DictLiteral([], 1, 1))
        assert "DictLiteral" in result

    def test_dict_with_pairs(self):
        pairs = [(StringLiteral("key", 1, 1), num(99))]
        result = pretty_write(DictLiteral(pairs, 1, 1))
        assert "DictLiteral" in result
        assert "key" in result
        assert "99" in result

    def test_fstring_parts(self):
        node = FStringLiteral(["Hello ", ident("name"), "!"], 1, 1)
        result = pretty_write(node)
        assert "FStringLiteral(" in result
        assert "StringPart('Hello ')" in result
        assert "Identifier(name)" in result
        assert "StringPart('!')" in result

    def test_fstring_empty(self):
        result = pretty_write(FStringLiteral([], 1, 1))
        assert "FStringLiteral(" in result


class TestPrettyWriteExpressions:
    def test_identifier(self):
        assert pretty_write(ident("foo")) == "Identifier(foo)"

    def test_binary_op(self):
        node = BinaryOp(num(1), "+", num(2), 1, 1)
        result = pretty_write(node)
        assert "BinaryOp(" in result
        assert "op='+'" in result
        assert "NumberLiteral(1)" in result
        assert "NumberLiteral(2)" in result

    def test_unary_op(self):
        node = UnaryOp("-", num(5), 1, 1)
        result = pretty_write(node)
        assert "UnaryOp(op='-'" in result
        assert "NumberLiteral(5)" in result

    def test_call_expr_no_args(self):
        node = CallExpr(ident("foo"), [], 1, 1)
        result = pretty_write(node)
        assert "CallExpr(" in result
        assert "Identifier(foo)" in result
        assert "args=[]" in result

    def test_call_expr_with_args(self):
        node = CallExpr(ident("add"), [num(1), num(2)], 1, 1)
        result = pretty_write(node)
        assert "args=[" in result
        assert "NumberLiteral(1)" in result

    def test_dot_access(self):
        node = DotAccess(ident("obj"), "hp", 1, 1)
        result = pretty_write(node)
        assert "DotAccess(" in result
        assert "Identifier(obj)" in result
        assert ".hp" in result

    def test_index_access(self):
        node = IndexAccess(ident("arr"), num(0), 1, 1)
        result = pretty_write(node)
        assert "IndexAccess(" in result
        assert "Identifier(arr)" in result
        assert "NumberLiteral(0)" in result

    def test_slice_access_with_bounds(self):
        node = SliceAccess(ident("arr"), num(1), num(3), 1, 1)
        result = pretty_write(node)
        assert "SliceAccess(" in result
        assert "start=NumberLiteral(1)" in result
        assert "end=NumberLiteral(3)" in result

    def test_slice_access_none_bounds(self):
        node = SliceAccess(ident("arr"), None, None, 1, 1)
        result = pretty_write(node)
        assert "start=None" in result
        assert "end=None" in result

    def test_pipeline_expr(self):
        node = PipelineExpr(ident("data"), CallExpr(ident("process"), [], 1, 1), 1, 1)
        result = pretty_write(node)
        assert "PipelineExpr(" in result
        assert "|>" in result
        assert "Identifier(data)" in result
        assert "CallExpr(" in result


class TestPrettyWriteStatements:
    def test_assign_declaration(self):
        node = AssignStmt("x", num(10), True, 1, 1)
        result = pretty_write(node)
        assert "AssignStmt(>> x =" in result
        assert "NumberLiteral(10)" in result

    def test_assign_reassignment(self):
        node = AssignStmt("x", num(20), False, 1, 1)
        result = pretty_write(node)
        assert "AssignStmt(x =" in result
        assert ">>" not in result

    def test_param_no_annotation(self):
        p = Param("name", None)
        assert pretty_write(p) == "Param(name)"

    def test_param_with_annotation(self):
        p = Param("age", "int")
        assert pretty_write(p) == "Param(age#int)"

    def test_fn_def_no_params(self):
        node = FnDef("greet", [], [ReturnStmt(num(0), 2, 1)], 1, 1)
        result = pretty_write(node)
        assert "FnDef(greet() +/" in result
        assert "ECB)" in result
        assert "ReturnStmt(" in result

    def test_fn_def_with_params(self):
        params = [Param("a", None), Param("b", "int")]
        node = FnDef("add", params, [], 1, 1)
        result = pretty_write(node)
        assert "FnDef(add(a, b#int) +/" in result

    def test_return_stmt(self):
        node = ReturnStmt(num(42), 1, 1)
        result = pretty_write(node)
        assert "ReturnStmt(" in result
        assert "NumberLiteral(42)" in result

    def test_raise_stmt(self):
        node = RaiseStmt(StringLiteral("oops", 1, 1), 1, 1)
        result = pretty_write(node)
        assert "RaiseStmt(" in result
        assert "'oops'" in result

    def test_if_stmt_no_elif_no_else(self):
        node = IfStmt(BoolLiteral(True, 1, 1), [ReturnStmt(num(1), 2, 1)], [], None, 1, 1)
        result = pretty_write(node)
        assert "IfStmt(" in result
        assert "then +/" in result
        assert "ECB)" in result
        assert "elif" not in result
        assert "else" not in result

    def test_if_stmt_with_elif(self):
        elif_cond = BoolLiteral(False, 3, 1)
        elif_body = [ReturnStmt(num(2), 4, 1)]
        node = IfStmt(BoolLiteral(True, 1, 1), [], [(elif_cond, elif_body)], None, 1, 1)
        result = pretty_write(node)
        assert "elif" in result

    def test_if_stmt_with_else(self):
        node = IfStmt(BoolLiteral(True, 1, 1), [], [], [ReturnStmt(num(0), 5, 1)], 1, 1)
        result = pretty_write(node)
        assert "else +/" in result

    def test_while_stmt(self):
        cond = BinaryOp(ident("i"), "<", num(5), 1, 1)
        node = WhileStmt(cond, [ReturnStmt(num(0), 2, 1)], 1, 1)
        result = pretty_write(node)
        assert "WhileStmt(" in result
        assert "+/" in result
        assert "ECB)" in result

    def test_for_stmt(self):
        node = ForStmt("n", ident("items"), [ReturnStmt(ident("n"), 2, 1)], 1, 1)
        result = pretty_write(node)
        assert "ForStmt(n in" in result
        assert "Identifier(items)" in result
        assert "ECB)" in result

    def test_blade_grp_def(self):
        method = FnDef("speak", [Param("self", None)], [], 2, 1)
        node = BladeGRPDef("Dog", [method], 1, 1)
        result = pretty_write(node)
        assert "BladeGRPDef(Dog +/" in result
        assert "FnDef(speak(self)" in result
        assert "ECB)" in result

    def test_try_catch(self):
        try_body = [AssignStmt("x", num(1), True, 2, 1)]
        catch_body = [ReturnStmt(ident("e"), 4, 1)]
        node = TryCatch(try_body, "e", catch_body, 1, 1)
        result = pretty_write(node)
        assert "TryCatch(" in result
        assert "try +/" in result
        assert "catch e +/" in result
        assert "ECB)" in result

    def test_uselib_stmt(self):
        node = UselibStmt("math", 1, 1)
        assert pretty_write(node) == "UselibStmt(-math-)"

    def test_uselib_stmt_path(self):
        node = UselibStmt("./mymodule", 1, 1)
        assert pretty_write(node) == "UselibStmt(-./mymodule-)"

    def test_program(self):
        stmts = [AssignStmt("x", num(1), True, 1, 1)]
        node = Program(stmts)
        result = pretty_write(node)
        assert "Program(" in result
        assert "AssignStmt(>> x =" in result

    def test_program_empty(self):
        result = pretty_write(Program([]))
        assert "Program(" in result


class TestPrettyWriteIndentation:
    def test_indent_level_zero(self):
        result = pretty_write(num(1), indent=0)
        assert result.startswith("NumberLiteral")

    def test_indent_level_one(self):
        result = pretty_write(num(1), indent=1)
        assert result.startswith("  NumberLiteral")

    def test_indent_level_two(self):
        result = pretty_write(num(1), indent=2)
        assert result.startswith("    NumberLiteral")

    def test_nested_binary_op_indentation(self):
        node = BinaryOp(num(1), "+", num(2), 1, 1)
        result = pretty_write(node, indent=1)
        lines = result.split("\n")
        # All lines should have at least 2-space base indent
        for line in lines:
            assert line.startswith("  "), f"Line missing indent: {repr(line)}"


class TestPrettyWriteUnknownNode:
    def test_unknown_node_type(self):
        class WeirdNode:
            pass
        result = pretty_write(WeirdNode())
        assert "<Unknown node: WeirdNode>" in result
