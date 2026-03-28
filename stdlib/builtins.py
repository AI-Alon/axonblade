"""
stdlib/builtins.py — Python-backed built-in functions (Week 6, Phase 6.5).

Registers all built-in functions per ProjectPlan.md §8.1:
  write, len, type, range, input, str, int, float, bool, grid

Also registers __builtin_* hooks called by stdlib .axb files (Week 7, §8.2–8.3):
  __builtin_sqrt, __builtin_floor, __builtin_ceil,
  __builtin_upper, __builtin_lower, __builtin_split,
  __builtin_join, __builtin_strip, __builtin_contains, __builtin_replace

build_global_env() returns a pre-loaded Environment ready for use.
"""

from __future__ import annotations

import math as _math

from core.environment import Environment
from core.errors import AxonTypeError, AxonRuntimeError


# ---------------------------------------------------------------------------
# §8.1 — Core built-in functions
# ---------------------------------------------------------------------------

def _builtin_write(value: object) -> None:
    """write(value) — print to stdout with newline."""
    if value is None:
        print("null")
    elif isinstance(value, bool):
        print("true" if value else "false")
    else:
        print(value)


def _builtin_len(collection: object) -> int:
    """len(collection) — length of list, dict, or string."""
    if isinstance(collection, (list, dict, str)):
        return len(collection)
    raise AxonTypeError(f"len() does not support {type(collection).__name__}")


def _builtin_type(value: object) -> str:
    """type(value) — returns type name as string."""
    from core.evaluator import AxonFunction, AxonBladeGRP, AxonInstance
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    if isinstance(value, AxonFunction):
        return "fn"
    if isinstance(value, AxonBladeGRP):
        return "bladeGRP"
    if isinstance(value, AxonInstance):
        return value.klass.name
    try:
        from grid.grid_object import AxonGrid
        if isinstance(value, AxonGrid):
            return "grid"
    except ImportError:
        pass
    return type(value).__name__


def _builtin_range(*args: object) -> list:
    """range(n) or range(start, end) — returns a list of integers."""
    if len(args) == 1:
        n = args[0]
        if not isinstance(n, int):
            raise AxonTypeError("range() argument must be int")
        return list(range(n))
    if len(args) == 2:
        start, end = args
        if not isinstance(start, int) or not isinstance(end, int):
            raise AxonTypeError("range() arguments must be int")
        return list(range(start, end))
    raise AxonRuntimeError("range() takes 1 or 2 arguments")


def _builtin_input(prompt: object = "") -> str:
    """input(prompt) — reads a line from stdin."""
    return input(str(prompt))


def _builtin_str(value: object) -> str:
    """str(value) — convert to string."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _builtin_int(value: object) -> int:
    """int(value) — convert to integer."""
    try:
        if isinstance(value, bool):
            raise AxonTypeError("Cannot convert bool to int")
        return int(value)
    except (ValueError, TypeError) as e:
        raise AxonTypeError(f"Cannot convert to int: {e}")


def _builtin_float(value: object) -> float:
    """float(value) — convert to float."""
    try:
        if isinstance(value, bool):
            raise AxonTypeError("Cannot convert bool to float")
        return float(value)
    except (ValueError, TypeError) as e:
        raise AxonTypeError(f"Cannot convert to float: {e}")


def _builtin_bool(value: object) -> bool:
    """bool(value) — convert to boolean."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, (str, list, dict)):
        return len(value) > 0
    return True


def _builtin_wait_key() -> None:
    """wait_key() — block until the user presses any key."""
    import sys
    if sys.platform == "win32":
        import msvcrt  # type: ignore[import]
        msvcrt.getch()
    else:
        import tty, termios, select
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _builtin_grid(cols: object, rows: object) -> object:
    """grid(cols, rows) — create a new AxonGrid."""
    from grid.grid_object import AxonGrid  # lazy import to avoid circular dep
    if not isinstance(cols, int) or not isinstance(rows, int):
        raise AxonTypeError("grid() requires int arguments")
    return AxonGrid(cols, rows)


# ---------------------------------------------------------------------------
# §8.2 — __builtin_* hooks for math.axb
# ---------------------------------------------------------------------------

def _builtin_sqrt(n: object) -> float:
    if not isinstance(n, (int, float)):
        raise AxonTypeError("sqrt() requires a number")
    return _math.sqrt(n)


def _builtin_floor(n: object) -> int:
    if not isinstance(n, (int, float)):
        raise AxonTypeError("floor() requires a number")
    return _math.floor(n)


def _builtin_ceil(n: object) -> int:
    if not isinstance(n, (int, float)):
        raise AxonTypeError("ceil() requires a number")
    return _math.ceil(n)


# ---------------------------------------------------------------------------
# §8.3 — __builtin_* hooks for string.axb
# ---------------------------------------------------------------------------

def _builtin_upper(s: object) -> str:
    if not isinstance(s, str):
        raise AxonTypeError("upper() requires a string")
    return s.upper()


def _builtin_lower(s: object) -> str:
    if not isinstance(s, str):
        raise AxonTypeError("lower() requires a string")
    return s.lower()


def _builtin_split(s: object, delim: object) -> list:
    if not isinstance(s, str) or not isinstance(delim, str):
        raise AxonTypeError("split() requires string arguments")
    return s.split(delim)


def _builtin_join(parts: object, delim: object) -> str:
    if not isinstance(parts, list) or not isinstance(delim, str):
        raise AxonTypeError("join() requires list and string arguments")
    return delim.join(str(p) for p in parts)


def _builtin_strip(s: object) -> str:
    if not isinstance(s, str):
        raise AxonTypeError("strip() requires a string")
    return s.strip()


def _builtin_contains(s: object, sub: object) -> bool:
    if not isinstance(s, str) or not isinstance(sub, str):
        raise AxonTypeError("contains() requires string arguments")
    return sub in s


def _builtin_replace(s: object, old: object, new: object) -> str:
    if not isinstance(s, str) or not isinstance(old, str) or not isinstance(new, str):
        raise AxonTypeError("replace() requires string arguments")
    return s.replace(old, new)


# ---------------------------------------------------------------------------
# build_global_env — entry point used by evaluator and REPL
# ---------------------------------------------------------------------------

def build_global_env() -> Environment:
    """
    Create and return a fresh global Environment pre-loaded with all
    built-in functions and __builtin_* hooks.
    """
    env = Environment()

    # §8.1 — core built-ins
    env.define("write",  _builtin_write)
    env.define("len",    _builtin_len)
    env.define("type",   _builtin_type)
    env.define("range",  _builtin_range)
    env.define("input",  _builtin_input)
    env.define("str",    _builtin_str)
    env.define("int",    _builtin_int)
    env.define("float",  _builtin_float)
    env.define("bool",   _builtin_bool)
    env.define("grid",     _builtin_grid)
    env.define("wait_key", _builtin_wait_key)

    # §8.2 — math hooks
    env.define("__builtin_sqrt",  _builtin_sqrt)
    env.define("__builtin_floor", _builtin_floor)
    env.define("__builtin_ceil",  _builtin_ceil)

    # §8.3 — string hooks
    env.define("__builtin_upper",    _builtin_upper)
    env.define("__builtin_lower",    _builtin_lower)
    env.define("__builtin_split",    _builtin_split)
    env.define("__builtin_join",     _builtin_join)
    env.define("__builtin_strip",    _builtin_strip)
    env.define("__builtin_contains", _builtin_contains)
    env.define("__builtin_replace",  _builtin_replace)

    return env
