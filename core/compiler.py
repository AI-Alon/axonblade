"""
core/compiler.py — AxonBlade AST → bytecode compiler (V2 Phase 3.2).

Walks the AST produced by core/parser.py and emits a CodeObject
(core/code_object.py) suitable for execution by core/vm.py.

Design decisions:
  - Upvalue analysis: free variables in function bodies that resolve to
    an enclosing function scope become upvalues (LOAD_DEREF/STORE_DEREF).
  - Top-level variables resolve as globals (LOAD_VAR with VM global fallback).
  - JUMP_IF_FALSE "or-pop" semantics:
      if TOS falsy  → jump, TOS stays on stack
      if TOS truthy → pop TOS, continue
  - JUMP_IF_TRUE is the dual.
  - If/while/for falsy branches emit an explicit POP to clean up condition.
"""

from __future__ import annotations

from typing import Any

from core.ast_nodes import (
    AssignStmt, BladeGRPDef, BinaryOp, BoolLiteral, CallExpr, ColorLiteral,
    DictLiteral, DotAccess, FnDef, ForStmt, FStringLiteral, Identifier,
    IfStmt, IndexAccess, ListLiteral, NullLiteral, NumberLiteral,
    PipelineExpr, Program, RaiseStmt, ReturnStmt, SliceAccess, StringLiteral,
    TryCatch, UnaryOp, UselibStmt, WhileStmt,
)
from core.code_object import CodeObject
from core.opcodes import Opcode

_ANSI_COLORS: dict[str, str] = {
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
# Scope bookkeeping
# ---------------------------------------------------------------------------

class _Scope:
    def __init__(self, parent: "_Scope | None" = None,
                 is_top_level: bool = False) -> None:
        self.parent = parent
        self.is_top_level = is_top_level
        self.locals_set: set[str] = set()
        self.cell_vars: set[str] = set()
        self.upvalues: list[str] = []


# ---------------------------------------------------------------------------
# Free-variable analysis (single-level — does not descend into inner FnDefs)
# ---------------------------------------------------------------------------

def _collect_free_vars(body: list, outer_defined: set[str]) -> set[str]:
    """
    Return names *used* in body that are not locally defined in body
    and not already in outer_defined.
    Does NOT recurse into nested FnDef / BladeGRPDef bodies.
    """
    local_defs: set[str] = set(outer_defined)
    used: set[str] = set()

    def walk(node: Any) -> None:
        if node is None:
            return
        t = type(node)

        if t is Identifier:
            used.add(node.name)
        elif t is FStringLiteral:
            for p in node.parts:
                if not isinstance(p, str):
                    walk(p)
        elif t is ListLiteral:
            for e in node.elements:
                walk(e)
        elif t is DictLiteral:
            for k, v in node.pairs:
                walk(k); walk(v)
        elif t is BinaryOp:
            walk(node.left); walk(node.right)
        elif t is UnaryOp:
            walk(node.operand)
        elif t is DotAccess:
            walk(node.obj)
        elif t is IndexAccess:
            walk(node.obj); walk(node.index)
        elif t is SliceAccess:
            walk(node.obj); walk(node.start); walk(node.end)
        elif t is CallExpr:
            walk(node.callee)
            for a in node.args:
                walk(a)
        elif t is PipelineExpr:
            walk(node.left); walk(node.right)
        elif t is AssignStmt:
            if isinstance(node.name, str):
                if node.is_declaration:
                    local_defs.add(node.name)
                else:
                    used.add(node.name)
            else:
                walk(node.name)
            walk(node.value)
        elif t is FnDef:
            if node.name:
                local_defs.add(node.name)
            # don't descend into body
        elif t is BladeGRPDef:
            local_defs.add(node.name)
        elif t is ReturnStmt:
            walk(node.value)
        elif t is RaiseStmt:
            walk(node.message)
        elif t is IfStmt:
            walk(node.condition)
            for s in node.then_body:
                walk(s)
            for cond, stmts in node.elif_clauses:
                walk(cond)
                for s in stmts:
                    walk(s)
            if node.else_body:
                for s in node.else_body:
                    walk(s)
        elif t is WhileStmt:
            walk(node.condition)
            for s in node.body:
                walk(s)
        elif t is ForStmt:
            local_defs.add(node.var_name)
            walk(node.iterable)
            for s in node.body:
                walk(s)
        elif t is TryCatch:
            for s in node.try_body:
                walk(s)
            local_defs.add(node.catch_var)
            for s in node.catch_body:
                walk(s)
        elif t is UselibStmt:
            raw = node.module_name
            bind = raw.split("/")[-1]
            if bind.endswith(".axb"):
                bind = bind[:-4]
            local_defs.add(bind)

    for stmt in body:
        walk(stmt)
    return used - local_defs


# ---------------------------------------------------------------------------
# Compiler
# ---------------------------------------------------------------------------

class Compiler:
    """Compile an AxonBlade AST Program into a top-level CodeObject."""

    def __init__(self) -> None:
        self._scope_stack: list[_Scope] = []
        self._code_stack: list[CodeObject] = []

    @property
    def _scope(self) -> _Scope:
        return self._scope_stack[-1]

    @property
    def _code(self) -> CodeObject:
        return self._code_stack[-1]

    def _push(self, code: CodeObject, scope: _Scope) -> None:
        self._code_stack.append(code)
        self._scope_stack.append(scope)

    def _pop(self) -> None:
        self._code_stack.pop()
        self._scope_stack.pop()

    def _emit(self, opcode: Opcode, arg: Any = None) -> int:
        return self._code.emit(opcode, arg)

    def _const(self, value: Any) -> int:
        return self._code.add_constant(value)

    def _patch(self, offset: int, value: Any) -> None:
        self._code.patch(offset, value)

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def compile(self, program: Program) -> CodeObject:
        code = CodeObject(name="<module>")
        scope = _Scope(parent=None, is_top_level=True)
        self._prescan_stmts(program.statements, scope)
        self._push(code, scope)
        for stmt in program.statements:
            self._compile(stmt)
        self._pop()
        code.cell_vars = sorted(scope.cell_vars)
        return code

    # ------------------------------------------------------------------
    # Pre-scan: discover cell_vars before compiling a scope
    # ------------------------------------------------------------------

    def _prescan_stmts(self, stmts: list, scope: _Scope) -> None:
        """Collect locally-defined names then find which are captured."""
        for stmt in stmts:
            if isinstance(stmt, AssignStmt) and isinstance(stmt.name, str) and stmt.is_declaration:
                scope.locals_set.add(stmt.name)
            elif isinstance(stmt, FnDef) and stmt.name:
                scope.locals_set.add(stmt.name)
            elif isinstance(stmt, BladeGRPDef):
                scope.locals_set.add(stmt.name)
            elif isinstance(stmt, ForStmt):
                scope.locals_set.add(stmt.var_name)
            elif isinstance(stmt, TryCatch):
                scope.locals_set.add(stmt.catch_var)
            elif isinstance(stmt, UselibStmt):
                raw = stmt.module_name
                bind = raw.split("/")[-1]
                if bind.endswith(".axb"):
                    bind = bind[:-4]
                scope.locals_set.add(bind)

        for stmt in stmts:
            self._find_cells_in_node(stmt, scope)

    def _find_cells_in_node(self, node: Any, scope: _Scope) -> None:
        """Walk AST to find which scope.locals_set names are captured by inner fns."""
        if isinstance(node, FnDef):
            params = {p.name for p in node.params}
            free = _collect_free_vars(node.body, params)
            for name in free:
                if name in scope.locals_set:
                    scope.cell_vars.add(name)
            for s in node.body:
                self._find_cells_in_node(s, scope)
        elif isinstance(node, BladeGRPDef):
            for method in node.methods:
                self._find_cells_in_node(method, scope)
        elif isinstance(node, IfStmt):
            for s in node.then_body:
                self._find_cells_in_node(s, scope)
            for _, body in node.elif_clauses:
                for s in body:
                    self._find_cells_in_node(s, scope)
            if node.else_body:
                for s in node.else_body:
                    self._find_cells_in_node(s, scope)
        elif isinstance(node, WhileStmt):
            for s in node.body:
                self._find_cells_in_node(s, scope)
        elif isinstance(node, ForStmt):
            for s in node.body:
                self._find_cells_in_node(s, scope)
        elif isinstance(node, TryCatch):
            for s in node.try_body:
                self._find_cells_in_node(s, scope)
            for s in node.catch_body:
                self._find_cells_in_node(s, scope)

    # ------------------------------------------------------------------
    # Name resolution
    # ------------------------------------------------------------------

    def _resolve_name(self, name: str) -> tuple[str, int | None]:
        """
        Return ('local', None), ('deref', idx), or ('global', None).
        'local'  → emit LOAD_VAR/STORE_VAR/DEFINE_VAR
        'deref'  → emit LOAD_DEREF/STORE_DEREF
        'global' → emit LOAD_VAR/STORE_VAR (VM falls back to globals dict)
        """
        depth = len(self._scope_stack) - 1
        own = self._scope_stack[depth]

        if name in own.locals_set:
            return ("local", None)
        if name in own.upvalues:
            return ("deref", own.upvalues.index(name))

        for d in range(depth - 1, -1, -1):
            outer = self._scope_stack[d]
            if outer.is_top_level:
                return ("global", None)
            if name in outer.locals_set or name in outer.upvalues:
                if name in outer.locals_set:
                    outer.cell_vars.add(name)
                idx = self._add_upvalue(name, depth)
                return ("deref", idx)

        return ("global", None)

    def _add_upvalue(self, name: str, at_depth: int) -> int:
        scope = self._scope_stack[at_depth]
        code = self._code_stack[at_depth]
        if name in scope.upvalues:
            return scope.upvalues.index(name)
        scope.upvalues.append(name)
        code.upvalue_names.append(name)
        return len(scope.upvalues) - 1

    def _emit_load(self, name: str) -> None:
        kind, idx = self._resolve_name(name)
        self._emit(Opcode.LOAD_DEREF, idx) if kind == "deref" else self._emit(Opcode.LOAD_VAR, name)

    def _emit_store(self, name: str) -> None:
        kind, idx = self._resolve_name(name)
        self._emit(Opcode.STORE_DEREF, idx) if kind == "deref" else self._emit(Opcode.STORE_VAR, name)

    def _emit_define(self, name: str) -> None:
        self._emit(Opcode.DEFINE_VAR, name)

    # ------------------------------------------------------------------
    # Main compile dispatch
    # ------------------------------------------------------------------

    def _compile(self, node: Any) -> None:  # noqa: C901
        t = type(node)

        # Literals
        if t is NumberLiteral:
            v = node.value
            c: Any = int(v) if isinstance(v, float) and v == int(v) else v
            self._emit(Opcode.PUSH_CONST, self._const(c))
        elif t is StringLiteral:
            self._emit(Opcode.PUSH_CONST, self._const(node.value))
        elif t is BoolLiteral:
            self._emit(Opcode.PUSH_TRUE if node.value else Opcode.PUSH_FALSE)
        elif t is NullLiteral:
            self._emit(Opcode.PUSH_NULL)
        elif t is ColorLiteral:
            self._emit(Opcode.PUSH_CONST, self._const(_ANSI_COLORS[node.name]))
        elif t is FStringLiteral:
            count = 0
            for part in node.parts:
                if isinstance(part, str):
                    self._emit(Opcode.PUSH_CONST, self._const(part))
                else:
                    self._compile(part)
                count += 1
            self._emit(Opcode.BUILD_FSTRING, count)
        elif t is ListLiteral:
            for elem in node.elements:
                self._compile(elem)
            self._emit(Opcode.MAKE_LIST, len(node.elements))
        elif t is DictLiteral:
            for key, val in node.pairs:
                self._compile(key)
                self._compile(val)
            self._emit(Opcode.MAKE_DICT, len(node.pairs))

        # Identifier
        elif t is Identifier:
            self._emit_load(node.name)

        # Operators
        elif t is BinaryOp:
            self._compile_binary(node)
        elif t is UnaryOp:
            self._compile(node.operand)
            self._emit(Opcode.NEG if node.op == "-" else Opcode.NOT)

        # Access
        elif t is DotAccess:
            self._compile(node.obj)
            self._emit(Opcode.GET_ATTR, node.attr)
        elif t is IndexAccess:
            self._compile(node.obj)
            self._compile(node.index)
            self._emit(Opcode.GET_INDEX)
        elif t is SliceAccess:
            self._compile(node.obj)
            self._compile(node.start) if node.start is not None else self._emit(Opcode.PUSH_NULL)
            self._compile(node.end)   if node.end   is not None else self._emit(Opcode.PUSH_NULL)
            self._emit(Opcode.GET_SLICE)

        # Calls
        elif t is CallExpr:
            self._compile(node.callee)
            for arg in node.args:
                self._compile(arg)
            self._emit(Opcode.CALL, len(node.args))
        elif t is PipelineExpr:
            self._compile_pipeline(node)

        # Statements
        elif t is AssignStmt:
            self._compile_assign(node)
        elif t is FnDef:
            self._compile_fn_def(node, define=(node.name != '<lambda>'))
        elif t is BladeGRPDef:
            self._compile_class_def(node)
        elif t is ReturnStmt:
            self._compile(node.value)
            self._emit(Opcode.RETURN)
        elif t is RaiseStmt:
            self._compile(node.message)
            self._emit(Opcode.RAISE)
        elif t is IfStmt:
            self._compile_if(node)
        elif t is WhileStmt:
            self._compile_while(node)
        elif t is ForStmt:
            self._compile_for(node)
        elif t is TryCatch:
            self._compile_try_catch(node)
        elif t is UselibStmt:
            self._emit(Opcode.IMPORT, node.module_name)
            raw = node.module_name
            bind = raw.split("/")[-1]
            if bind.endswith(".axb"):
                bind = bind[:-4]
            self._scope.locals_set.add(bind)
            self._emit_define(bind)
        elif t is Program:
            for stmt in node.statements:
                self._compile(stmt)

    # ------------------------------------------------------------------
    # Binary operators
    # ------------------------------------------------------------------

    _SIMPLE_OPS: dict[str, Opcode] = {
        "+": Opcode.ADD, "-": Opcode.SUB, "*": Opcode.MUL,
        "/": Opcode.DIV, "%": Opcode.MOD, "**": Opcode.POW,
        "==": Opcode.EQ,  "!=": Opcode.NEQ,
        "<":  Opcode.LT,  ">":  Opcode.GT,
        "<=": Opcode.LTE, ">=": Opcode.GTE,
    }

    def _compile_binary(self, node: BinaryOp) -> None:
        op = node.op
        if op == "-a":
            # Short-circuit AND: if TOS falsy → jump (TOS stays), else pop TOS
            self._compile(node.left)
            jump = self._emit(Opcode.JUMP_IF_FALSE, None)
            self._compile(node.right)
            self._patch(jump, len(self._code.instructions))
            return
        if op == "-o":
            # Short-circuit OR: if TOS truthy → jump (TOS stays), else pop TOS
            self._compile(node.left)
            jump = self._emit(Opcode.JUMP_IF_TRUE, None)
            self._compile(node.right)
            self._patch(jump, len(self._code.instructions))
            return
        opcode = self._SIMPLE_OPS.get(op)
        if opcode is None:
            raise SyntaxError(f"Unknown binary operator '{op}'")
        self._compile(node.left)
        self._compile(node.right)
        self._emit(opcode)

    # ------------------------------------------------------------------
    # Assignment
    # ------------------------------------------------------------------

    def _compile_assign(self, node: AssignStmt) -> None:
        target = node.name
        if isinstance(target, DotAccess):
            self._compile(target.obj)
            self._compile(node.value)
            self._emit(Opcode.SET_ATTR, target.attr)
        elif isinstance(target, IndexAccess):
            self._compile(target.obj)
            self._compile(target.index)
            self._compile(node.value)
            self._emit(Opcode.SET_INDEX)
        else:
            name: str = target  # type: ignore[assignment]
            self._compile(node.value)
            if node.is_declaration:
                self._scope.locals_set.add(name)
                self._emit_define(name)
            else:
                self._emit_store(name)

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    def _compile_pipeline(self, node: PipelineExpr) -> None:
        right = node.right
        if isinstance(right, CallExpr):
            self._compile(right.callee)
            self._compile(node.left)        # left inserted as first arg
            for arg in right.args:
                self._compile(arg)
            self._emit(Opcode.CALL, 1 + len(right.args))
        else:
            self._compile(right)            # bare callee
            self._compile(node.left)
            self._emit(Opcode.CALL, 1)

    # ------------------------------------------------------------------
    # Control flow
    # ------------------------------------------------------------------

    def _compile_if(self, node: IfStmt) -> None:
        end_jumps: list[int] = []

        # Then branch
        self._compile(node.condition)
        skip_then = self._emit(Opcode.JUMP_IF_FALSE, None)
        for stmt in node.then_body:
            self._compile(stmt)
        end_jumps.append(self._emit(Opcode.JUMP, None))
        self._patch(skip_then, len(self._code.instructions))
        self._emit(Opcode.POP)   # discard falsy condition

        # Elif branches
        for elif_cond, elif_body in node.elif_clauses:
            self._compile(elif_cond)
            skip_elif = self._emit(Opcode.JUMP_IF_FALSE, None)
            for stmt in elif_body:
                self._compile(stmt)
            end_jumps.append(self._emit(Opcode.JUMP, None))
            self._patch(skip_elif, len(self._code.instructions))
            self._emit(Opcode.POP)

        # Else branch
        if node.else_body is not None:
            for stmt in node.else_body:
                self._compile(stmt)

        end_ip = len(self._code.instructions)
        for j in end_jumps:
            self._patch(j, end_ip)

    def _compile_while(self, node: WhileStmt) -> None:
        loop_start = len(self._code.instructions)
        self._compile(node.condition)
        skip = self._emit(Opcode.JUMP_IF_FALSE, None)
        for stmt in node.body:
            self._compile(stmt)
        self._emit(Opcode.JUMP, loop_start)
        self._patch(skip, len(self._code.instructions))
        self._emit(Opcode.POP)   # discard falsy condition

    def _compile_for(self, node: ForStmt) -> None:
        # Index-based iteration using hidden locals (unique per loop position)
        uid      = f"_for_{node.line}_{node.col}"
        iter_var = f"__it{uid}"
        idx_var  = f"__ix{uid}"
        len_var  = f"__ln{uid}"

        self._compile(node.iterable)
        self._scope.locals_set.add(iter_var)
        self._emit_define(iter_var)

        self._emit(Opcode.LOAD_VAR, "len")
        self._emit(Opcode.LOAD_VAR, iter_var)
        self._emit(Opcode.CALL, 1)
        self._scope.locals_set.add(len_var)
        self._emit_define(len_var)

        self._emit(Opcode.PUSH_CONST, self._const(0))
        self._scope.locals_set.add(idx_var)
        self._emit_define(idx_var)

        loop_start = len(self._code.instructions)

        self._emit(Opcode.LOAD_VAR, idx_var)
        self._emit(Opcode.LOAD_VAR, len_var)
        self._emit(Opcode.LT)
        skip = self._emit(Opcode.JUMP_IF_FALSE, None)

        # Bind current element
        self._emit(Opcode.LOAD_VAR, iter_var)
        self._emit(Opcode.LOAD_VAR, idx_var)
        self._emit(Opcode.GET_INDEX)
        self._scope.locals_set.add(node.var_name)
        self._emit_define(node.var_name)

        for stmt in node.body:
            self._compile(stmt)

        # Increment index
        self._emit(Opcode.LOAD_VAR, idx_var)
        self._emit(Opcode.PUSH_CONST, self._const(1))
        self._emit(Opcode.ADD)
        self._emit(Opcode.STORE_VAR, idx_var)

        self._emit(Opcode.JUMP, loop_start)
        self._patch(skip, len(self._code.instructions))
        self._emit(Opcode.POP)   # discard falsy condition

    # ------------------------------------------------------------------
    # Exception handling
    # ------------------------------------------------------------------

    def _compile_try_catch(self, node: TryCatch) -> None:
        setup = self._emit(Opcode.SETUP_TRY, None)   # arg patched to handler ip

        for stmt in node.try_body:
            self._compile(stmt)

        self._emit(Opcode.POP_TRY)
        jump_end = self._emit(Opcode.JUMP, None)

        handler_ip = len(self._code.instructions)
        self._patch(setup, handler_ip)
        # TOS is the error dict (pushed by VM on exception)
        self._scope.locals_set.add(node.catch_var)
        self._emit_define(node.catch_var)

        for stmt in node.catch_body:
            self._compile(stmt)

        self._patch(jump_end, len(self._code.instructions))

    # ------------------------------------------------------------------
    # Function definition
    # ------------------------------------------------------------------

    def _compile_fn_def(self, node: FnDef, define: bool = True) -> None:
        """
        Compile a function body into a nested CodeObject, emit PUSH_CONST +
        MAKE_FN.  If define=True, also emit DEFINE_VAR to bind the name.
        If define=False, the AxonFunction is left on the stack (used by class
        compilation to collect methods without polluting the current scope).
        """
        fn_code = CodeObject(
            name=node.name or "<lambda>",
            param_names=[p.name for p in node.params],
            param_types=[p.type_ann for p in node.params],
        )
        fn_scope = _Scope(parent=self._scope, is_top_level=False)
        for p in node.params:
            fn_scope.locals_set.add(p.name)
        self._prescan_stmts(node.body, fn_scope)

        self._push(fn_code, fn_scope)
        for stmt in node.body:
            self._compile(stmt)
        # Implicit null return
        self._emit(Opcode.PUSH_NULL)
        self._emit(Opcode.RETURN)
        self._pop()

        fn_code.cell_vars = sorted(fn_scope.cell_vars)

        self._emit(Opcode.PUSH_CONST, self._const(fn_code))
        self._emit(Opcode.MAKE_FN)

        if define and node.name:
            self._scope.locals_set.add(node.name)
            self._emit_define(node.name)

    # ------------------------------------------------------------------
    # Class definition
    # ------------------------------------------------------------------

    def _compile_class_def(self, node: BladeGRPDef) -> None:
        """
        Compile each method as an anonymous AxonFunction left on the stack,
        then emit MAKE_CLASS to bundle them into an AxonBladeGRP.

        Stack before MAKE_CLASS (bottom → top): fn_method0, fn_method1, ...
        MAKE_CLASS arg = (class_name, [method0_name, method1_name, ...])
        """
        method_names: list[str] = []
        for method in node.methods:
            method_names.append(method.name)
            self._compile_fn_def(method, define=False)  # leave AxonFunction on stack

        self._emit(Opcode.MAKE_CLASS, (node.name, method_names))
        self._scope.locals_set.add(node.name)
        self._emit_define(node.name)


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------

def compile_source(source: str) -> CodeObject:
    """Parse source text and compile it to a CodeObject."""
    from core.parser import parse_source
    program = parse_source(source)
    return Compiler().compile(program)
