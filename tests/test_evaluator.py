"""
tests/test_evaluator.py — Week 5 + Week 6 evaluator tests (Phases 5.1-6.5).

Covers:
  - Literal evaluation
  - BinaryOp with type checking
  - UnaryOp
  - Variables and scoping
  - Control flow: if/elif/else, while, for
  - F-string interpolation
  - Functions, closures, type-annotated params
  - bladeGRP class system
  - Pipeline operator
  - Built-in functions
  - Error handling (AxonTypeError, AxonNameError, etc.)
"""

import pytest

from core.evaluator import (
    AxonFunction,
    AxonBladeGRP,
    AxonInstance,
    BoundMethod,
    Evaluator,
)
from core.environment import Environment
from core.errors import (
    AxonDivisionError,
    AxonNameError,
    AxonTypeError,
    AxonRuntimeError,
    AxonIndexError,
)
from core.parser import parse_source
from stdlib.builtins import build_global_env


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ev = Evaluator()


def run(source: str, env: Environment | None = None) -> object:
    """Parse and evaluate AxonBlade source, returning the last value."""
    if env is None:
        env = build_global_env()
    prog = parse_source(source)
    return _ev.eval(prog, env)


def run_env(source: str) -> tuple[object, Environment]:
    """Run source and return (last_value, env) for inspecting variables."""
    env = build_global_env()
    prog = parse_source(source)
    result = _ev.eval(prog, env)
    return result, env


# ===========================================================================
# Phase 5.2 — Literals
# ===========================================================================

class TestLiteralEval:
    def test_integer(self):
        assert run("42\n") == 42

    def test_float(self):
        assert run("3.14\n") == pytest.approx(3.14)

    def test_whole_float_becomes_int(self):
        assert run("4.0\n") == 4
        assert isinstance(run("4.0\n"), int)

    def test_string(self):
        assert run('"hello"\n') == "hello"

    def test_bool_true(self):
        assert run("true\n") is True

    def test_bool_false(self):
        assert run("false\n") is False

    def test_null(self):
        assert run("null\n") is None

    def test_color_red(self):
        assert run("-*red*-\n") == "\033[31m"

    def test_color_reset(self):
        assert run("-*reset*-\n") == "\033[0m"

    def test_color_cyan(self):
        assert run("-*cyan*-\n") == "\033[36m"

    def test_list_literal(self):
        assert run("[1, 2, 3]\n") == [1, 2, 3]

    def test_dict_literal(self):
        assert run('{a: 1, b: 2}\n') == {"a": 1, "b": 2}

    def test_empty_list(self):
        assert run("[]\n") == []

    def test_empty_dict(self):
        assert run("{}\n") == {}


# ===========================================================================
# Phase 5.3 — BinaryOp and UnaryOp
# ===========================================================================

class TestArithmetic:
    def test_addition(self):
        assert run("3 + 4\n") == 7

    def test_subtraction(self):
        assert run("10 - 3\n") == 7

    def test_multiplication(self):
        assert run("3 * 4\n") == 12

    def test_division_whole(self):
        assert run("10 / 2\n") == 5
        assert isinstance(run("10 / 2\n"), int)

    def test_division_float(self):
        assert run("7 / 2\n") == pytest.approx(3.5)

    def test_modulo(self):
        assert run("10 % 3\n") == 1

    def test_power(self):
        assert run("2 ** 8\n") == 256

    def test_string_concat(self):
        assert run('"hello" + " world"\n') == "hello world"

    def test_unary_minus(self):
        assert run("-5\n") == -5

    def test_unary_not_true(self):
        assert run("-n true\n") is False

    def test_unary_not_false(self):
        assert run("-n false\n") is True

    def test_chained_arithmetic(self):
        assert run("2 + 3 * 4\n") == 14  # * higher precedence


class TestComparisons:
    def test_eq_true(self):
        assert run("3 == 3\n") is True

    def test_eq_false(self):
        assert run("3 == 4\n") is False

    def test_neq(self):
        assert run("3 != 4\n") is True

    def test_lt(self):
        assert run("3 < 4\n") is True

    def test_gt(self):
        assert run("4 > 3\n") is True

    def test_lte(self):
        assert run("3 <= 3\n") is True

    def test_gte(self):
        assert run("5 >= 5\n") is True


class TestLogical:
    def test_and_true(self):
        assert run("true -a true\n") is True

    def test_and_false(self):
        assert run("true -a false\n") is False

    def test_or_true(self):
        assert run("false -o true\n") is True

    def test_or_false(self):
        assert run("false -o false\n") is False

    def test_and_short_circuit(self):
        # false -a (division by zero) — right side should not be evaluated
        assert run("false -a 1/0\n") is False

    def test_or_short_circuit(self):
        assert run("true -o 1/0\n") is True


class TestTypeErrors:
    def test_str_plus_int(self):
        with pytest.raises(AxonTypeError):
            run('"hello" + 42\n')

    def test_bool_plus_int(self):
        with pytest.raises(AxonTypeError):
            run("true + 1\n")

    def test_list_multiply_str(self):
        with pytest.raises(AxonTypeError):
            run('[1,2,3] * "x"\n')

    def test_division_by_zero(self):
        with pytest.raises(AxonDivisionError):
            run("10 / 0\n")

    def test_modulo_by_zero(self):
        with pytest.raises(AxonDivisionError):
            run("5 % 0\n")


# ===========================================================================
# Phase 5.4 — Variables and control flow
# ===========================================================================

class TestVariables:
    def test_declare_and_get(self):
        _, env = run_env(">> x = 42\n")
        assert env.get("x") == 42

    def test_reassign(self):
        _, env = run_env(">> x = 10\nx = 20\n")
        assert env.get("x") == 20

    def test_declaration_is_local(self):
        src = (
            ">> x = 1\n"
            "bladeFN f() +/\n"
            "    >> x = 99\n"
            "ECB\n"
            "f()\n"
        )
        _, env = run_env(src)
        assert env.get("x") == 1  # outer x unchanged

    def test_undefined_var(self):
        with pytest.raises(AxonNameError):
            run("x\n")

    def test_multiple_vars(self):
        _, env = run_env(">> a = 1\n>> b = 2\n>> c = a + b\n")
        assert env.get("c") == 3


class TestControlFlow:
    def test_if_true(self):
        _, env = run_env(">> x = 0\nif true +/\n    x = 1\nECB\n")
        assert env.get("x") == 1

    def test_if_false(self):
        _, env = run_env(">> x = 0\nif false +/\n    x = 1\nECB\n")
        assert env.get("x") == 0

    def test_if_else(self):
        _, env = run_env(
            ">> x = 0\n"
            "if false +/\n    x = 1\nECB\n"
            "else +/\n    x = 2\nECB\n"
        )
        assert env.get("x") == 2

    def test_if_elif_else(self):
        _, env = run_env(
            ">> score = 80\n"
            ">> grade = \"C\"\n"
            "if score >= 90 +/\n    grade = \"A\"\nECB\n"
            "elif score >= 75 +/\n    grade = \"B\"\nECB\n"
            "else +/\n    grade = \"C\"\nECB\n"
        )
        assert env.get("grade") == "B"

    def test_while_loop(self):
        _, env = run_env(
            ">> i = 0\n"
            ">> total = 0\n"
            "while i < 5 +/\n"
            "    total = total + i\n"
            "    i = i + 1\n"
            "ECB\n"
        )
        assert env.get("total") == 10

    def test_for_loop(self):
        _, env = run_env(
            ">> total = 0\n"
            "for n in [1, 2, 3, 4, 5] +/\n"
            "    total = total + n\n"
            "ECB\n"
        )
        assert env.get("total") == 15

    def test_for_with_range(self):
        _, env = run_env(
            ">> total = 0\n"
            "for i in range(5) +/\n"
            "    total = total + i\n"
            "ECB\n"
        )
        assert env.get("total") == 10

    def test_nested_for(self):
        _, env = run_env(
            ">> count = 0\n"
            "for i in range(3) +/\n"
            "    for j in range(3) +/\n"
            "        count = count + 1\n"
            "    ECB\n"
            "ECB\n"
        )
        assert env.get("count") == 9

    def test_index_access(self):
        assert run(">> items = [10, 20, 30]\nitems~1~\n") == 20

    def test_dict_access(self):
        assert run('>> d = {a: 1}\nd~"a"~\n') == 1

    def test_slice_access(self):
        assert run(">> items = [1, 2, 3, 4, 5]\nitems~1:3~\n") == [2, 3]

    def test_subscript_assignment(self):
        _, env = run_env('>> d = {a: 1}\nd~"a"~ = 99\n')
        assert env.get("d")["a"] == 99


# ===========================================================================
# Phase 5.5 — F-string interpolation
# ===========================================================================

class TestFString:
    def test_simple_interpolation(self):
        _, env = run_env('>> name = "AxonBlade"\n')
        assert run('>> name = "World"\n"Hello &{name}"\n') == "Hello World"

    def test_expression_interpolation(self):
        assert run('"Result: &{3 + 4}"\n') == "Result: 7"

    def test_multiple_interpolations(self):
        assert run('"&{1} + &{2} = &{1 + 2}"\n') == "1 + 2 = 3"

    def test_null_interpolation(self):
        assert run('"value: &{null}"\n') == "value: null"

    def test_bool_interpolation(self):
        assert run('"flag: &{true}"\n') == "flag: true"


# ===========================================================================
# Phase 6.1–6.3 — Functions and closures
# ===========================================================================

class TestFunctions:
    def test_basic_function(self):
        assert run("bladeFN double(x) +/\n    return x * 2\nECB\ndouble(5)\n") == 10

    def test_function_no_return(self):
        assert run("bladeFN noop() +/\n    >> x = 1\nECB\nnoop()\n") is None

    def test_function_multiple_params(self):
        assert run("bladeFN add(a, b) +/\n    return a + b\nECB\nadd(3, 4)\n") == 7

    def test_recursive_function(self):
        src = (
            "bladeFN fib(n) +/\n"
            "    if n <= 1 +/\n"
            "        return n\n"
            "    ECB\n"
            "    return fib(n - 1) + fib(n - 2)\n"
            "ECB\n"
            "fib(7)\n"
        )
        assert run(src) == 13

    def test_typed_param_str(self):
        src = 'bladeFN greet(name#str) +/\n    return name\nECB\ngreet("Ada")\n'
        assert run(src) == "Ada"

    def test_typed_param_wrong_type(self):
        src = "bladeFN f(x#int) +/\n    return x\nECB\nf(\"hello\")\n"
        with pytest.raises(AxonTypeError):
            run(src)

    def test_wrong_arg_count(self):
        src = "bladeFN f(x, y) +/\n    return x\nECB\nf(1)\n"
        with pytest.raises(AxonRuntimeError):
            run(src)

    def test_first_class_function(self):
        src = (
            "bladeFN apply(func, val) +/\n"
            "    return func(val)\n"
            "ECB\n"
            "bladeFN double(x) +/\n"
            "    return x * 2\n"
            "ECB\n"
            "apply(double, 5)\n"
        )
        assert run(src) == 10


class TestClosures:
    def test_basic_closure(self):
        src = (
            "bladeFN make_counter() +/\n"
            "    >> count = 0\n"
            "    bladeFN increment() +/\n"
            "        count = count + 1\n"
            "        return count\n"
            "    ECB\n"
            "    return increment\n"
            "ECB\n"
            ">> c = make_counter()\n"
            ">> a = c()\n"
            ">> b = c()\n"
            ">> d = c()\n"
            "d\n"
        )
        assert run(src) == 3

    def test_independent_closures(self):
        src = (
            "bladeFN make_adder(n) +/\n"
            "    bladeFN adder(x) +/\n"
            "        return x + n\n"
            "    ECB\n"
            "    return adder\n"
            "ECB\n"
            ">> add5 = make_adder(5)\n"
            ">> add10 = make_adder(10)\n"
            "add5(3) + add10(3)\n"
        )
        assert run(src) == 21

    def test_closure_captures_env_at_definition(self):
        src = (
            ">> x = 1\n"
            "bladeFN get_x() +/\n"
            "    return x\n"
            "ECB\n"
            "x = 99\n"
            "get_x()\n"
        )
        # x is set then mutated — closure should see the mutated value
        # because it captures the *environment object*, not a snapshot
        assert run(src) == 99


# ===========================================================================
# Phase 6.4 — bladeGRP class system
# ===========================================================================

class TestBladeGRP:
    def test_instance_creation(self):
        src = (
            "bladeGRP Dog +/\n"
            "    bladeFN init(blade, name#str) +/\n"
            "        blade.name = name\n"
            "    ECB\n"
            "ECB\n"
            ">> d = Dog(\"Rex\")\n"
            "d.name\n"
        )
        assert run(src) == "Rex"

    def test_method_call(self):
        src = (
            "bladeGRP Counter +/\n"
            "    bladeFN init(blade) +/\n"
            "        blade.count = 0\n"
            "    ECB\n"
            "    bladeFN inc(blade) +/\n"
            "        blade.count = blade.count + 1\n"
            "        return blade.count\n"
            "    ECB\n"
            "ECB\n"
            ">> c = Counter()\n"
            "c.inc()\n"
            "c.inc()\n"
            "c.inc()\n"
        )
        assert run(src) == 3

    def test_class_returns_instance(self):
        src = (
            "bladeGRP Foo +/\n"
            "    bladeFN init(blade) +/\n"
            "        blade.x = 42\n"
            "    ECB\n"
            "ECB\n"
            ">> f = Foo()\n"
        )
        _, env = run_env(src)
        assert isinstance(env.get("f"), AxonInstance)

    def test_method_returns_value(self):
        src = (
            "bladeGRP Calc +/\n"
            "    bladeFN square(blade, n#int) +/\n"
            "        return n * n\n"
            "    ECB\n"
            "ECB\n"
            ">> c = Calc()\n"
            "c.square(7)\n"
        )
        assert run(src) == 49

    def test_animal_example(self):
        src = (
            "bladeGRP Animal +/\n"
            "    bladeFN init(blade, name#str, sound#str) +/\n"
            "        blade.name = name\n"
            "        blade.sound = sound\n"
            "    ECB\n"
            "    bladeFN describe(blade) +/\n"
            "        return blade.name\n"
            "    ECB\n"
            "ECB\n"
            ">> dog = Animal(\"Rex\", \"woof\")\n"
            "dog.describe()\n"
        )
        assert run(src) == "Rex"


# ===========================================================================
# Phase 6.5 — Pipeline operator and built-ins
# ===========================================================================

class TestPipeline:
    def test_simple_pipeline(self):
        src = (
            "bladeFN double(x) +/\n    return x * 2\nECB\n"
            "5 |> double\n"
        )
        assert run(src) == 10

    def test_pipeline_with_args(self):
        src = (
            "bladeFN add(x, y) +/\n    return x + y\nECB\n"
            "5 |> add(3)\n"
        )
        assert run(src) == 8

    def test_chained_pipeline(self):
        src = (
            "bladeFN double(x) +/\n    return x * 2\nECB\n"
            "bladeFN inc(x) +/\n    return x + 1\nECB\n"
            "5 |> double |> inc\n"
        )
        assert run(src) == 11


class TestBuiltins:
    def test_write_does_not_crash(self, capsys):
        run('write("hello")\n')
        captured = capsys.readouterr()
        assert "hello" in captured.out

    def test_len_list(self):
        assert run("len([1, 2, 3])\n") == 3

    def test_len_string(self):
        assert run('len("hello")\n') == 5

    def test_len_dict(self):
        assert run("len({a: 1, b: 2})\n") == 2

    def test_type_int(self):
        assert run("type(42)\n") == "int"

    def test_type_str(self):
        assert run('type("hello")\n') == "str"

    def test_type_list(self):
        assert run("type([])\n") == "list"

    def test_type_null(self):
        assert run("type(null)\n") == "null"

    def test_range_single(self):
        assert run("range(5)\n") == [0, 1, 2, 3, 4]

    def test_range_two_args(self):
        assert run("range(2, 5)\n") == [2, 3, 4]

    def test_str_conversion(self):
        assert run("str(42)\n") == "42"

    def test_int_conversion(self):
        assert run('int("42")\n') == 42

    def test_float_conversion(self):
        assert run('float("3.14")\n') == pytest.approx(3.14)

    def test_bool_conversion(self):
        assert run("bool(0)\n") is False
        assert run("bool(1)\n") is True


# ===========================================================================
# Error handling (Phase 7.2)
# ===========================================================================

class TestTryCatch:
    def test_catches_division_by_zero(self):
        src = (
            ">> caught = false\n"
            "try +/\n"
            "    >> x = 1 / 0\n"
            "ECB\n"
            "catch e +/\n"
            "    caught = true\n"
            "ECB\n"
        )
        _, env = run_env(src)
        assert env.get("caught") is True

    def test_catch_error_dict(self):
        src = (
            ">> err_type = \"\"\n"
            "try +/\n"
            '    raise "oops"\n'
            "ECB\n"
            "catch e +/\n"
            '    err_type = e~"type"~\n'
            "ECB\n"
        )
        _, env = run_env(src)
        assert env.get("err_type") == "AxonRuntimeError"

    def test_raise_statement(self):
        with pytest.raises(AxonRuntimeError):
            run('raise "Something bad"\n')

    def test_raise_custom_message(self):
        src = (
            ">> msg = \"\"\n"
            "try +/\n"
            '    raise "Custom error"\n'
            "ECB\n"
            "catch e +/\n"
            '    msg = e~"message"~\n'
            "ECB\n"
        )
        _, env = run_env(src)
        assert env.get("msg") == "Custom error"

    def test_catch_name_error(self):
        src = (
            ">> caught = false\n"
            "try +/\n"
            "    undeclared_var\n"
            "ECB\n"
            "catch e +/\n"
            "    caught = true\n"
            "ECB\n"
        )
        _, env = run_env(src)
        assert env.get("caught") is True
