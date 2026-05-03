"""
core/evaluator.py — AxonBlade tree-walk evaluator (Weeks 5–6, Phases 5.1-6.5).

Week 5 (Phases 5.1–5.5):
  5.1  Environment chain (see core/environment.py)
  5.2  Literal evaluation, Identifier lookup
  5.3  BinaryOp with type checks, UnaryOp
  5.4  Collections, AssignStmt, IfStmt, WhileStmt, ForStmt
  5.5  FStringLiteral interpolation

Week 6 (Phases 6.1–6.5):
  6.1  AxonFunction + ReturnException + FnDef evaluation
  6.2  CallExpr with type checking and closure env
  6.3  Closures (captured at definition time)
  6.4  AxonBladeGRP, AxonInstance, BoundMethod + DotAccess on instances
  6.5  PipelineExpr rewriting + built-ins integration

Runtime types live here:
  AxonFunction, AxonBladeGRP, AxonInstance, BoundMethod
"""

from __future__ import annotations

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
)
from core.environment import Environment
from core.errors import (
    AxonDivisionError,
    AxonError,
    AxonIndexError,
    AxonNameError,
    AxonRuntimeError,
    AxonTypeError,
)

# ---------------------------------------------------------------------------
# §10.2 — ANSI foreground color map (used by ColorLiteral eval)
# ---------------------------------------------------------------------------

ANSI_FG_COLORS: dict[str, str] = {
    "black":   "\033[30m",
    "red":     "\033[31m",
    "green":   "\033[32m",
    "yellow":  "\033[33m",
    "blue":    "\033[34m",
    "magenta": "\033[35m",
    "cyan":    "\033[36m",
    "white":   "\033[37m",
    "reset":   "\033[0m",
}

# ---------------------------------------------------------------------------
# Runtime types  (§6.3–6.5)
# ---------------------------------------------------------------------------


class AxonFunction:
    """Represents a callable AxonBlade function value (§6.3)."""

    def __init__(self, name: str, params: list[Param],
                 body: list, closure_env: Environment) -> None:
        self.name = name
        self.params = params
        self.body = body
        self.closure_env = closure_env  # captured at definition time

    def __repr__(self) -> str:
        return f"<bladeFN {self.name}>"


class AxonBladeGRP:
    """Represents a bladeGRP class (§6.5)."""

    def __init__(self, name: str, methods: dict) -> None:
        self.name = name
        self.methods = methods  # dict[str, AxonFunction]

    def __repr__(self) -> str:
        return f"<bladeGRP {self.name}>"


class AxonInstance:
    """Represents an instance of a bladeGRP (§6.5)."""

    def __init__(self, klass: AxonBladeGRP) -> None:
        self.klass = klass
        self.fields: dict = {}

    def get(self, name: str) -> object:
        if name in self.fields:
            return self.fields[name]
        if name in self.klass.methods:
            return BoundMethod(self, self.klass.methods[name])
        raise AxonNameError(f"No attribute '{name}' on {self.klass.name} instance")

    def set_field(self, name: str, value: object) -> None:
        self.fields[name] = value

    def __repr__(self) -> str:
        return f"<{self.klass.name} instance>"


class BoundMethod:
    """A method bound to an instance (§6.5)."""

    def __init__(self, instance: AxonInstance, fn: AxonFunction) -> None:
        self.instance = instance
        self.fn = fn

    def __repr__(self) -> str:
        return f"<bound method {self.fn.name}>"


# ---------------------------------------------------------------------------
# Return / control-flow exception  (§6.4)
# ---------------------------------------------------------------------------


class ReturnException(Exception):
    """Raised by return statements to unwind the call stack."""

    def __init__(self, value: object) -> None:
        self.value = value


# ---------------------------------------------------------------------------
# Type checking helper  (§7.2)
# ---------------------------------------------------------------------------


def check_type(value: object, annotation: str | None,
               param_name: str, line: int) -> None:
    """Enforce a parameter type annotation at call time."""
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
    # Grid type — lazy import so the evaluator works before grid/ is implemented
    try:
        from grid.grid_object import AxonGrid  # type: ignore[import]
        type_map["grid"] = AxonGrid
    except ImportError:
        pass  # grid not yet implemented; skip grid annotation checks
    expected = type_map.get(annotation)
    if expected is None:
        return  # unknown annotation — skip
    if not isinstance(value, expected):
        got = type(value).__name__
        raise AxonTypeError(
            f"Parameter '{param_name}' expected {annotation}, got {got}",
            line=line,
        )


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------


class Evaluator:
    """
    Tree-walk evaluator for AxonBlade.

    Usage:
        from core.evaluator import Evaluator
        from stdlib.builtins import build_global_env
        ev = Evaluator()
        result = ev.eval(ast_node, build_global_env())
    """

    def __init__(self) -> None:
        # Reference to the module loader — injected to avoid circular imports
        self._module_loader = None

    # ------------------------------------------------------------------
    # Main dispatch
    # ------------------------------------------------------------------

    def eval(self, node: object, env: Environment) -> object:
        """Dispatch to the appropriate eval method for *node*."""

        # --- Literals ---
        if isinstance(node, NumberLiteral):
            v = node.value
            return int(v) if isinstance(v, float) and v == int(v) else v

        if isinstance(node, StringLiteral):
            return node.value

        if isinstance(node, BoolLiteral):
            return node.value

        if isinstance(node, NullLiteral):
            return None

        if isinstance(node, ColorLiteral):
            return ANSI_FG_COLORS[node.name]

        if isinstance(node, FStringLiteral):
            return self._eval_fstring(node, env)

        # --- Collections ---
        if isinstance(node, ListLiteral):
            return [self.eval(e, env) for e in node.elements]

        if isinstance(node, DictLiteral):
            return {self.eval(k, env): self.eval(v, env) for k, v in node.pairs}

        # --- Identifier ---
        if isinstance(node, Identifier):
            return env.get(node.name)

        # --- Operators ---
        if isinstance(node, BinaryOp):
            return self._eval_binary(node, env)

        if isinstance(node, UnaryOp):
            return self._eval_unary(node, env)

        # --- Access ---
        if isinstance(node, DotAccess):
            return self._eval_dot_access(node, env)

        if isinstance(node, IndexAccess):
            return self._eval_index_access(node, env)

        if isinstance(node, SliceAccess):
            return self._eval_slice_access(node, env)

        # --- Calls and pipeline ---
        if isinstance(node, CallExpr):
            return self._eval_call(node, env)

        if isinstance(node, PipelineExpr):
            return self._eval_pipeline(node, env)

        # --- Statements ---
        if isinstance(node, AssignStmt):
            return self._eval_assign(node, env)

        if isinstance(node, FnDef):
            return self._eval_fn_def(node, env)

        if isinstance(node, BladeGRPDef):
            return self._eval_bladegrp_def(node, env)

        if isinstance(node, ReturnStmt):
            raise ReturnException(self.eval(node.value, env))

        if isinstance(node, RaiseStmt):
            msg = self.eval(node.message, env)
            raise AxonRuntimeError(str(msg), line=node.line)

        if isinstance(node, IfStmt):
            return self._eval_if(node, env)

        if isinstance(node, WhileStmt):
            return self._eval_while(node, env)

        if isinstance(node, ForStmt):
            return self._eval_for(node, env)

        if isinstance(node, TryCatch):
            return self._eval_try_catch(node, env)

        if isinstance(node, UselibStmt):
            return self._eval_uselib(node, env)

        if isinstance(node, Program):
            return self._eval_program(node, env)

        raise AxonRuntimeError(
            f"Unknown AST node type: {type(node).__name__}", line=0
        )

    # ------------------------------------------------------------------
    # Program
    # ------------------------------------------------------------------

    def _eval_program(self, node: Program, env: Environment) -> object:
        result: object = None
        for stmt in node.statements:
            result = self.eval(stmt, env)
        return result

    def eval_body(self, stmts: list, env: Environment) -> object:
        """Evaluate a list of statements, returning the last value."""
        result: object = None
        for stmt in stmts:
            result = self.eval(stmt, env)
        return result

    # ------------------------------------------------------------------
    # 5.5 — F-string interpolation (§6.7)
    # ------------------------------------------------------------------

    def _eval_fstring(self, node: FStringLiteral, env: Environment) -> str:
        parts: list[str] = []
        for part in node.parts:
            if isinstance(part, str):
                parts.append(part)
            else:
                parts.append(self._axon_str(self.eval(part, env)))
        return "".join(parts)

    # ------------------------------------------------------------------
    # 5.3 — BinaryOp and UnaryOp  (§7.3)
    # ------------------------------------------------------------------

    def _eval_binary(self, node: BinaryOp, env: Environment) -> object:
        left = self.eval(node.left, env)
        op = node.op

        # Short-circuit logical operators
        if op == "-a":
            if not self._is_truthy(left):
                return left
            return self.eval(node.right, env)
        if op == "-o":
            if self._is_truthy(left):
                return left
            return self.eval(node.right, env)

        right = self.eval(node.right, env)

        def _is_num(v: object) -> bool:
            return isinstance(v, (int, float)) and not isinstance(v, bool)

        # Arithmetic
        if op == "+":
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            if _is_num(left) and _is_num(right):
                result = left + right
                return int(result) if isinstance(result, float) and result == int(result) else result
            raise AxonTypeError(
                f"Cannot use '+' with {type(left).__name__} and {type(right).__name__}",
                line=node.line,
            )
        if op == "-":
            self._require_numeric(left, right, "-", node.line)
            return self._maybe_int(left - right)  # type: ignore[operator]
        if op == "*":
            self._require_numeric(left, right, "*", node.line)
            return self._maybe_int(left * right)  # type: ignore[operator]
        if op == "/":
            self._require_numeric(left, right, "/", node.line)
            if right == 0:
                raise AxonDivisionError("Division by zero", line=node.line)
            result = left / right  # type: ignore[operator]
            return self._maybe_int(result)
        if op == "%":
            self._require_numeric(left, right, "%", node.line)
            if right == 0:
                raise AxonDivisionError("Modulo by zero", line=node.line)
            return self._maybe_int(left % right)  # type: ignore[operator]
        if op == "**":
            self._require_numeric(left, right, "**", node.line)
            return self._maybe_int(left ** right)  # type: ignore[operator]

        # Comparisons
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
        if op in ("<", ">", "<=", ">="):
            if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
                raise AxonTypeError(
                    f"Cannot compare {type(left).__name__} and {type(right).__name__} with '{op}'",
                    line=node.line,
                )
            if op == "<":  return left < right
            if op == ">":  return left > right
            if op == "<=": return left <= right
            if op == ">=": return left >= right

        raise AxonRuntimeError(f"Unknown binary operator '{op}'", line=node.line)

    def _eval_unary(self, node: UnaryOp, env: Environment) -> object:
        val = self.eval(node.operand, env)
        if node.op == "-":
            if not isinstance(val, (int, float)):
                raise AxonTypeError(
                    f"Cannot negate {type(val).__name__}", line=node.line
                )
            return self._maybe_int(-val)
        if node.op == "-n":
            return not self._is_truthy(val)
        raise AxonRuntimeError(f"Unknown unary operator '{node.op}'", line=node.line)

    # ------------------------------------------------------------------
    # 5.4 — Collections, AssignStmt, control flow
    # ------------------------------------------------------------------

    def _eval_dot_access(self, node: DotAccess, env: Environment) -> object:
        obj = self.eval(node.obj, env)
        attr = node.attr

        if isinstance(obj, AxonInstance):
            return obj.get(attr)

        # Module namespace (Environment stored as a namespace)
        if isinstance(obj, Environment):
            try:
                return obj.get(attr)
            except AxonNameError:
                raise AxonNameError(
                    f"Module has no attribute '{attr}'", line=node.line
                )

        # AxonGrid — delegate to Python attribute
        try:
            from grid.grid_object import AxonGrid  # type: ignore[import]
            if isinstance(obj, AxonGrid):
                method = getattr(obj, attr, None)
                if method is not None:
                    return method
                raise AxonNameError(
                    f"AxonGrid has no method '{attr}'", line=node.line
                )
        except ImportError:
            pass

        # List methods
        if isinstance(obj, list):
            _LIST_METHODS = {
                "append": lambda item: obj.append(item),
                "pop": lambda *args: obj.pop(*[int(a) for a in args]) if args else obj.pop(),
                "insert": lambda i, item: obj.insert(int(i), item),
                "remove": lambda item: obj.remove(item),
                "reverse": lambda: obj.reverse(),
                "copy": lambda: obj.copy(),
            }
            if attr in _LIST_METHODS:
                return _LIST_METHODS[attr]
            raise AxonTypeError(
                f"list has no method '{attr}'", line=node.line
            )

        # Dict methods
        if isinstance(obj, dict):
            _DICT_METHODS = {
                "keys": lambda: list(obj.keys()),
                "values": lambda: list(obj.values()),
                "items": lambda: [[k, v] for k, v in obj.items()],
                "get": lambda key, default=None: obj.get(key, default),
            }
            if attr in _DICT_METHODS:
                return _DICT_METHODS[attr]
            raise AxonTypeError(
                f"dict has no method '{attr}'", line=node.line
            )

        # String dot-methods (Phase 1.7)
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
            raise AxonTypeError(
                f"str has no method '{attr}'", line=node.line
            )

        raise AxonTypeError(
            f"Cannot access attribute '{attr}' on {type(obj).__name__}",
            line=node.line,
        )

    def _eval_index_access(self, node: IndexAccess, env: Environment) -> object:
        obj = self.eval(node.obj, env)
        idx = self.eval(node.index, env)
        try:
            return obj[idx]
        except (KeyError, IndexError) as e:
            raise AxonIndexError(str(e), line=node.line)
        except TypeError as e:
            raise AxonTypeError(str(e), line=node.line)

    def _eval_slice_access(self, node: SliceAccess, env: Environment) -> object:
        obj = self.eval(node.obj, env)
        start = self.eval(node.start, env) if node.start is not None else None
        end = self.eval(node.end, env) if node.end is not None else None
        try:
            return obj[start:end]
        except TypeError as e:
            raise AxonTypeError(str(e), line=node.line)

    def _eval_assign(self, node: AssignStmt, env: Environment) -> None:
        value = self.eval(node.value, env)

        # Subscript assignment: obj~key~ = val
        if isinstance(node.name, IndexAccess):
            obj = self.eval(node.name.obj, env)
            idx = self.eval(node.name.index, env)
            try:
                obj[idx] = value
            except (KeyError, IndexError) as e:
                raise AxonIndexError(str(e), line=node.line)
            return

        # DotAccess assignment: self.field = val
        if isinstance(node.name, DotAccess):
            obj = self.eval(node.name.obj, env)
            attr = node.name.attr
            if isinstance(obj, AxonInstance):
                obj.set_field(attr, value)
            else:
                raise AxonTypeError(
                    f"Cannot set attribute on {type(obj).__name__}", line=node.line
                )
            return

        # Plain name assignment
        name: str = node.name  # type: ignore[assignment]
        if node.is_declaration:
            env.define(name, value)
        else:
            env.set(name, value)

    def _eval_if(self, node: IfStmt, env: Environment) -> object:
        if self._is_truthy(self.eval(node.condition, env)):
            return self.eval_body(node.then_body, env)
        for elif_cond, elif_body in node.elif_clauses:
            if self._is_truthy(self.eval(elif_cond, env)):
                return self.eval_body(elif_body, env)
        if node.else_body is not None:
            return self.eval_body(node.else_body, env)
        return None

    def _eval_while(self, node: WhileStmt, env: Environment) -> None:
        while self._is_truthy(self.eval(node.condition, env)):
            self.eval_body(node.body, env)

    def _eval_for(self, node: ForStmt, env: Environment) -> None:
        iterable = self.eval(node.iterable, env)
        if not hasattr(iterable, "__iter__"):
            raise AxonTypeError(
                f"Cannot iterate over {type(iterable).__name__}", line=node.line
            )
        for item in iterable:
            child_env = env.child()
            child_env.define(node.var_name, item)
            self.eval_body(node.body, child_env)

    # ------------------------------------------------------------------
    # 6.1–6.3 — Functions and closures
    # ------------------------------------------------------------------

    def _eval_fn_def(self, node: FnDef, env: Environment) -> AxonFunction:
        fn = AxonFunction(
            name=node.name,
            params=node.params,
            body=node.body,
            closure_env=env,  # capture current env at definition time
        )
        if node.name != "<lambda>":
            env.define(node.name, fn)
        return fn

    def _call_function(self, fn: AxonFunction, args: list,
                       call_line: int = 0) -> object:
        """Create a child env from closure_env, bind args, eval body."""
        if len(args) != len(fn.params):
            raise AxonRuntimeError(
                f"'{fn.name}' expects {len(fn.params)} argument(s), "
                f"got {len(args)}",
                line=call_line,
            )
        call_env = fn.closure_env.child()
        for param, arg in zip(fn.params, args):
            check_type(arg, param.type_ann, param.name, call_line)
            call_env.define(param.name, arg)
        try:
            self.eval_body(fn.body, call_env)
            return None
        except ReturnException as ret:
            return ret.value

    # ------------------------------------------------------------------
    # 6.4 — bladeGRP system
    # ------------------------------------------------------------------

    def _eval_bladegrp_def(self, node: BladeGRPDef,
                           env: Environment) -> AxonBladeGRP:
        methods: dict = {}
        for fn_node in node.methods:
            fn = AxonFunction(
                name=fn_node.name,
                params=fn_node.params,
                body=fn_node.body,
                closure_env=env,
            )
            methods[fn_node.name] = fn
        klass = AxonBladeGRP(name=node.name, methods=methods)
        env.define(node.name, klass)
        return klass

    # ------------------------------------------------------------------
    # 6.2 — CallExpr dispatch
    # ------------------------------------------------------------------

    def _eval_call(self, node: CallExpr, env: Environment) -> object:
        callee = self.eval(node.callee, env)
        args = [self.eval(a, env) for a in node.args]

        # AxonFunction (user-defined)
        if isinstance(callee, AxonFunction):
            return self._call_function(callee, args, node.line)

        # BoundMethod — prepend self as first arg
        if isinstance(callee, BoundMethod):
            return self._call_function(callee.fn, [callee.instance] + args, node.line)

        # AxonBladeGRP instantiation
        if isinstance(callee, AxonBladeGRP):
            instance = AxonInstance(callee)
            if "init" in callee.methods:
                self._call_function(callee.methods["init"], [instance] + args, node.line)
            return instance

        # Python callable (built-ins)
        if callable(callee):
            try:
                return callee(*args)
            except AxonError:
                raise
            except Exception as e:
                raise AxonRuntimeError(str(e), line=node.line)

        # Python bound method (AxonGrid methods)
        raise AxonTypeError(
            f"'{type(callee).__name__}' is not callable", line=node.line
        )

    # ------------------------------------------------------------------
    # 6.5 — Pipeline operator
    # ------------------------------------------------------------------

    def _eval_pipeline(self, node: PipelineExpr, env: Environment) -> object:
        """a |> f(b)  →  f(a, b)  (left inserted as first argument)."""
        left_val = self.eval(node.left, env)
        right = node.right
        if not isinstance(right, CallExpr):
            # bare identifier: a |> f  →  f(a)
            callee = self.eval(right, env)
            if isinstance(callee, AxonFunction):
                return self._call_function(callee, [left_val], node.line)
            if callable(callee):
                try:
                    return callee(left_val)
                except AxonError:
                    raise
                except Exception as e:
                    raise AxonRuntimeError(str(e), line=node.line)
            raise AxonTypeError(
                f"Pipeline target '{type(callee).__name__}' is not callable",
                line=node.line,
            )
        # Evaluate existing args, then prepend left_val
        extra_args = [self.eval(a, env) for a in right.args]
        callee = self.eval(right.callee, env)
        all_args = [left_val] + extra_args
        if isinstance(callee, AxonFunction):
            return self._call_function(callee, all_args, node.line)
        if isinstance(callee, BoundMethod):
            return self._call_function(callee.fn, [callee.instance] + all_args, node.line)
        if callable(callee):
            try:
                return callee(*all_args)
            except AxonError:
                raise
            except Exception as e:
                raise AxonRuntimeError(str(e), line=node.line)
        raise AxonTypeError(
            f"Pipeline target '{type(callee).__name__}' is not callable",
            line=node.line,
        )

    # ------------------------------------------------------------------
    # 7.2 — TryCatch
    # ------------------------------------------------------------------

    def _eval_try_catch(self, node: TryCatch, env: Environment) -> object:
        try:
            return self.eval_body(node.try_body, env)
        except AxonError as e:
            catch_env = env.child()
            catch_env.define(node.catch_var, e.to_axon_dict())
            return self.eval_body(node.catch_body, catch_env)

    # ------------------------------------------------------------------
    # 7.3 — uselib
    # ------------------------------------------------------------------

    def _eval_uselib(self, node: UselibStmt, env: Environment) -> None:
        if self._module_loader is None:
            raise AxonRuntimeError(
                "Module loader not configured — cannot use uselib", line=node.line
            )
        module_env = self._module_loader(node.module_name, node.line)
        # Bind the module under a clean name:
        #   "math"        → "math"
        #   "./mymodule"  → "mymodule"
        raw = node.module_name
        bind_name = raw.split("/")[-1]
        if bind_name.endswith(".axb"):
            bind_name = bind_name[:-4]
        env.define(bind_name, module_env)

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_truthy(value: object) -> bool:
        """AxonBlade truthiness: None and false are falsy; everything else truthy."""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        return True

    @staticmethod
    def _maybe_int(value: object) -> object:
        """Convert float to int when the result is a whole number."""
        if isinstance(value, float) and value == int(value):
            return int(value)
        return value

    @staticmethod
    def _require_numeric(left: object, right: object,
                         op: str, line: int) -> None:
        # bool is a subclass of int in Python but AxonBlade forbids bool arithmetic
        def _is_num(v: object) -> bool:
            return isinstance(v, (int, float)) and not isinstance(v, bool)
        if not _is_num(left) or not _is_num(right):
            raise AxonTypeError(
                f"Cannot use '{op}' with {type(left).__name__} and {type(right).__name__}",
                line=line,
            )

    @staticmethod
    def _axon_str(value: object) -> str:
        """Convert a value to its AxonBlade string representation."""
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)
