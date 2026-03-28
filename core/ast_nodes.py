"""AST node definitions and pretty-writer for the AxonBlade language.

All nodes are Python @dataclass classes. Every node (except Param and Program)
carries line: int and col: int for error reporting.
"""

from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# 5.1 Literal Nodes
# ---------------------------------------------------------------------------

@dataclass
class NumberLiteral:
    value: float
    line: int
    col: int


@dataclass
class StringLiteral:
    value: str
    line: int
    col: int


@dataclass
class FStringLiteral:
    # parts: alternating str and Expr nodes
    parts: list
    line: int
    col: int


@dataclass
class ColorLiteral:
    name: str  # "red", "blue", etc.
    line: int
    col: int


@dataclass
class BoolLiteral:
    value: bool
    line: int
    col: int


@dataclass
class NullLiteral:
    line: int
    col: int


@dataclass
class ListLiteral:
    elements: list  # list of Expr nodes
    line: int
    col: int


@dataclass
class DictLiteral:
    pairs: list  # list of (key_expr, val_expr) tuples
    line: int
    col: int


# ---------------------------------------------------------------------------
# 5.2 Expression Nodes
# ---------------------------------------------------------------------------

@dataclass
class Identifier:
    name: str
    line: int
    col: int


@dataclass
class BinaryOp:
    left: object
    op: str  # "+", "-", "*", "/", "**", "%", "==", "!=", "<", ">", "<=", ">="
    right: object
    line: int
    col: int


@dataclass
class UnaryOp:
    op: str  # "-", "-n"
    operand: object
    line: int
    col: int


@dataclass
class CallExpr:
    callee: object  # Identifier or DotAccess
    args: list
    line: int
    col: int


@dataclass
class DotAccess:
    obj: object
    attr: str
    line: int
    col: int


@dataclass
class IndexAccess:
    obj: object
    index: object
    line: int
    col: int


@dataclass
class SliceAccess:
    obj: object
    start: object
    end: object
    line: int
    col: int


@dataclass
class PipelineExpr:
    left: object
    right: object  # must be a CallExpr; left is inserted as first arg
    line: int
    col: int


# ---------------------------------------------------------------------------
# 5.3 Statement Nodes
# ---------------------------------------------------------------------------

@dataclass
class AssignStmt:
    name: str
    value: object
    is_declaration: bool  # True if >> was used
    line: int
    col: int


@dataclass
class Param:
    name: str
    type_ann: str | None  # "str", "int", etc. or None


@dataclass
class FnDef:
    name: str
    params: list  # list of Param
    body: list  # list of statement nodes
    line: int
    col: int


@dataclass
class ReturnStmt:
    value: object
    line: int
    col: int


@dataclass
class RaiseStmt:
    message: object
    line: int
    col: int


@dataclass
class IfStmt:
    condition: object
    then_body: list
    elif_clauses: list  # list of (condition, body) tuples
    else_body: list | None
    line: int
    col: int


@dataclass
class WhileStmt:
    condition: object
    body: list
    line: int
    col: int


@dataclass
class ForStmt:
    var_name: str
    iterable: object
    body: list
    line: int
    col: int


@dataclass
class BladeGRPDef:
    name: str
    methods: list  # list of FnDef nodes
    line: int
    col: int


@dataclass
class TryCatch:
    try_body: list
    catch_var: str
    catch_body: list
    line: int
    col: int


@dataclass
class UselibStmt:
    module_name: str  # "math" or "./myfile"
    line: int
    col: int


@dataclass
class Program:
    statements: list


# ---------------------------------------------------------------------------
# Pretty-writer  (Phase 2.4)
# ---------------------------------------------------------------------------

def pretty_write(node, indent=0) -> str:
    """Return a human-readable, indented string representation of an AST node."""
    pad = "  " * indent

    # -- Literal nodes -------------------------------------------------------

    if isinstance(node, NumberLiteral):
        return f"{pad}NumberLiteral({node.value})"

    if isinstance(node, StringLiteral):
        return f"{pad}StringLiteral({node.value!r})"

    if isinstance(node, FStringLiteral):
        lines = [f"{pad}FStringLiteral("]
        for part in node.parts:
            if isinstance(part, str):
                lines.append(f"{pad}  StringPart({part!r})")
            else:
                lines.append(pretty_write(part, indent + 1))
        lines.append(f"{pad})")
        return "\n".join(lines)

    if isinstance(node, ColorLiteral):
        return f"{pad}ColorLiteral(-*{node.name}*-)"

    if isinstance(node, BoolLiteral):
        return f"{pad}BoolLiteral({node.value})"

    if isinstance(node, NullLiteral):
        return f"{pad}NullLiteral()"

    if isinstance(node, ListLiteral):
        if not node.elements:
            return f"{pad}ListLiteral([])"
        lines = [f"{pad}ListLiteral(["]
        for elem in node.elements:
            lines.append(pretty_write(elem, indent + 1))
        lines.append(f"{pad}])")
        return "\n".join(lines)

    if isinstance(node, DictLiteral):
        if not node.pairs:
            return f"{pad}DictLiteral({{}})"
        lines = [f"{pad}DictLiteral({{"]
        for key, val in node.pairs:
            lines.append(f"{pad}  {pretty_write(key, 0)}: {pretty_write(val, 0)}")
        lines.append(f"{pad}}})")
        return "\n".join(lines)

    # -- Expression nodes ----------------------------------------------------

    if isinstance(node, Identifier):
        return f"{pad}Identifier({node.name})"

    if isinstance(node, BinaryOp):
        lines = [f"{pad}BinaryOp("]
        lines.append(pretty_write(node.left, indent + 1))
        lines.append(f"{pad}  op={node.op!r}")
        lines.append(pretty_write(node.right, indent + 1))
        lines.append(f"{pad})")
        return "\n".join(lines)

    if isinstance(node, UnaryOp):
        lines = [f"{pad}UnaryOp(op={node.op!r}"]
        lines.append(pretty_write(node.operand, indent + 1))
        lines.append(f"{pad})")
        return "\n".join(lines)

    if isinstance(node, CallExpr):
        lines = [f"{pad}CallExpr("]
        lines.append(f"{pad}  callee=")
        lines.append(pretty_write(node.callee, indent + 2))
        if node.args:
            lines.append(f"{pad}  args=[")
            for arg in node.args:
                lines.append(pretty_write(arg, indent + 2))
            lines.append(f"{pad}  ]")
        else:
            lines.append(f"{pad}  args=[]")
        lines.append(f"{pad})")
        return "\n".join(lines)

    if isinstance(node, DotAccess):
        lines = [f"{pad}DotAccess("]
        lines.append(pretty_write(node.obj, indent + 1))
        lines.append(f"{pad}  .{node.attr}")
        lines.append(f"{pad})")
        return "\n".join(lines)

    if isinstance(node, IndexAccess):
        lines = [f"{pad}IndexAccess("]
        lines.append(pretty_write(node.obj, indent + 1))
        lines.append(f"{pad}  index=")
        lines.append(pretty_write(node.index, indent + 2))
        lines.append(f"{pad})")
        return "\n".join(lines)

    if isinstance(node, SliceAccess):
        lines = [f"{pad}SliceAccess("]
        lines.append(pretty_write(node.obj, indent + 1))
        start_str = pretty_write(node.start, 0) if node.start else "None"
        end_str = pretty_write(node.end, 0) if node.end else "None"
        lines.append(f"{pad}  start={start_str}")
        lines.append(f"{pad}  end={end_str}")
        lines.append(f"{pad})")
        return "\n".join(lines)

    if isinstance(node, PipelineExpr):
        lines = [f"{pad}PipelineExpr("]
        lines.append(pretty_write(node.left, indent + 1))
        lines.append(f"{pad}  |>")
        lines.append(pretty_write(node.right, indent + 1))
        lines.append(f"{pad})")
        return "\n".join(lines)

    # -- Statement nodes -----------------------------------------------------

    if isinstance(node, AssignStmt):
        decl = ">> " if node.is_declaration else ""
        lines = [f"{pad}AssignStmt({decl}{node.name} ="]
        lines.append(pretty_write(node.value, indent + 1))
        lines.append(f"{pad})")
        return "\n".join(lines)

    if isinstance(node, Param):
        if node.type_ann:
            return f"{pad}Param({node.name}#{node.type_ann})"
        return f"{pad}Param({node.name})"

    if isinstance(node, FnDef):
        params_str = ", ".join(
            f"{p.name}#{p.type_ann}" if p.type_ann else p.name
            for p in node.params
        )
        lines = [f"{pad}FnDef({node.name}({params_str}) +/"]
        for stmt in node.body:
            lines.append(pretty_write(stmt, indent + 1))
        lines.append(f"{pad}ECB)")
        return "\n".join(lines)

    if isinstance(node, ReturnStmt):
        lines = [f"{pad}ReturnStmt("]
        lines.append(pretty_write(node.value, indent + 1))
        lines.append(f"{pad})")
        return "\n".join(lines)

    if isinstance(node, RaiseStmt):
        lines = [f"{pad}RaiseStmt("]
        lines.append(pretty_write(node.message, indent + 1))
        lines.append(f"{pad})")
        return "\n".join(lines)

    if isinstance(node, IfStmt):
        lines = [f"{pad}IfStmt("]
        lines.append(f"{pad}  condition=")
        lines.append(pretty_write(node.condition, indent + 2))
        lines.append(f"{pad}  then +/")
        for stmt in node.then_body:
            lines.append(pretty_write(stmt, indent + 2))
        for cond, body in node.elif_clauses:
            lines.append(f"{pad}  elif")
            lines.append(pretty_write(cond, indent + 2))
            lines.append(f"{pad}  +/")
            for stmt in body:
                lines.append(pretty_write(stmt, indent + 2))
        if node.else_body is not None:
            lines.append(f"{pad}  else +/")
            for stmt in node.else_body:
                lines.append(pretty_write(stmt, indent + 2))
        lines.append(f"{pad}ECB)")
        return "\n".join(lines)

    if isinstance(node, WhileStmt):
        lines = [f"{pad}WhileStmt("]
        lines.append(pretty_write(node.condition, indent + 1))
        lines.append(f"{pad}  +/")
        for stmt in node.body:
            lines.append(pretty_write(stmt, indent + 1))
        lines.append(f"{pad}ECB)")
        return "\n".join(lines)

    if isinstance(node, ForStmt):
        lines = [f"{pad}ForStmt({node.var_name} in"]
        lines.append(pretty_write(node.iterable, indent + 1))
        lines.append(f"{pad}  +/")
        for stmt in node.body:
            lines.append(pretty_write(stmt, indent + 1))
        lines.append(f"{pad}ECB)")
        return "\n".join(lines)

    if isinstance(node, BladeGRPDef):
        lines = [f"{pad}BladeGRPDef({node.name} +/"]
        for method in node.methods:
            lines.append(pretty_write(method, indent + 1))
        lines.append(f"{pad}ECB)")
        return "\n".join(lines)

    if isinstance(node, TryCatch):
        lines = [f"{pad}TryCatch("]
        lines.append(f"{pad}  try +/")
        for stmt in node.try_body:
            lines.append(pretty_write(stmt, indent + 2))
        lines.append(f"{pad}  catch {node.catch_var} +/")
        for stmt in node.catch_body:
            lines.append(pretty_write(stmt, indent + 2))
        lines.append(f"{pad}ECB)")
        return "\n".join(lines)

    if isinstance(node, UselibStmt):
        return f"{pad}UselibStmt(-{node.module_name}-)"

    if isinstance(node, Program):
        lines = [f"{pad}Program("]
        for stmt in node.statements:
            lines.append(pretty_write(stmt, indent + 1))
        lines.append(f"{pad})")
        return "\n".join(lines)

    return f"{pad}<Unknown node: {type(node).__name__}>"
