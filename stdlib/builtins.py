"""
stdlib/builtins.py — Python-backed built-in functions (Week 6, Phase 6.5).

Registers all built-in functions per ProjectPlan.md §8.1:
  write, len, type, range, input, str, int, float, bool, grid

Also registers __builtin_* hooks called by stdlib .axb files (Week 7, §8.2–8.3):
  __builtin_sqrt, __builtin_floor, __builtin_ceil,
  __builtin_upper, __builtin_lower, __builtin_split,
  __builtin_join, __builtin_strip, __builtin_contains, __builtin_replace

V2.0 hooks for io, json, http, regex modules (Phase 1.1–1.4):
  __builtin_io_*, __builtin_json_*, __builtin_http_*, __builtin_regex_*

build_global_env() returns a pre-loaded Environment ready for use.
"""

from __future__ import annotations

import datetime as _dt
import json as _json
import math as _math
import os as _os
import random as _random
import re as _re
import time as _time
from pathlib import Path as _Path

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
    from core.runtime import AxonFunction, AxonBladeGRP, AxonInstance
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


def _builtin_starts_with(s: object, prefix: object) -> bool:
    if not isinstance(s, str) or not isinstance(prefix, str):
        raise AxonTypeError("starts_with() requires string arguments")
    return s.startswith(prefix)


def _builtin_ends_with(s: object, suffix: object) -> bool:
    if not isinstance(s, str) or not isinstance(suffix, str):
        raise AxonTypeError("ends_with() requires string arguments")
    return s.endswith(suffix)


def _builtin_trim(s: object) -> str:
    if not isinstance(s, str):
        raise AxonTypeError("trim() requires a string")
    return s.strip()


# ---------------------------------------------------------------------------
# §V2 Phase 1.1 — __builtin_* hooks for io.axb
# ---------------------------------------------------------------------------

def _builtin_io_read(path: object) -> str:
    if not isinstance(path, str):
        raise AxonTypeError("io.read() requires a string path")
    try:
        return _Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        raise AxonRuntimeError(f"io.read(): file not found: {path}")
    except OSError as e:
        raise AxonRuntimeError(f"io.read(): {e}")


def _builtin_io_write(path: object, content: object) -> None:
    if not isinstance(path, str) or not isinstance(content, str):
        raise AxonTypeError("io.write() requires string arguments")
    try:
        _Path(path).write_text(content, encoding="utf-8")
    except OSError as e:
        raise AxonRuntimeError(f"io.write(): {e}")


def _builtin_io_append(path: object, content: object) -> None:
    if not isinstance(path, str) or not isinstance(content, str):
        raise AxonTypeError("io.append() requires string arguments")
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(content)
    except OSError as e:
        raise AxonRuntimeError(f"io.append(): {e}")


def _builtin_io_exists(path: object) -> bool:
    if not isinstance(path, str):
        raise AxonTypeError("io.exists() requires a string path")
    return _Path(path).exists()


def _builtin_io_delete(path: object) -> None:
    if not isinstance(path, str):
        raise AxonTypeError("io.delete() requires a string path")
    try:
        _Path(path).unlink()
    except FileNotFoundError:
        raise AxonRuntimeError(f"io.delete(): file not found: {path}")
    except OSError as e:
        raise AxonRuntimeError(f"io.delete(): {e}")


def _builtin_io_list(path: object) -> list:
    if not isinstance(path, str):
        raise AxonTypeError("io.list() requires a string path")
    try:
        return [entry.name for entry in _Path(path).iterdir()]
    except NotADirectoryError:
        raise AxonRuntimeError(f"io.list(): not a directory: {path}")
    except FileNotFoundError:
        raise AxonRuntimeError(f"io.list(): path not found: {path}")
    except OSError as e:
        raise AxonRuntimeError(f"io.list(): {e}")


# ---------------------------------------------------------------------------
# §V2 Phase 1.2 — __builtin_* hooks for json.axb
# ---------------------------------------------------------------------------

def _builtin_json_parse(s: object) -> object:
    if not isinstance(s, str):
        raise AxonTypeError("json.parse() requires a string")
    try:
        return _json.loads(s)
    except _json.JSONDecodeError as e:
        raise AxonRuntimeError(f"json.parse(): invalid JSON: {e}")


def _builtin_json_stringify(value: object) -> str:
    try:
        return _json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        raise AxonRuntimeError(f"json.stringify(): cannot serialize value: {e}")


# ---------------------------------------------------------------------------
# §V2 Phase 1.3 — __builtin_* hooks for http.axb
# ---------------------------------------------------------------------------

def _builtin_http_get(url: object) -> dict:
    if not isinstance(url, str):
        raise AxonTypeError("http.get() requires a string URL")
    import urllib.request as _req
    import urllib.error as _err
    try:
        with _req.urlopen(_req.Request(url), timeout=10) as resp:
            return {
                "status": resp.status,
                "body": resp.read().decode("utf-8"),
                "headers": dict(resp.headers),
            }
    except _err.HTTPError as e:
        body = e.read().decode("utf-8") if hasattr(e, "read") else ""
        return {"status": e.code, "body": body, "headers": {}}
    except Exception as e:
        raise AxonRuntimeError(f"http.get(): {e}")


def _builtin_http_post(url: object, data: object) -> dict:
    if not isinstance(url, str):
        raise AxonTypeError("http.post() requires a string URL")
    import urllib.request as _req
    import urllib.error as _err
    try:
        payload = _json.dumps(data).encode("utf-8")
        req = _req.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with _req.urlopen(req, timeout=10) as resp:
            return {
                "status": resp.status,
                "body": resp.read().decode("utf-8"),
                "headers": dict(resp.headers),
            }
    except _err.HTTPError as e:
        body = e.read().decode("utf-8") if hasattr(e, "read") else ""
        return {"status": e.code, "body": body, "headers": {}}
    except Exception as e:
        raise AxonRuntimeError(f"http.post(): {e}")


def _builtin_http_put(url: object, data: object) -> dict:
    if not isinstance(url, str):
        raise AxonTypeError("http.put() requires a string URL")
    import urllib.request as _req
    import urllib.error as _err
    try:
        payload = _json.dumps(data).encode("utf-8")
        req = _req.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="PUT",
        )
        with _req.urlopen(req, timeout=10) as resp:
            return {
                "status": resp.status,
                "body": resp.read().decode("utf-8"),
                "headers": dict(resp.headers),
            }
    except _err.HTTPError as e:
        body = e.read().decode("utf-8") if hasattr(e, "read") else ""
        return {"status": e.code, "body": body, "headers": {}}
    except Exception as e:
        raise AxonRuntimeError(f"http.put(): {e}")


def _builtin_http_delete(url: object) -> dict:
    if not isinstance(url, str):
        raise AxonTypeError("http.delete() requires a string URL")
    import urllib.request as _req
    import urllib.error as _err
    try:
        req = _req.Request(url, method="DELETE")
        with _req.urlopen(req, timeout=10) as resp:
            return {
                "status": resp.status,
                "body": resp.read().decode("utf-8"),
                "headers": dict(resp.headers),
            }
    except _err.HTTPError as e:
        body = e.read().decode("utf-8") if hasattr(e, "read") else ""
        return {"status": e.code, "body": body, "headers": {}}
    except Exception as e:
        raise AxonRuntimeError(f"http.delete(): {e}")


# ---------------------------------------------------------------------------
# §V2 Phase 1.4 — __builtin_* hooks for regex.axb
# ---------------------------------------------------------------------------

def _builtin_regex_match(pattern: object, s: object) -> bool:
    if not isinstance(pattern, str) or not isinstance(s, str):
        raise AxonTypeError("regex.match() requires string arguments")
    try:
        return bool(_re.search(pattern, s))
    except _re.error as e:
        raise AxonRuntimeError(f"regex.match(): invalid pattern: {e}")


def _builtin_regex_find(pattern: object, s: object) -> object:
    if not isinstance(pattern, str) or not isinstance(s, str):
        raise AxonTypeError("regex.find() requires string arguments")
    try:
        m = _re.search(pattern, s)
        return m.group(0) if m else None
    except _re.error as e:
        raise AxonRuntimeError(f"regex.find(): invalid pattern: {e}")


def _builtin_regex_find_all(pattern: object, s: object) -> list:
    if not isinstance(pattern, str) or not isinstance(s, str):
        raise AxonTypeError("regex.find_all() requires string arguments")
    try:
        return _re.findall(pattern, s)
    except _re.error as e:
        raise AxonRuntimeError(f"regex.find_all(): invalid pattern: {e}")


def _builtin_regex_replace(pattern: object, s: object, repl: object) -> str:
    if not isinstance(pattern, str) or not isinstance(s, str) or not isinstance(repl, str):
        raise AxonTypeError("regex.replace() requires string arguments")
    try:
        return _re.sub(pattern, repl, s)
    except _re.error as e:
        raise AxonRuntimeError(f"regex.replace(): invalid pattern: {e}")


# ---------------------------------------------------------------------------
# §V2 Phase 1.5 — __builtin_* hooks for datetime.axb
# ---------------------------------------------------------------------------

def _builtin_datetime_now() -> str:
    return _dt.datetime.now().isoformat()


def _builtin_datetime_format(iso_str: object, fmt: object) -> str:
    if not isinstance(iso_str, str) or not isinstance(fmt, str):
        raise AxonTypeError("datetime.format() requires string arguments")
    try:
        return _dt.datetime.fromisoformat(iso_str).strftime(fmt)
    except ValueError as e:
        raise AxonRuntimeError(f"datetime.format(): {e}")


def _builtin_datetime_parse(s: object, fmt: object) -> str:
    if not isinstance(s, str) or not isinstance(fmt, str):
        raise AxonTypeError("datetime.parse() requires string arguments")
    try:
        return _dt.datetime.strptime(s, fmt).isoformat()
    except ValueError as e:
        raise AxonRuntimeError(f"datetime.parse(): {e}")


def _builtin_datetime_timestamp() -> float:
    return _time.time()


def _builtin_datetime_diff_seconds(iso_a: object, iso_b: object) -> float:
    if not isinstance(iso_a, str) or not isinstance(iso_b, str):
        raise AxonTypeError("datetime.diff_seconds() requires string arguments")
    try:
        a = _dt.datetime.fromisoformat(iso_a)
        b = _dt.datetime.fromisoformat(iso_b)
        return (b - a).total_seconds()
    except ValueError as e:
        raise AxonRuntimeError(f"datetime.diff_seconds(): {e}")


# ---------------------------------------------------------------------------
# §V2 Phase 1.6 — __builtin_* hooks for random.axb
# ---------------------------------------------------------------------------

def _builtin_random_int(lo: object, hi: object) -> int:
    if not isinstance(lo, int) or not isinstance(hi, int):
        raise AxonTypeError("random.int() requires int arguments")
    if lo > hi:
        raise AxonRuntimeError("random.int(): min must be <= max")
    return _random.randint(lo, hi)


def _builtin_random_float() -> float:
    return _random.random()


def _builtin_random_choice(lst: object) -> object:
    if not isinstance(lst, list):
        raise AxonTypeError("random.choice() requires a list")
    if not lst:
        raise AxonRuntimeError("random.choice(): list is empty")
    return _random.choice(lst)


def _builtin_random_shuffle(lst: object) -> list:
    if not isinstance(lst, list):
        raise AxonTypeError("random.shuffle() requires a list")
    result = lst.copy()
    _random.shuffle(result)
    return result


def _builtin_random_seed(n: object) -> None:
    if not isinstance(n, int):
        raise AxonTypeError("random.seed() requires an int")
    _random.seed(n)


# ---------------------------------------------------------------------------
# build_global_env — entry point used by VM and REPL
# ---------------------------------------------------------------------------

def build_global_dict() -> dict:
    """
    Create and return a fresh dict pre-loaded with all built-in functions
    and __builtin_* hooks.  Used by the VM (which expects a plain dict).
    """
    env: dict = {}
    _fill_env(env)
    return env


def build_global_env() -> Environment:
    """
    Create and return a fresh global Environment pre-loaded with all
    built-in functions.  Used by the module loader for namespace wrapping.
    """
    env = Environment()
    _fill_env(env.store)
    return env


def _fill_env(env: dict) -> None:
    """Populate *env* (a plain dict) with all built-in names."""

    # §8.1 — core built-ins
    env["write"]    = _builtin_write
    env["len"]      = _builtin_len
    env["type"]     = _builtin_type
    env["range"]    = _builtin_range
    env["input"]    = _builtin_input
    env["str"]      = _builtin_str
    env["int"]      = _builtin_int
    env["float"]    = _builtin_float
    env["bool"]     = _builtin_bool
    env["grid"]     = _builtin_grid
    env["wait_key"] = _builtin_wait_key

    # §8.2 — math hooks
    env["__builtin_sqrt"]  = _builtin_sqrt
    env["__builtin_floor"] = _builtin_floor
    env["__builtin_ceil"]  = _builtin_ceil

    # §8.3 — string hooks
    env["__builtin_upper"]       = _builtin_upper
    env["__builtin_lower"]       = _builtin_lower
    env["__builtin_split"]       = _builtin_split
    env["__builtin_join"]        = _builtin_join
    env["__builtin_strip"]       = _builtin_strip
    env["__builtin_contains"]    = _builtin_contains
    env["__builtin_replace"]     = _builtin_replace
    env["__builtin_starts_with"] = _builtin_starts_with
    env["__builtin_ends_with"]   = _builtin_ends_with
    env["__builtin_trim"]        = _builtin_trim

    # V2 Phase 1.1 — io hooks
    env["__builtin_io_read"]   = _builtin_io_read
    env["__builtin_io_write"]  = _builtin_io_write
    env["__builtin_io_append"] = _builtin_io_append
    env["__builtin_io_exists"] = _builtin_io_exists
    env["__builtin_io_delete"] = _builtin_io_delete
    env["__builtin_io_list"]   = _builtin_io_list

    # V2 Phase 1.2 — json hooks
    env["__builtin_json_parse"]     = _builtin_json_parse
    env["__builtin_json_stringify"] = _builtin_json_stringify

    # V2 Phase 1.3 — http hooks
    env["__builtin_http_get"]    = _builtin_http_get
    env["__builtin_http_post"]   = _builtin_http_post
    env["__builtin_http_put"]    = _builtin_http_put
    env["__builtin_http_delete"] = _builtin_http_delete

    # V2 Phase 1.4 — regex hooks
    env["__builtin_regex_match"]    = _builtin_regex_match
    env["__builtin_regex_find"]     = _builtin_regex_find
    env["__builtin_regex_find_all"] = _builtin_regex_find_all
    env["__builtin_regex_replace"]  = _builtin_regex_replace

    # V2 Phase 1.5 — datetime hooks
    env["__builtin_datetime_now"]          = _builtin_datetime_now
    env["__builtin_datetime_format"]       = _builtin_datetime_format
    env["__builtin_datetime_parse"]        = _builtin_datetime_parse
    env["__builtin_datetime_timestamp"]    = _builtin_datetime_timestamp
    env["__builtin_datetime_diff_seconds"] = _builtin_datetime_diff_seconds

    # V2 Phase 1.6 — random hooks
    env["__builtin_random_int"]     = _builtin_random_int
    env["__builtin_random_float"]   = _builtin_random_float
    env["__builtin_random_choice"]  = _builtin_random_choice
    env["__builtin_random_shuffle"] = _builtin_random_shuffle
    env["__builtin_random_seed"]    = _builtin_random_seed
