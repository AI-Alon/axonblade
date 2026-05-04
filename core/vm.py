"""
core/vm.py — AxonBlade stack-based bytecode virtual machine (V2 Phase 3.3).

Architecture
------------
  VM holds a globals dict (built-ins + top-level definitions).
  Each function call creates a CallFrame with:
    - code:           CodeObject being executed
    - ip:             instruction pointer
    - stack:          value stack (list, top = [-1])
    - locals:         dict for non-cell local variables
    - cells:          dict[name, Cell] for locals captured by inner fns
    - captured_cells: list[Cell] indexed by code.upvalue_names

Cell objects allow inner functions to share mutable bindings with their
enclosing scopes.

JUMP_IF_FALSE "or-pop" semantics
---------------------------------
  if TOS is falsy  → jump to target, TOS stays on stack
  if TOS is truthy → pop TOS, continue

JUMP_IF_TRUE is the dual (truthy → jump/keep, falsy → pop/continue).

This lets short-circuit AND/OR leave the value on the stack for the
caller, while if/while/for emit explicit POP instructions on the
falsy-branch target to clean up the condition.
"""

from __future__ import annotations

from typing import Any

from core.code_object import CodeObject
from core.errors import (
    AxonDivisionError, AxonError, AxonIndexError,
    AxonNameError, AxonRuntimeError, AxonTypeError,
)
from core.opcodes import Opcode
from core.runtime import (
    AxonBladeGRP, AxonFunction, AxonInstance, BoundMethod, Cell,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_truthy(value: object) -> bool:
    if value is None or value is False:
        return False
    return True


def _axon_str(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _maybe_int(v: object) -> object:
    if isinstance(v, float) and v == int(v):
        return int(v)
    return v


def _is_num(v: object) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


_ANSI_COLORS: dict[str, str] = {
    "black": "\033[30m", "red": "\033[31m", "green": "\033[32m",
    "yellow": "\033[33m", "blue": "\033[34m", "magenta": "\033[35m",
    "cyan": "\033[36m", "white": "\033[37m", "reset": "\033[0m",
}


# ---------------------------------------------------------------------------
# Call frame
# ---------------------------------------------------------------------------

class CallFrame:
    __slots__ = ("code", "ip", "stack", "locals", "cells", "captured_cells",
                 "handler_stack")

    def __init__(self, code: CodeObject,
                 captured_cells: list[Cell] | None = None) -> None:
        self.code = code
        self.ip = 0
        self.stack: list[Any] = []
        self.locals: dict[str, Any] = {}
        self.cells: dict[str, Cell] = {}
        self.captured_cells: list[Cell] = captured_cells or []
        self.handler_stack: list[tuple[int, int]] = []  # (handler_ip, stack_depth)

    def push(self, value: Any) -> None:
        self.stack.append(value)

    def pop(self) -> Any:
        return self.stack.pop()

    def peek(self) -> Any:
        return self.stack[-1]


# ---------------------------------------------------------------------------
# Dot-access helper (mirrors evaluator logic, now uses runtime types)
# ---------------------------------------------------------------------------

def _get_attr(obj: Any, attr: str, line: int = 0) -> Any:
    if isinstance(obj, AxonInstance):
        return obj.get_attr(attr)

    # Module namespace (Environment stored as namespace)
    from core.environment import Environment
    if isinstance(obj, Environment):
        try:
            return obj.get(attr)
        except AxonNameError:
            raise AxonNameError(f"Module has no attribute '{attr}'", line=line)

    # AxonGrid — delegate to Python attribute
    try:
        from grid.grid_object import AxonGrid  # type: ignore[import]
        if isinstance(obj, AxonGrid):
            method = getattr(obj, attr, None)
            if method is not None:
                return method
            raise AxonNameError(f"AxonGrid has no method '{attr}'", line=line)
    except ImportError:
        pass

    # List methods
    if isinstance(obj, list):
        _LIST_METHODS = {
            "append": lambda item: obj.append(item),
            "pop":    lambda *a: obj.pop(*[int(x) for x in a]) if a else obj.pop(),
            "insert": lambda i, item: obj.insert(int(i), item),
            "remove": lambda item: obj.remove(item),
            "reverse": lambda: obj.reverse(),
            "copy":   lambda: obj.copy(),
        }
        if attr in _LIST_METHODS:
            return _LIST_METHODS[attr]
        raise AxonTypeError(f"list has no method '{attr}'", line=line)

    # Dict methods
    if isinstance(obj, dict):
        _DICT_METHODS = {
            "keys":   lambda: list(obj.keys()),
            "values": lambda: list(obj.values()),
            "items":  lambda: [[k, v] for k, v in obj.items()],
            "get":    lambda key, default=None: obj.get(key, default),
        }
        if attr in _DICT_METHODS:
            return _DICT_METHODS[attr]
        raise AxonTypeError(f"dict has no method '{attr}'", line=line)

    # String dot-methods
    if isinstance(obj, str):
        _STR_METHODS = {
            "upper":       lambda: obj.upper(),
            "lower":       lambda: obj.lower(),
            "strip":       lambda: obj.strip(),
            "trim":        lambda: obj.strip(),
            "split":       lambda sep: obj.split(sep),
            "replace":     lambda old, new: obj.replace(old, new),
            "contains":    lambda sub: sub in obj,
            "starts_with": lambda prefix: obj.startswith(prefix),
            "ends_with":   lambda suffix: obj.endswith(suffix),
        }
        if attr in _STR_METHODS:
            return _STR_METHODS[attr]
        raise AxonTypeError(f"str has no method '{attr}'", line=line)

    raise AxonTypeError(
        f"Cannot access attribute '{attr}' on {type(obj).__name__}", line=line
    )


# ---------------------------------------------------------------------------
# VM
# ---------------------------------------------------------------------------

class VM:
    """
    Execute a compiled CodeObject.

    Usage::
        vm = VM(globals_dict)
        result = vm.run(code_object)
    """

    def __init__(self, globals_dict: dict) -> None:
        self.globals = globals_dict
        self._frame_stack: list[CallFrame] = []
        # Injected by the module system so IMPORT can call back
        self._module_loader: Any = None

    @property
    def _frame(self) -> CallFrame:
        return self._frame_stack[-1]

    # ------------------------------------------------------------------
    # Entry points
    # ------------------------------------------------------------------

    def run(self, code: CodeObject) -> Any:
        """Run a top-level CodeObject, sharing globals as top-level locals."""
        frame = CallFrame(code)
        frame.locals = self.globals          # top-level vars go into globals
        self._frame_stack.append(frame)
        try:
            return self._exec()
        finally:
            self._frame_stack.pop()

    def call(self, fn: AxonFunction, args: list) -> Any:
        """Call an AxonFunction with the given args, return its result."""
        self._push_fn_frame(fn, args)
        try:
            return self._exec()
        finally:
            self._frame_stack.pop()

    # ------------------------------------------------------------------
    # Main execution loop
    # ------------------------------------------------------------------

    def _exec(self) -> Any:  # noqa: C901
        frame = self._frame
        instrs = frame.code.instructions

        while True:
            if frame.ip >= len(instrs):
                return None

            instr = instrs[frame.ip]
            frame.ip += 1
            op = instr.opcode
            arg = instr.arg

            try:
                # ---- Stack basics ------------------------------------
                if op is Opcode.PUSH_CONST:
                    frame.push(frame.code.constants[arg])

                elif op is Opcode.PUSH_NULL:
                    frame.push(None)

                elif op is Opcode.PUSH_TRUE:
                    frame.push(True)

                elif op is Opcode.PUSH_FALSE:
                    frame.push(False)

                elif op is Opcode.POP:
                    frame.pop()

                # ---- Variables --------------------------------------
                elif op is Opcode.LOAD_VAR:
                    frame.push(self._load_var(frame, arg))

                elif op is Opcode.DEFINE_VAR:
                    val = frame.pop()
                    if arg in frame.code.cell_vars:
                        frame.cells[arg] = Cell(val)
                        frame.locals[arg] = val  # also expose via locals/globals for LOAD_VAR lookup
                    else:
                        frame.locals[arg] = val

                elif op is Opcode.STORE_VAR:
                    val = frame.pop()
                    self._store_var(frame, arg, val)

                # ---- Upvalues (cells) -------------------------------
                elif op is Opcode.LOAD_DEREF:
                    cell = self._find_cell(frame, arg)
                    frame.push(cell.value)

                elif op is Opcode.STORE_DEREF:
                    val = frame.pop()
                    cell = self._find_cell(frame, arg)
                    cell.value = val

                # ---- Arithmetic -------------------------------------
                elif op is Opcode.ADD:
                    r, l = frame.pop(), frame.pop()
                    if isinstance(l, str) and isinstance(r, str):
                        frame.push(l + r)
                    elif _is_num(l) and _is_num(r):
                        frame.push(_maybe_int(l + r))
                    else:
                        raise AxonTypeError(
                            f"Cannot use '+' with {type(l).__name__} and {type(r).__name__}"
                        )

                elif op is Opcode.SUB:
                    r, l = frame.pop(), frame.pop()
                    self._require_num(l, r, "-")
                    frame.push(_maybe_int(l - r))

                elif op is Opcode.MUL:
                    r, l = frame.pop(), frame.pop()
                    self._require_num(l, r, "*")
                    frame.push(_maybe_int(l * r))

                elif op is Opcode.DIV:
                    r, l = frame.pop(), frame.pop()
                    self._require_num(l, r, "/")
                    if r == 0:
                        raise AxonDivisionError("Division by zero")
                    frame.push(_maybe_int(l / r))

                elif op is Opcode.MOD:
                    r, l = frame.pop(), frame.pop()
                    self._require_num(l, r, "%")
                    if r == 0:
                        raise AxonDivisionError("Modulo by zero")
                    frame.push(_maybe_int(l % r))

                elif op is Opcode.POW:
                    r, l = frame.pop(), frame.pop()
                    self._require_num(l, r, "**")
                    frame.push(_maybe_int(l ** r))

                elif op is Opcode.NEG:
                    v = frame.pop()
                    if not _is_num(v):
                        raise AxonTypeError(f"Cannot negate {type(v).__name__}")
                    frame.push(_maybe_int(-v))

                # ---- Comparison -------------------------------------
                elif op is Opcode.EQ:
                    r, l = frame.pop(), frame.pop()
                    frame.push(l == r)

                elif op is Opcode.NEQ:
                    r, l = frame.pop(), frame.pop()
                    frame.push(l != r)

                elif op is Opcode.LT:
                    r, l = frame.pop(), frame.pop()
                    self._require_ord(l, r, "<")
                    frame.push(l < r)

                elif op is Opcode.GT:
                    r, l = frame.pop(), frame.pop()
                    self._require_ord(l, r, ">")
                    frame.push(l > r)

                elif op is Opcode.LTE:
                    r, l = frame.pop(), frame.pop()
                    self._require_ord(l, r, "<=")
                    frame.push(l <= r)

                elif op is Opcode.GTE:
                    r, l = frame.pop(), frame.pop()
                    self._require_ord(l, r, ">=")
                    frame.push(l >= r)

                # ---- Logic ------------------------------------------
                elif op is Opcode.AND:
                    r, l = frame.pop(), frame.pop()
                    frame.push(r if _is_truthy(l) else l)

                elif op is Opcode.OR:
                    r, l = frame.pop(), frame.pop()
                    frame.push(l if _is_truthy(l) else r)

                elif op is Opcode.NOT:
                    frame.push(not _is_truthy(frame.pop()))

                # ---- Jumps ------------------------------------------
                elif op is Opcode.JUMP:
                    frame.ip = arg

                elif op is Opcode.JUMP_IF_FALSE:
                    # "or-pop": if TOS falsy → jump (TOS stays); else pop TOS
                    val = frame.peek()
                    if not _is_truthy(val):
                        frame.ip = arg
                    else:
                        frame.pop()

                elif op is Opcode.JUMP_IF_TRUE:
                    val = frame.peek()
                    if _is_truthy(val):
                        frame.ip = arg
                    else:
                        frame.pop()

                # ---- Collections ------------------------------------
                elif op is Opcode.MAKE_LIST:
                    items = [frame.pop() for _ in range(arg)]
                    items.reverse()
                    frame.push(items)

                elif op is Opcode.MAKE_DICT:
                    pairs = [(frame.pop(), frame.pop()) for _ in range(arg)]
                    pairs.reverse()
                    # pairs are (val, key) due to stack order; swap
                    frame.push({k: v for v, k in pairs})

                elif op is Opcode.GET_INDEX:
                    idx = frame.pop()
                    obj = frame.pop()
                    try:
                        frame.push(obj[idx])
                    except (KeyError, IndexError) as e:
                        raise AxonIndexError(str(e))
                    except TypeError as e:
                        raise AxonTypeError(str(e))

                elif op is Opcode.SET_INDEX:
                    val = frame.pop()
                    idx = frame.pop()
                    obj = frame.pop()
                    try:
                        obj[idx] = val
                    except (KeyError, IndexError) as e:
                        raise AxonIndexError(str(e))
                    except TypeError as e:
                        raise AxonTypeError(str(e))

                elif op is Opcode.GET_SLICE:
                    end = frame.pop()
                    start = frame.pop()
                    obj = frame.pop()
                    try:
                        frame.push(obj[start:end])
                    except TypeError as e:
                        raise AxonTypeError(str(e))

                # ---- Attributes -------------------------------------
                elif op is Opcode.GET_ATTR:
                    obj = frame.pop()
                    frame.push(_get_attr(obj, arg))

                elif op is Opcode.SET_ATTR:
                    val = frame.pop()
                    obj = frame.pop()
                    if isinstance(obj, AxonInstance):
                        obj.set_field(arg, val)
                    else:
                        raise AxonTypeError(
                            f"Cannot set attribute on {type(obj).__name__}"
                        )

                # ---- Functions --------------------------------------
                elif op is Opcode.MAKE_FN:
                    fn_code: CodeObject = frame.pop()
                    captured: list[Cell] = []
                    for uv_name in fn_code.upvalue_names:
                        captured.append(self._find_cell_by_name(frame, uv_name))
                    frame.push(AxonFunction(fn_code, captured))

                elif op is Opcode.CALL:
                    n_args = arg
                    args_list = [frame.pop() for _ in range(n_args)]
                    args_list.reverse()
                    callee = frame.pop()
                    result = self._call(callee, args_list)
                    frame.push(result)

                elif op is Opcode.RETURN:
                    return frame.pop()

                # ---- Classes ----------------------------------------
                elif op is Opcode.MAKE_CLASS:
                    class_name, method_names = arg
                    fns = [frame.pop() for _ in range(len(method_names))]
                    fns.reverse()
                    methods = {name: fn for name, fn in zip(method_names, fns)}
                    frame.push(AxonBladeGRP(class_name, methods))

                # ---- Strings ----------------------------------------
                elif op is Opcode.BUILD_FSTRING:
                    parts = [frame.pop() for _ in range(arg)]
                    parts.reverse()
                    frame.push("".join(_axon_str(p) for p in parts))

                # ---- Exceptions -------------------------------------
                elif op is Opcode.SETUP_TRY:
                    frame.handler_stack.append((arg, len(frame.stack)))

                elif op is Opcode.POP_TRY:
                    frame.handler_stack.pop()

                elif op is Opcode.RAISE:
                    msg = frame.pop()
                    raise AxonRuntimeError(str(msg))

                # ---- Modules ----------------------------------------
                elif op is Opcode.IMPORT:
                    if self._module_loader is None:
                        raise AxonRuntimeError(
                            "Module loader not configured — cannot use uselib"
                        )
                    module_ns = self._module_loader(arg)
                    frame.push(module_ns)

                else:
                    raise AxonRuntimeError(f"Unknown opcode: {op}")

            except AxonError as exc:
                if frame.handler_stack:
                    handler_ip, stack_depth = frame.handler_stack.pop()
                    # Unwind the value stack to where it was before try
                    del frame.stack[stack_depth:]
                    frame.push(exc.to_axon_dict())
                    frame.ip = handler_ip
                else:
                    raise

    # ------------------------------------------------------------------
    # Variable lookup helpers
    # ------------------------------------------------------------------

    def _load_var(self, frame: CallFrame, name: str) -> Any:
        if name in frame.cells:
            return frame.cells[name].value
        if name in frame.locals:
            return frame.locals[name]
        if name in self.globals:
            return self.globals[name]
        raise AxonNameError(f"Undefined variable '{name}'")

    def _store_var(self, frame: CallFrame, name: str, value: Any) -> None:
        if name in frame.cells:
            frame.cells[name].value = value
        elif name in frame.locals:
            frame.locals[name] = value
        elif name in self.globals:
            self.globals[name] = value
        else:
            raise AxonNameError(f"Undefined variable '{name}'")

    def _find_cell(self, frame: CallFrame, upvalue_idx: int) -> Cell:
        """Return the Cell for the given upvalue index."""
        uv_name = frame.code.upvalue_names[upvalue_idx]
        # Check captured cells first (from enclosing function)
        if upvalue_idx < len(frame.captured_cells):
            return frame.captured_cells[upvalue_idx]
        raise AxonRuntimeError(f"Missing captured cell for '{uv_name}'")

    def _find_cell_by_name(self, frame: CallFrame, name: str) -> Cell:
        """
        Find the Cell for *name* in the current frame (needed by MAKE_FN).
        Checks frame.cells (local cell vars) then frame.captured_cells
        (upvalues from outer scopes matched by code.upvalue_names).
        """
        if name in frame.cells:
            return frame.cells[name]
        for i, uv_name in enumerate(frame.code.upvalue_names):
            if uv_name == name and i < len(frame.captured_cells):
                return frame.captured_cells[i]
        # Variable is a regular local — box it as a Cell now
        if name in frame.locals:
            cell = Cell(frame.locals.pop(name))
            frame.cells[name] = cell
            return cell
        if name in self.globals:
            cell = Cell(self.globals[name])
            frame.cells[name] = cell
            return cell
        raise AxonRuntimeError(f"Cannot capture '{name}': variable not found")

    # ------------------------------------------------------------------
    # Call dispatch
    # ------------------------------------------------------------------

    def _call(self, callee: Any, args: list) -> Any:
        if isinstance(callee, AxonFunction):
            self._push_fn_frame(callee, args)
            try:
                return self._exec()
            finally:
                self._frame_stack.pop()

        if isinstance(callee, BoundMethod):
            return self._call(callee.fn, [callee.instance] + args)

        if isinstance(callee, AxonBladeGRP):
            instance = AxonInstance(callee)
            if "init" in callee.methods:
                self._call(callee.methods["init"], [instance] + args)
            return instance

        if callable(callee):
            try:
                return callee(*args)
            except AxonError:
                raise
            except Exception as e:
                raise AxonRuntimeError(str(e))

        raise AxonTypeError(f"'{type(callee).__name__}' is not callable")

    def _push_fn_frame(self, fn: AxonFunction, args: list) -> None:
        code = fn.code
        if len(args) != len(code.param_names):
            raise AxonRuntimeError(
                f"'{code.name}' expects {len(code.param_names)} argument(s), "
                f"got {len(args)}"
            )
        # Type-check parameters
        for param_name, param_type, arg_val in zip(
            code.param_names, code.param_types, args
        ):
            self._check_type(arg_val, param_type, param_name)

        frame = CallFrame(code, fn.captured_cells)
        for param_name, arg_val in zip(code.param_names, args):
            if param_name in code.cell_vars:
                frame.cells[param_name] = Cell(arg_val)
                frame.locals[param_name] = arg_val
            else:
                frame.locals[param_name] = arg_val

        self._frame_stack.append(frame)

    # ------------------------------------------------------------------
    # Type checking
    # ------------------------------------------------------------------

    def _check_type(self, value: Any, annotation: str | None,
                    param_name: str) -> None:
        if annotation is None or annotation == "any":
            return
        type_map: dict = {
            "str":   str,
            "int":   int,
            "bool":  bool,
            "list":  list,
            "dict":  dict,
            "fn":    AxonFunction,
            "float": (float, int),
        }
        try:
            from grid.grid_object import AxonGrid  # type: ignore[import]
            type_map["grid"] = AxonGrid
        except ImportError:
            pass
        expected = type_map.get(annotation)
        if expected is None:
            return
        if not isinstance(value, expected):
            raise AxonTypeError(
                f"Parameter '{param_name}' expected {annotation}, "
                f"got {type(value).__name__}"
            )

    # ------------------------------------------------------------------
    # Arithmetic helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _require_num(l: Any, r: Any, op: str) -> None:
        if not _is_num(l) or not _is_num(r):
            raise AxonTypeError(
                f"Cannot use '{op}' with {type(l).__name__} and {type(r).__name__}"
            )

    @staticmethod
    def _require_ord(l: Any, r: Any, op: str) -> None:
        if not isinstance(l, (int, float)) or not isinstance(r, (int, float)):
            raise AxonTypeError(
                f"Cannot compare {type(l).__name__} and {type(r).__name__} with '{op}'"
            )
