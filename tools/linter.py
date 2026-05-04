"""
tools/linter.py — AxonBlade static linter (V2 Phase 2.2).

Diagnostics emitted:
  [error]   undefined variable used before declaration in scope
  [error]   function called with wrong number of arguments (at known call sites)
  [warning] variable declared with >> but never read
  [warning] unreachable statements after return in a function body
  [warning] variable shadows a name from an outer scope

Output format:
  file.axb:12:5: [error] undefined variable 'x'

Exit codes:
  0  — no errors, no warnings
  1  — at least one error
  2  — at least one warning, no errors
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

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


# ---------------------------------------------------------------------------
# Diagnostic
# ---------------------------------------------------------------------------

@dataclass
class Diagnostic:
    level: str      # "error" or "warning"
    message: str
    file: str
    line: int
    col: int

    def format(self) -> str:
        return f"{self.file}:{self.line}:{self.col}: [{self.level}] {self.message}"


# ---------------------------------------------------------------------------
# Scope — tracks declarations and reads within one lexical scope
# ---------------------------------------------------------------------------

@dataclass
class _VarInfo:
    line: int
    col: int
    read: bool = False


class _Scope:
    def __init__(self, parent: Optional["_Scope"] = None) -> None:
        self.parent = parent
        self.vars: dict[str, _VarInfo] = {}

    def declare(self, name: str, line: int, col: int) -> bool:
        """Return True if name shadows an outer scope variable."""
        self.vars[name] = _VarInfo(line=line, col=col)
        return self.parent is not None and self._outer_has(name)

    def _outer_has(self, name: str) -> bool:
        s = self.parent
        while s is not None:
            if name in s.vars:
                return True
            s = s.parent
        return False

    def mark_read(self, name: str) -> bool:
        """Mark name as read in the nearest scope that owns it. Return True if found."""
        s: Optional[_Scope] = self
        while s is not None:
            if name in s.vars:
                s.vars[name].read = True
                return True
            s = s.parent
        return False

    def is_declared(self, name: str) -> bool:
        s: Optional[_Scope] = self
        while s is not None:
            if name in s.vars:
                return True
            s = s.parent
        return False

    def unread_local(self) -> list[tuple[str, _VarInfo]]:
        return [(n, v) for n, v in self.vars.items() if not v.read]


# ---------------------------------------------------------------------------
# Linter
# ---------------------------------------------------------------------------

# Built-in names that are always in scope
_BUILTINS: set[str] = {
    "write", "len", "type", "range", "input", "str", "int", "float",
    "bool", "grid", "wait_key", "null", "true", "false",
    "test", "assert_eq", "assert_true", "assert_raises",
    # __builtin_* hooks — exposed to .axb code via stdlib modules
}


class Linter:
    def __init__(self, filename: str = "<unknown>") -> None:
        self.filename = filename
        self.diagnostics: list[Diagnostic] = []
        self._fn_arities: dict[str, int] = {}   # name → param count for known fns

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def lint(self, program: Program) -> list[Diagnostic]:
        self.diagnostics = []
        self._fn_arities = {}
        global_scope = _Scope()
        # First pass: collect all top-level function names and arities
        for stmt in program.statements:
            if isinstance(stmt, FnDef):
                self._fn_arities[stmt.name] = len(stmt.params)
                global_scope.declare(stmt.name, stmt.line, stmt.col)
                global_scope.vars[stmt.name].read = True  # fn defs are "used"
            elif isinstance(stmt, BladeGRPDef):
                global_scope.declare(stmt.name, stmt.line, stmt.col)
                global_scope.vars[stmt.name].read = True
        # Second pass: full walk
        for stmt in program.statements:
            self._lint_stmt(stmt, global_scope)
        self._check_unused(global_scope)
        return self.diagnostics

    # ------------------------------------------------------------------
    # Statement walk
    # ------------------------------------------------------------------

    def _lint_stmt(self, node: object, scope: _Scope) -> bool:
        """Walk a statement. Returns True if it is a guaranteed return (for unreachable detection)."""

        if isinstance(node, AssignStmt):
            # RHS first (value may reference outer scope)
            self._lint_expr(node.value, scope)
            # Determine LHS
            if isinstance(node.name, (DotAccess, IndexAccess)):
                self._lint_expr(node.name, scope)
            else:
                name: str = node.name  # type: ignore[assignment]
                if node.is_declaration:
                    # Re-binding a name via >> means any known function arity is gone
                    self._fn_arities.pop(name, None)
                    shadows = scope.declare(name, node.line, node.col)
                    if shadows:
                        self._warn(
                            f"variable '{name}' shadows an outer scope variable",
                            node.line, node.col,
                        )
                else:
                    if not scope.is_declared(name) and name not in _BUILTINS:
                        self._error(
                            f"undefined variable '{name}'",
                            node.line, node.col,
                        )
                    else:
                        scope.mark_read(name)
            return False

        if isinstance(node, FnDef):
            self._lint_fn_def(node, scope)
            return False

        if isinstance(node, BladeGRPDef):
            for method in node.methods:
                self._lint_fn_def(method, scope)
            return False

        if isinstance(node, ReturnStmt):
            self._lint_expr(node.value, scope)
            return True  # guaranteed return

        if isinstance(node, RaiseStmt):
            self._lint_expr(node.message, scope)
            return True

        if isinstance(node, IfStmt):
            self._lint_expr(node.condition, scope)
            self._lint_body(node.then_body, scope)
            for cond, body in node.elif_clauses:
                self._lint_expr(cond, scope)
                self._lint_body(body, scope)
            if node.else_body:
                self._lint_body(node.else_body, scope)
            return False

        if isinstance(node, WhileStmt):
            self._lint_expr(node.condition, scope)
            self._lint_body(node.body, scope)
            return False

        if isinstance(node, ForStmt):
            self._lint_expr(node.iterable, scope)
            loop_scope = _Scope(parent=scope)
            shadows = loop_scope.declare(node.var_name, node.line, node.col)
            if shadows:
                self._warn(
                    f"loop variable '{node.var_name}' shadows an outer scope variable",
                    node.line, node.col,
                )
            loop_scope.vars[node.var_name].read = True  # assume used in body
            self._lint_body(node.body, loop_scope)
            return False

        if isinstance(node, TryCatch):
            self._lint_body(node.try_body, scope)
            catch_scope = _Scope(parent=scope)
            catch_scope.declare(node.catch_var, node.line, node.col)
            catch_scope.vars[node.catch_var].read = True  # assume used in catch body
            self._lint_body(node.catch_body, catch_scope)
            return False

        if isinstance(node, UselibStmt):
            # Bind module name in scope
            bind = node.module_name.split("/")[-1]
            if bind.endswith(".axb"):
                bind = bind[:-4]
            scope.declare(bind, node.line, node.col)
            scope.vars[bind].read = True
            return False

        # Bare expression (e.g., a call)
        self._lint_expr(node, scope)
        return False

    def _lint_body(self, stmts: list, scope: _Scope) -> None:
        """Lint a statement list; warn on unreachable code after a return."""
        body_scope = _Scope(parent=scope)
        returned = False
        for i, stmt in enumerate(stmts):
            if returned:
                self._warn(
                    "unreachable statement after return",
                    getattr(stmt, "line", 0),
                    getattr(stmt, "col", 0),
                )
                break
            returned = self._lint_stmt(stmt, body_scope)
        self._check_unused(body_scope)

    def _lint_fn_def(self, node: FnDef, outer: _Scope) -> None:
        # Register the function name in the enclosing scope (mirrors evaluator)
        if node.name not in ("<lambda>", ""):
            outer.declare(node.name, node.line, node.col)
            outer.vars[node.name].read = True  # function definitions are "used"
        self._fn_arities[node.name] = len(node.params)
        fn_scope = _Scope(parent=outer)
        for param in node.params:
            shadows = fn_scope.declare(param.name, node.line, node.col)
            fn_scope.vars[param.name].read = True  # params are considered used
            if shadows:
                self._warn(
                    f"parameter '{param.name}' shadows an outer scope variable",
                    node.line, node.col,
                )
        self._lint_body(node.body, fn_scope)

    # ------------------------------------------------------------------
    # Expression walk
    # ------------------------------------------------------------------

    def _lint_expr(self, node: object, scope: _Scope,
                   _pipeline_rhs: bool = False) -> None:
        if node is None:
            return

        if isinstance(node, (NumberLiteral, StringLiteral, BoolLiteral,
                              NullLiteral, ColorLiteral)):
            return

        if isinstance(node, FStringLiteral):
            for part in node.parts:
                if not isinstance(part, str):
                    self._lint_expr(part, scope)
            return

        if isinstance(node, Identifier):
            name = node.name
            if name.startswith("__builtin_"):
                return  # stdlib internal hooks
            if name in _BUILTINS:
                return
            if not scope.mark_read(name):
                self._error(
                    f"undefined variable '{name}'",
                    node.line, node.col,
                )
            return

        if isinstance(node, BinaryOp):
            self._lint_expr(node.left, scope)
            self._lint_expr(node.right, scope)
            return

        if isinstance(node, UnaryOp):
            self._lint_expr(node.operand, scope)
            return

        if isinstance(node, CallExpr):
            self._lint_expr(node.callee, scope)
            for arg in node.args:
                self._lint_expr(arg, scope)
            # Arity check: skip for pipeline targets (the pipeline prepends one arg)
            if not _pipeline_rhs and isinstance(node.callee, Identifier):
                name = node.callee.name
                if name in self._fn_arities:
                    expected = self._fn_arities[name]
                    got = len(node.args)
                    if got != expected:
                        self._error(
                            f"'{name}' called with {got} argument(s), expected {expected}",
                            node.line, node.col,
                        )
            return

        if isinstance(node, DotAccess):
            self._lint_expr(node.obj, scope)
            return

        if isinstance(node, IndexAccess):
            self._lint_expr(node.obj, scope)
            self._lint_expr(node.index, scope)
            return

        if isinstance(node, SliceAccess):
            self._lint_expr(node.obj, scope)
            if node.start is not None:
                self._lint_expr(node.start, scope)
            if node.end is not None:
                self._lint_expr(node.end, scope)
            return

        if isinstance(node, ListLiteral):
            for elem in node.elements:
                self._lint_expr(elem, scope)
            return

        if isinstance(node, DictLiteral):
            for k, v in node.pairs:
                self._lint_expr(k, scope)
                self._lint_expr(v, scope)
            return

        if isinstance(node, PipelineExpr):
            self._lint_expr(node.left, scope)
            # Right side of pipeline: one implicit arg is prepended, skip arity check
            self._lint_expr(node.right, scope, _pipeline_rhs=True)
            return

        if isinstance(node, FnDef):
            # Lambda / inline function
            self._lint_fn_def(node, scope)
            return

    # ------------------------------------------------------------------
    # Unused variable check
    # ------------------------------------------------------------------

    def _check_unused(self, scope: _Scope) -> None:
        for name, info in scope.unread_local():
            if name.startswith("_") or name.startswith("__builtin_"):
                continue
            self._warn(
                f"variable '{name}' is declared but never read",
                info.line, info.col,
            )

    # ------------------------------------------------------------------
    # Diagnostic helpers
    # ------------------------------------------------------------------

    def _error(self, message: str, line: int, col: int) -> None:
        self.diagnostics.append(Diagnostic("error", message, self.filename, line, col))

    def _warn(self, message: str, line: int, col: int) -> None:
        self.diagnostics.append(Diagnostic("warning", message, self.filename, line, col))


# ---------------------------------------------------------------------------
# Module-level helper
# ---------------------------------------------------------------------------

def lint_file(path: str) -> tuple[list[Diagnostic], int]:
    """
    Parse and lint a file. Returns (diagnostics, exit_code).
    exit_code: 0 = clean, 1 = errors, 2 = warnings only.
    """
    from pathlib import Path
    from core.parser import parse_source, ParseError

    source = Path(path).read_text(encoding="utf-8")
    try:
        prog = parse_source(source)
    except (ParseError, SyntaxError) as e:
        d = Diagnostic("error", f"parse error: {e}", path, 0, 0)
        return [d], 1

    linter = Linter(filename=path)
    diags = linter.lint(prog)

    has_errors = any(d.level == "error" for d in diags)
    has_warnings = any(d.level == "warning" for d in diags)

    if has_errors:
        return diags, 1
    if has_warnings:
        return diags, 2
    return diags, 0
