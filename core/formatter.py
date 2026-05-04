"""
core/formatter.py — AxonBlade code formatter (V2 Phase 2.1).

Walks the AST and emits canonical formatted source. Rules:
  - 4-space indentation per nesting level
  - Single space around all binary operators
  - One blank line between top-level declarations (FnDef, BladeGRPDef)
  - No trailing whitespace on any line

Usage:
    from core.formatter import Formatter
    from core.parser import parse_source
    formatted = Formatter().format(parse_source(source))
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

_OP_TOKENS: dict[str, str] = {
    "+": "+", "-": "-", "*": "*", "/": "/", "%": "%", "**": "**",
    "==": "==", "!=": "!=", "<": "<", ">": ">", "<=": "<=", ">=": ">=",
    "-a": "-a", "-o": "-o",
}

_INDENT = "    "  # 4 spaces


class Formatter:
    """Convert an AxonBlade AST back into formatted source code."""

    def format(self, program: Program) -> str:
        lines = self._fmt_program(program)
        # Strip trailing whitespace on each line, add final newline
        result = "\n".join(line.rstrip() for line in lines)
        if result and not result.endswith("\n"):
            result += "\n"
        return result

    # ------------------------------------------------------------------
    # Program level
    # ------------------------------------------------------------------

    def _fmt_program(self, node: Program) -> list[str]:
        out: list[str] = []
        for i, stmt in enumerate(node.statements):
            block = self._fmt_stmt(stmt, 0)
            if i > 0 and out:
                # Blank line before top-level function/class definitions
                if isinstance(stmt, (FnDef, BladeGRPDef)):
                    out.append("")
                elif isinstance(node.statements[i - 1], (FnDef, BladeGRPDef)):
                    out.append("")
            out.extend(block)
        return out

    # ------------------------------------------------------------------
    # Statement dispatch
    # ------------------------------------------------------------------

    def _fmt_stmt(self, node: object, depth: int) -> list[str]:
        pad = _INDENT * depth

        if isinstance(node, AssignStmt):
            return self._fmt_assign(node, pad)

        if isinstance(node, FnDef):
            return self._fmt_fn_def(node, depth)

        if isinstance(node, BladeGRPDef):
            return self._fmt_bladegrp(node, depth)

        if isinstance(node, ReturnStmt):
            return [f"{pad}return {self._fmt_expr(node.value)}"]

        if isinstance(node, RaiseStmt):
            return [f"{pad}raise {self._fmt_expr(node.message)}"]

        if isinstance(node, IfStmt):
            return self._fmt_if(node, depth)

        if isinstance(node, WhileStmt):
            return self._fmt_while(node, depth)

        if isinstance(node, ForStmt):
            return self._fmt_for(node, depth)

        if isinstance(node, TryCatch):
            return self._fmt_try_catch(node, depth)

        if isinstance(node, UselibStmt):
            return [f"{pad}uselib -{node.module_name}-"]

        # Bare expression statement (e.g., a call)
        return [f"{pad}{self._fmt_expr(node)}"]

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------

    def _fmt_assign(self, node: AssignStmt, pad: str) -> list[str]:
        val = self._fmt_expr(node.value)
        if isinstance(node.name, (DotAccess, IndexAccess)):
            lhs = self._fmt_expr(node.name)
        else:
            lhs = str(node.name)
        if node.is_declaration:
            return [f"{pad}>> {lhs} = {val}"]
        return [f"{pad}{lhs} = {val}"]

    def _fmt_fn_def(self, node: FnDef, depth: int) -> list[str]:
        pad = _INDENT * depth
        params = self._fmt_params(node.params)
        lines = [f"{pad}bladeFN {node.name}({params}) +/"]
        for stmt in node.body:
            lines.extend(self._fmt_stmt(stmt, depth + 1))
        lines.append(f"{pad}ECB")
        return lines

    def _fmt_bladegrp(self, node: BladeGRPDef, depth: int) -> list[str]:
        pad = _INDENT * depth
        lines = [f"{pad}bladeGRP {node.name} +/"]
        for i, method in enumerate(node.methods):
            if i > 0:
                lines.append("")
            lines.extend(self._fmt_fn_def(method, depth + 1))
        lines.append(f"{pad}ECB")
        return lines

    def _fmt_if(self, node: IfStmt, depth: int) -> list[str]:
        pad = _INDENT * depth
        lines = [f"{pad}if {self._fmt_expr(node.condition)} +/"]
        for stmt in node.then_body:
            lines.extend(self._fmt_stmt(stmt, depth + 1))
        for cond, body in node.elif_clauses:
            lines.append(f"{pad}elif {self._fmt_expr(cond)} +/")
            for stmt in body:
                lines.extend(self._fmt_stmt(stmt, depth + 1))
        if node.else_body is not None:
            lines.append(f"{pad}else +/")
            for stmt in node.else_body:
                lines.extend(self._fmt_stmt(stmt, depth + 1))
        lines.append(f"{pad}ECB")
        return lines

    def _fmt_while(self, node: WhileStmt, depth: int) -> list[str]:
        pad = _INDENT * depth
        lines = [f"{pad}while {self._fmt_expr(node.condition)} +/"]
        for stmt in node.body:
            lines.extend(self._fmt_stmt(stmt, depth + 1))
        lines.append(f"{pad}ECB")
        return lines

    def _fmt_for(self, node: ForStmt, depth: int) -> list[str]:
        pad = _INDENT * depth
        lines = [f"{pad}for {node.var_name} in {self._fmt_expr(node.iterable)} +/"]
        for stmt in node.body:
            lines.extend(self._fmt_stmt(stmt, depth + 1))
        lines.append(f"{pad}ECB")
        return lines

    def _fmt_try_catch(self, node: TryCatch, depth: int) -> list[str]:
        pad = _INDENT * depth
        lines = [f"{pad}try +/"]
        for stmt in node.try_body:
            lines.extend(self._fmt_stmt(stmt, depth + 1))
        lines.append(f"{pad}catch {node.catch_var} +/")
        for stmt in node.catch_body:
            lines.extend(self._fmt_stmt(stmt, depth + 1))
        lines.append(f"{pad}ECB")
        return lines

    # ------------------------------------------------------------------
    # Expression formatter
    # ------------------------------------------------------------------

    def _fmt_expr(self, node: object) -> str:
        if isinstance(node, NumberLiteral):
            v = node.value
            if isinstance(v, float) and v == int(v):
                return str(int(v))
            return str(v)

        if isinstance(node, StringLiteral):
            # Re-escape backslashes and double quotes
            escaped = node.value.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'

        if isinstance(node, FStringLiteral):
            return self._fmt_fstring(node)

        if isinstance(node, ColorLiteral):
            return f"-*{node.name}*-"

        if isinstance(node, BoolLiteral):
            return "true" if node.value else "false"

        if isinstance(node, NullLiteral):
            return "null"

        if isinstance(node, ListLiteral):
            if not node.elements:
                return "[]"
            items = ", ".join(self._fmt_expr(e) for e in node.elements)
            return f"[{items}]"

        if isinstance(node, DictLiteral):
            if not node.pairs:
                return "{}"
            pairs = ", ".join(
                f"{self._fmt_expr(k)}: {self._fmt_expr(v)}"
                for k, v in node.pairs
            )
            return "{" + pairs + "}"

        if isinstance(node, Identifier):
            return node.name

        if isinstance(node, BinaryOp):
            left = self._fmt_expr(node.left)
            right = self._fmt_expr(node.right)
            op = node.op
            # Parenthesize sub-binary-ops if they might be ambiguous
            if isinstance(node.left, BinaryOp):
                left = self._maybe_paren(node.left, node, left, side="left")
            if isinstance(node.right, BinaryOp):
                right = self._maybe_paren(node.right, node, right, side="right")
            return f"{left} {op} {right}"

        if isinstance(node, UnaryOp):
            operand = self._fmt_expr(node.operand)
            if node.op == "-n":
                return f"-n {operand}"
            return f"{node.op}{operand}"

        if isinstance(node, CallExpr):
            callee = self._fmt_expr(node.callee)
            args = ", ".join(self._fmt_expr(a) for a in node.args)
            return f"{callee}({args})"

        if isinstance(node, DotAccess):
            obj = self._fmt_expr(node.obj)
            return f"{obj}.{node.attr}"

        if isinstance(node, IndexAccess):
            obj = self._fmt_expr(node.obj)
            idx = self._fmt_expr(node.index)
            return f"{obj}~{idx}~"

        if isinstance(node, SliceAccess):
            obj = self._fmt_expr(node.obj)
            start = self._fmt_expr(node.start) if node.start is not None else ""
            end = self._fmt_expr(node.end) if node.end is not None else ""
            return f"{obj}~{start}:{end}~"

        if isinstance(node, PipelineExpr):
            left = self._fmt_expr(node.left)
            right = self._fmt_expr(node.right)
            return f"{left} |> {right}"

        # Fallback for raw expressions used as statements
        return repr(node)

    def _fmt_fstring(self, node: FStringLiteral) -> str:
        parts: list[str] = []
        for part in node.parts:
            if isinstance(part, str):
                # Escape double quotes in the string portion
                parts.append(part.replace('"', '\\"'))
            else:
                parts.append(f"&{{{self._fmt_expr(part)}}}")
        return '"' + "".join(parts) + '"'

    def _fmt_params(self, params: list[Param]) -> str:
        result = []
        for p in params:
            if p.type_ann:
                result.append(f"{p.name}#{p.type_ann}")
            else:
                result.append(p.name)
        return ", ".join(result)

    # ------------------------------------------------------------------
    # Precedence helper — add parens when needed for clarity
    # ------------------------------------------------------------------

    _PREC: dict[str, int] = {
        "|>": 1, "-o": 3, "-a": 5,
        "==": 7, "!=": 7, "<": 7, ">": 7, "<=": 7, ">=": 7,
        "+": 9, "-": 9,
        "*": 11, "/": 11, "%": 11,
        "**": 14,
    }

    def _maybe_paren(self, child: BinaryOp, parent: BinaryOp,
                     text: str, side: str) -> str:
        cp = self._PREC.get(child.op, 99)
        pp = self._PREC.get(parent.op, 99)
        if cp < pp:
            return f"({text})"
        # Right-associative: paren right child if same precedence (except **)
        if cp == pp and side == "right" and parent.op != "**":
            return f"({text})"
        return text
