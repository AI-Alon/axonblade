"""
core/parser.py — AxonBlade parser (Weeks 3–4, Phases 3.1-4.5).

Week 3 implements a Pratt (top-down operator precedence) parser for all
AxonBlade expressions.

Week 4 extends the parser with full statement-level parsing:
  4.1  Variable declarations (>>) and re-assignments
  4.2  bladeFN function definitions and bladeGRP class definitions
  4.3  Control flow: if/elif/else, while, for
  4.4  try/catch, uselib, raise, return
  4.5  Top-level Program node + comprehensive tests

Precedence table (tightest first):
    postfix (., (), ~)  >  **  >  * / %  >  + -
    > comparisons  >  not  >  and  >  or  >  |>
"""

from __future__ import annotations

from typing import Optional

from core.tokens import Token, TokenType
from core.lexer import Lexer
from core.ast_nodes import (
    AssignStmt,
    BladeGRPDef,
    BoolLiteral,
    BinaryOp,
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


# ---------------------------------------------------------------------------
# 3.1 — Binding-power tables
# ---------------------------------------------------------------------------

# (left_bp, right_bp) for infix binary operators
_INFIX_BP: dict[TokenType, tuple[int, int]] = {
    TokenType.PIPE:    (1, 2),    # |>  pipeline — lowest
    TokenType.OR:      (3, 4),
    TokenType.AND:     (5, 6),
    TokenType.EQ:      (7, 8),    # comparisons
    TokenType.NEQ:     (7, 8),
    TokenType.LT:      (7, 8),
    TokenType.GT:      (7, 8),
    TokenType.LTE:     (7, 8),
    TokenType.GTE:     (7, 8),
    TokenType.PLUS:    (9, 10),
    TokenType.MINUS:   (9, 10),
    TokenType.STAR:    (11, 12),
    TokenType.SLASH:   (11, 12),
    TokenType.PERCENT: (11, 12),
    TokenType.POWER:   (14, 13),  # right-associative: right_bp < left_bp
}

# Postfix operators (., (), ~) bind tighter than all binary operators
_POSTFIX_BP: int = 16

# Prefix right-binding powers
_BP_UNARY_MINUS: int = 13  # same as POWER right_bp → -(2**2) works correctly
_BP_NOT: int = 6            # captures comparisons (left_bp=7>6), stops at and (left_bp=5≤6)

# Operator string map for BinaryOp nodes
_TOKEN_TO_OP: dict[TokenType, str] = {
    TokenType.PLUS:    "+",
    TokenType.MINUS:   "-",
    TokenType.STAR:    "*",
    TokenType.SLASH:   "/",
    TokenType.PERCENT: "%",
    TokenType.POWER:   "**",
    TokenType.EQ:      "==",
    TokenType.NEQ:     "!=",
    TokenType.LT:      "<",
    TokenType.GT:      ">",
    TokenType.LTE:     "<=",
    TokenType.GTE:     ">=",
}


# ---------------------------------------------------------------------------
# ParseError
# ---------------------------------------------------------------------------

class ParseError(SyntaxError):
    """Raised for parse failures, carrying source location."""

    def __init__(self, message: str, line: int = 0, col: int = 0) -> None:
        super().__init__(message)
        self.line = line
        self.col = col

    def __str__(self) -> str:
        loc = f" [line {self.line}, col {self.col}]" if self.line else ""
        return f"ParseError{loc}: {self.args[0]}"


# ---------------------------------------------------------------------------
# 3.1 — Parser class scaffold & helpers
# ---------------------------------------------------------------------------

class Parser:
    """
    AxonBlade Pratt parser.

    Phase 3 implements the complete expression parser.
    Phase 4 (Week 4) extends this class with statement-level parsing.
    """

    def __init__(self, tokens: list[Token]) -> None:
        self.tokens: list[Token] = tokens
        self.pos: int = 0
        # True while parsing the content of a ~...~ subscript.
        # Prevents the closing ~ from being mis-parsed as a new subscript opener.
        # Automatically inherited by all recursive parse_expr calls.
        # Explicitly reset to False inside (), [], {} so nested subscripts
        # inside delimited contexts still work (e.g. items~f(arr~0~)~).
        self._stop_tilde: bool = False

    # --- Navigation helpers ------------------------------------------------

    def peek(self, offset: int = 0) -> Token:
        """Return token at pos+offset without consuming.  Returns EOF if past end."""
        idx = self.pos + offset
        if idx >= len(self.tokens):
            return self.tokens[-1]  # always EOF sentinel
        return self.tokens[idx]

    def consume(self) -> Token:
        """Return current token and advance position."""
        tok = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return tok

    def expect(self, *types: TokenType) -> Token:
        """
        Consume and return the current token.
        Raises ParseError if it is not one of *types*.
        """
        tok = self.peek()
        if tok.type not in types:
            expected = " or ".join(t.name for t in types)
            val_str = f" ({tok.value!r})" if tok.value is not None else ""
            raise ParseError(
                f"Expected {expected}, got {tok.type.name}{val_str}",
                tok.line,
                tok.col,
            )
        return self.consume()

    def check(self, *types: TokenType) -> bool:
        """Return True if the current token type is in *types*."""
        return self.peek().type in types

    def match(self, *types: TokenType) -> Optional[Token]:
        """Consume and return the current token if its type is in *types*, else None."""
        if self.peek().type in types:
            return self.consume()
        return None

    def skip_newlines(self) -> None:
        """Consume all consecutive NEWLINE tokens."""
        while self.peek().type == TokenType.NEWLINE:
            self.consume()

    def _error(self, msg: str, tok: Optional[Token] = None) -> ParseError:
        t = tok or self.peek()
        return ParseError(msg, t.line, t.col)

    # -----------------------------------------------------------------------
    # 3.2 — Literal & grouping parsers
    # -----------------------------------------------------------------------

    def _parse_fstring(self, tok: Token) -> FStringLiteral:
        """
        Convert an FSTRING token's raw parts into an FStringLiteral.

        The lexer stores parts as a list of ("str", text) | ("expr", src_str).
        We re-lex and re-parse each ("expr", src_str) into a proper AST node.
        Sub-parsers start fresh with _stop_tilde=False.
        """
        parts: list = []
        for kind, text in tok.value:
            if kind == "str":
                parts.append(text)
            else:
                sub_tokens = Lexer(text).tokenize()
                sub_expr = Parser(sub_tokens).parse_expr(0)
                parts.append(sub_expr)
        return FStringLiteral(parts=parts, line=tok.line, col=tok.col)

    def _parse_list(self, tok: Token) -> ListLiteral:
        """
        Parse list literal [ expr, ... ].  tok is the already-consumed '['.
        Resets _stop_tilde so subscripts inside [] work correctly.
        """
        elements: list = []
        old_stop = self._stop_tilde
        self._stop_tilde = False
        try:
            self.skip_newlines()
            if not self.check(TokenType.RBRACKET):
                elements.append(self.parse_expr(0))
                while self.match(TokenType.COMMA):
                    self.skip_newlines()
                    if self.check(TokenType.RBRACKET):
                        break  # trailing comma allowed
                    elements.append(self.parse_expr(0))
            self.skip_newlines()
            self.expect(TokenType.RBRACKET)
        finally:
            self._stop_tilde = old_stop
        return ListLiteral(elements=elements, line=tok.line, col=tok.col)

    def _parse_dict(self, tok: Token) -> DictLiteral:
        """
        Parse dict literal { key: expr, ... }.  tok is the already-consumed '{'.

        Bare IDENT keys are treated as string literal keys (AxonBlade syntax:
        {name: "Ada"} stores the key as string "name", matching player~"name"~).
        Resets _stop_tilde so subscripts inside {} work correctly.
        """
        pairs: list = []
        old_stop = self._stop_tilde
        self._stop_tilde = False
        try:
            self.skip_newlines()
            if not self.check(TokenType.RBRACE):
                key = self._parse_dict_key()
                self.expect(TokenType.COLON)
                val = self.parse_expr(0)
                pairs.append((key, val))
                while self.match(TokenType.COMMA):
                    self.skip_newlines()
                    if self.check(TokenType.RBRACE):
                        break  # trailing comma allowed
                    key = self._parse_dict_key()
                    self.expect(TokenType.COLON)
                    val = self.parse_expr(0)
                    pairs.append((key, val))
            self.skip_newlines()
            self.expect(TokenType.RBRACE)
        finally:
            self._stop_tilde = old_stop
        return DictLiteral(pairs=pairs, line=tok.line, col=tok.col)

    def _parse_dict_key(self) -> object:
        """
        Parse one dict key.
        A bare IDENT becomes a StringLiteral (JS-style object key semantics).
        Any other token is parsed as a full expression.
        """
        tok = self.peek()
        if tok.type == TokenType.IDENT:
            self.consume()
            return StringLiteral(value=tok.value, line=tok.line, col=tok.col)
        return self.parse_expr(0)

    def _parse_grouped(self) -> object:
        """
        Parse a grouped expression ( expr ).  '(' already consumed.
        Resets _stop_tilde so subscripts inside () work correctly.
        """
        old_stop = self._stop_tilde
        self._stop_tilde = False
        try:
            self.skip_newlines()
            expr = self.parse_expr(0)
            self.skip_newlines()
            self.expect(TokenType.RPAREN)
        finally:
            self._stop_tilde = old_stop
        return expr

    # -----------------------------------------------------------------------
    # 3.3 — Prefix handler (NUD)
    # -----------------------------------------------------------------------

    def _parse_prefix(self) -> object:
        """
        Consume the current token and return the corresponding prefix node.
        Handles literals, unary operators, and delimited expressions.
        """
        tok = self.consume()

        # --- Grouping ---
        if tok.type == TokenType.LPAREN:
            return self._parse_grouped()

        # --- Prefix unary operators ---
        if tok.type == TokenType.MINUS:
            operand = self.parse_expr(_BP_UNARY_MINUS)
            return UnaryOp(op="-", operand=operand, line=tok.line, col=tok.col)

        if tok.type == TokenType.NOT:
            operand = self.parse_expr(_BP_NOT)
            return UnaryOp(op="-n", operand=operand, line=tok.line, col=tok.col)

        # --- Literals (Phase 3.2) ---
        if tok.type == TokenType.NUMBER:
            return NumberLiteral(value=tok.value, line=tok.line, col=tok.col)

        if tok.type == TokenType.STRING:
            return StringLiteral(value=tok.value, line=tok.line, col=tok.col)

        if tok.type == TokenType.FSTRING:
            return self._parse_fstring(tok)

        if tok.type == TokenType.COLOR:
            return ColorLiteral(name=tok.value, line=tok.line, col=tok.col)

        if tok.type == TokenType.TRUE:
            return BoolLiteral(value=True, line=tok.line, col=tok.col)

        if tok.type == TokenType.FALSE:
            return BoolLiteral(value=False, line=tok.line, col=tok.col)

        if tok.type == TokenType.NULL:
            return NullLiteral(line=tok.line, col=tok.col)

        # --- Collection literals ---
        if tok.type == TokenType.LBRACKET:
            return self._parse_list(tok)

        if tok.type == TokenType.LBRACE:
            return self._parse_dict(tok)

        # --- Identifiers ---
        if tok.type == TokenType.IDENT:
            return Identifier(name=tok.value, line=tok.line, col=tok.col)

        # blade is a valid primary expression (becomes Identifier("blade"))
        if tok.type == TokenType.SELF:
            return Identifier(name="blade", line=tok.line, col=tok.col)

        # Inline anonymous function: bladeFN(params) +/ body ECB
        if tok.type == TokenType.BLADEFN:
            return self._parse_fn_def(pre_consumed=tok)

        val_str = f" ({tok.value!r})" if tok.value is not None else ""
        raise self._error(
            f"Unexpected token {tok.type.name}{val_str} in expression", tok
        )

    # -----------------------------------------------------------------------
    # 3.3/3.4 — Postfix handler (LED for postfix)
    # -----------------------------------------------------------------------

    def _parse_postfix(self, left: object) -> object:
        """
        Parse one postfix operation on an already-parsed left expression:
          obj.attr          → DotAccess
          callee(args)      → CallExpr
          obj~index~        → IndexAccess
          obj~start:end~    → SliceAccess
        """
        tok = self.peek()

        # Dot access: left.attr
        if tok.type == TokenType.DOT:
            self.consume()  # .
            attr_tok = self.expect(TokenType.IDENT)
            return DotAccess(
                obj=left, attr=attr_tok.value, line=tok.line, col=tok.col
            )

        # Function / method call: left(args)
        if tok.type == TokenType.LPAREN:
            self.consume()  # (
            args = self._parse_arg_list()
            self.expect(TokenType.RPAREN)
            return CallExpr(callee=left, args=args, line=tok.line, col=tok.col)

        # Subscript / slice: left~index~ or left~start:end~
        if tok.type == TokenType.TILDE:
            return self._parse_subscript(left, tok)

        raise self._error(f"Unexpected postfix token {tok.type.name}", tok)

    def _parse_subscript(self, obj: object, tilde_tok: Token) -> object:
        """
        Parse ~index~ → IndexAccess  or  ~start:end~ → SliceAccess.
        Handles omitted start (~:end~) and omitted end (~start:~).
        Opening ~ confirmed by caller (peek), consumed here.

        Sets _stop_tilde=True for the duration of parsing the index/bounds so
        that the closing ~ is not consumed as a new postfix subscript.
        Resets to False automatically when entering nested (), [], {} contexts.
        """
        self.consume()  # opening ~
        old_stop = self._stop_tilde
        self._stop_tilde = True
        try:
            # ~:end~  — omitted start
            if self.check(TokenType.COLON):
                self.consume()  # :
                end = None if self.check(TokenType.TILDE) else self.parse_expr(0)
                self._stop_tilde = old_stop
                self.expect(TokenType.TILDE)
                return SliceAccess(
                    obj=obj, start=None, end=end,
                    line=tilde_tok.line, col=tilde_tok.col,
                )

            first = self.parse_expr(0)

            if self.match(TokenType.COLON):
                # ~first:end~  or  ~first:~
                end = None if self.check(TokenType.TILDE) else self.parse_expr(0)
                self._stop_tilde = old_stop
                self.expect(TokenType.TILDE)
                return SliceAccess(
                    obj=obj, start=first, end=end,
                    line=tilde_tok.line, col=tilde_tok.col,
                )

            self._stop_tilde = old_stop
            self.expect(TokenType.TILDE)
            return IndexAccess(
                obj=obj, index=first, line=tilde_tok.line, col=tilde_tok.col
            )
        except Exception:
            self._stop_tilde = old_stop
            raise

    def _parse_arg_list(self) -> list:
        """
        Parse comma-separated argument list inside '(' ... ')'.
        Caller has consumed '(' and must consume ')' after this returns.
        Resets _stop_tilde so subscripts inside () arguments work correctly.
        Trailing commas are allowed.
        """
        args: list = []
        old_stop = self._stop_tilde
        self._stop_tilde = False
        try:
            self.skip_newlines()
            if self.check(TokenType.RPAREN):
                return args
            args.append(self.parse_expr(0))
            while self.match(TokenType.COMMA):
                self.skip_newlines()
                if self.check(TokenType.RPAREN):
                    break  # trailing comma
                args.append(self.parse_expr(0))
        finally:
            self._stop_tilde = old_stop
        return args

    # -----------------------------------------------------------------------
    # 3.4/3.5 — Main Pratt expression loop
    # -----------------------------------------------------------------------

    def parse_expr(self, min_bp: int = 0) -> object:
        """
        Parse an expression using Pratt top-down operator precedence.

        Callers pass min_bp to control what operators are absorbed:
          - 0  → parse the full expression
          - n  → only absorb operators whose left_bp > n

        self._stop_tilde is checked for ~ to prevent the closing ~ of a
        subscript from being consumed as a new subscript opener.

        Returns an AST expression node.
        """
        left = self._parse_prefix()

        while True:
            tok = self.peek()

            # ~ as postfix subscript opener: blocked when inside ~...~
            if tok.type == TokenType.TILDE:
                if self._stop_tilde or _POSTFIX_BP <= min_bp:
                    break
                left = self._parse_postfix(left)
                continue

            # Other postfix operators: ., (
            if tok.type in (TokenType.DOT, TokenType.LPAREN):
                if _POSTFIX_BP <= min_bp:
                    break
                left = self._parse_postfix(left)
                continue

            # Binary infix operators
            bp_pair = _INFIX_BP.get(tok.type)
            if bp_pair is None:
                break  # token is not an infix operator

            left_bp, right_bp = bp_pair
            if left_bp <= min_bp:
                break  # current operator has lower/equal precedence — stop

            op_tok = self.consume()

            # --- Phase 3.5: Pipeline operator |> ---
            if op_tok.type == TokenType.PIPE:
                right = self.parse_expr(right_bp)
                left = PipelineExpr(
                    left=left, right=right, line=op_tok.line, col=op_tok.col
                )
                continue

            # --- Logical operators: produce BinaryOp with string op ---
            if op_tok.type == TokenType.OR:
                right = self.parse_expr(right_bp)
                left = BinaryOp(
                    left=left, op="-o", right=right,
                    line=op_tok.line, col=op_tok.col,
                )
                continue

            if op_tok.type == TokenType.AND:
                right = self.parse_expr(right_bp)
                left = BinaryOp(
                    left=left, op="-a", right=right,
                    line=op_tok.line, col=op_tok.col,
                )
                continue

            # --- Arithmetic and comparison operators ---
            op_str = _TOKEN_TO_OP[op_tok.type]
            right = self.parse_expr(right_bp)
            left = BinaryOp(
                left=left, op=op_str, right=right,
                line=op_tok.line, col=op_tok.col,
            )

        return left

    # -----------------------------------------------------------------------
    # 4.1 — Variable declaration and assignment  (Phase 4.1)
    # -----------------------------------------------------------------------

    def _parse_assign_or_expr_stmt(self) -> object:
        """
        Parse either:
          >> name = expr          → AssignStmt(is_declaration=True)
          name = expr             → AssignStmt(is_declaration=False)
          name~index~ = expr      → IndexAccess assignment (AssignStmt target stored as expr)
          expr                    → expression statement (e.g. write(...))

        Also handles subscript assignment: obj~key~ = val stored as
        AssignStmt where name is the IndexAccess node (evaluator handles this).
        """
        tok = self.peek()

        # >> name = expr  (variable declaration)
        if tok.type == TokenType.VARDECL:
            self.consume()  # >>
            name_tok = self.expect(TokenType.IDENT)
            self.expect(TokenType.ASSIGN)
            value = self.parse_expr(0)
            return AssignStmt(
                name=name_tok.value, value=value,
                is_declaration=True, line=tok.line, col=tok.col,
            )

        # name = expr  (re-assignment) — look ahead past the expression
        # We parse the left side as an expression, then check for '='
        left = self.parse_expr(0)

        if self.check(TokenType.ASSIGN):
            assign_tok = self.consume()  # =
            value = self.parse_expr(0)
            # Plain identifier assignment
            if isinstance(left, Identifier):
                return AssignStmt(
                    name=left.name, value=value,
                    is_declaration=False, line=left.line, col=left.col,
                )
            # Subscript assignment: obj~key~ = val  or  obj~k1~~k2~ = val
            # Store the lhs node directly so the evaluator can dispatch
            if isinstance(left, (IndexAccess, DotAccess)):
                return AssignStmt(
                    name=left, value=value,
                    is_declaration=False, line=left.line, col=left.col,
                )
            raise self._error(
                "Invalid assignment target", assign_tok
            )

        # Otherwise it's a bare expression statement (e.g. write(...))
        return left

    # -----------------------------------------------------------------------
    # 4.2 — Function and class definitions  (Phase 4.2)
    # -----------------------------------------------------------------------

    def _parse_param_list(self) -> list[Param]:
        """
        Parse a bladeFN parameter list between '(' and ')'.
        Each param is either:
          name          → Param(name, type_ann=None)
          name#type     → Param(name, type_ann="str"/etc.)

        The lexer emits TYPE_ANN tokens (value = type name string) directly
        after a param IDENT inside a param context.
        """
        params: list[Param] = []
        self.expect(TokenType.LPAREN)
        if not self.check(TokenType.RPAREN):
            params.append(self._parse_one_param())
            while self.match(TokenType.COMMA):
                if self.check(TokenType.RPAREN):
                    break
                params.append(self._parse_one_param())
        self.expect(TokenType.RPAREN)
        return params

    def _parse_one_param(self) -> Param:
        """
        Parse a single parameter: name  or  name#type.

        The lexer emits TYPE_ANN with value=(param_name, type_name) for
        annotated params, and a plain IDENT (or SELF) for unannotated params.
        """
        tok = self.peek()
        if tok.type == TokenType.TYPE_ANN:
            self.consume()
            param_name, type_ann = tok.value  # tuple from lexer
            return Param(name=param_name, type_ann=type_ann)
        # Accept SELF keyword as a param name ("blade" in method definitions)
        if tok.type == TokenType.SELF:
            self.consume()
            return Param(name="blade", type_ann=None)
        name_tok = self.expect(TokenType.IDENT)
        return Param(name=name_tok.value, type_ann=None)

    def _parse_block(self) -> list:
        """
        Parse a block: expect BLOCKOPEN (+/), then statements until ECB.
        Handles surrounding NEWLINE/INDENT/DEDENT tokens emitted by the lexer.
        Returns a list of statement nodes.
        """
        self.expect(TokenType.BLOCKOPEN)
        self.skip_newlines()
        # Consume optional INDENT emitted by the lexer
        self.match(TokenType.INDENT)
        self.skip_newlines()

        body: list = []
        while not self.check(TokenType.ECB) and not self.check(TokenType.EOF):
            stmt = self.parse_statement()
            if stmt is not None:
                body.append(stmt)
            self.skip_newlines()

        # Consume optional DEDENT before ECB
        self.match(TokenType.DEDENT)
        self.skip_newlines()
        self.expect(TokenType.ECB)
        return body

    def _parse_fn_def(self, pre_consumed: Token = None) -> FnDef:
        """
        Parse bladeFN name(params) +/ body ECB
        Also handles anonymous inline lambdas: bladeFN(params) +/ body ECB
        If pre_consumed is given, the bladeFN token was already consumed by the caller.
        """
        fn_tok = pre_consumed if pre_consumed is not None else self.consume()  # bladeFN
        # Optional name (anonymous functions used in on_key callbacks etc.)
        name: str = "<lambda>"
        if self.check(TokenType.IDENT):
            name = self.consume().value
        params = self._parse_param_list()
        body = self._parse_block()
        return FnDef(name=name, params=params, body=body, line=fn_tok.line, col=fn_tok.col)

    def _parse_bladegrp_def(self) -> BladeGRPDef:
        """Parse bladeGRP Name +/ methods ECB"""
        grp_tok = self.consume()  # bladeGRP
        name_tok = self.expect(TokenType.IDENT)
        self.expect(TokenType.BLOCKOPEN)
        self.skip_newlines()
        self.match(TokenType.INDENT)
        self.skip_newlines()

        methods: list[FnDef] = []
        while not self.check(TokenType.ECB) and not self.check(TokenType.EOF):
            self.skip_newlines()
            self.match(TokenType.INDENT)
            self.match(TokenType.DEDENT)
            self.skip_newlines()
            if self.check(TokenType.ECB):
                break
            if self.check(TokenType.BLADEFN):
                methods.append(self._parse_fn_def())
            else:
                raise self._error(
                    "Only bladeFN definitions allowed inside bladeGRP body"
                )
            self.skip_newlines()

        self.match(TokenType.DEDENT)
        self.skip_newlines()
        self.expect(TokenType.ECB)
        return BladeGRPDef(
            name=name_tok.value, methods=methods,
            line=grp_tok.line, col=grp_tok.col,
        )

    # -----------------------------------------------------------------------
    # 4.3 — Control flow statements  (Phase 4.3)
    # -----------------------------------------------------------------------

    def _parse_if_stmt(self) -> IfStmt:
        """Parse if expr +/ body ECB [elif expr +/ body ECB]* [else +/ body ECB]"""
        if_tok = self.consume()  # if
        condition = self.parse_expr(0)
        then_body = self._parse_block()
        self.skip_newlines()

        elif_clauses: list = []
        while self.check(TokenType.ELIF):
            self.consume()  # elif
            elif_cond = self.parse_expr(0)
            elif_body = self._parse_block()
            elif_clauses.append((elif_cond, elif_body))
            self.skip_newlines()

        else_body: Optional[list] = None
        if self.check(TokenType.ELSE):
            self.consume()  # else
            else_body = self._parse_block()

        return IfStmt(
            condition=condition, then_body=then_body,
            elif_clauses=elif_clauses, else_body=else_body,
            line=if_tok.line, col=if_tok.col,
        )

    def _parse_while_stmt(self) -> WhileStmt:
        """Parse while expr +/ body ECB"""
        while_tok = self.consume()  # while
        condition = self.parse_expr(0)
        body = self._parse_block()
        return WhileStmt(
            condition=condition, body=body,
            line=while_tok.line, col=while_tok.col,
        )

    def _parse_for_stmt(self) -> ForStmt:
        """Parse for name in expr +/ body ECB"""
        for_tok = self.consume()  # for
        var_tok = self.expect(TokenType.IDENT)
        self.expect(TokenType.IN)
        iterable = self.parse_expr(0)
        body = self._parse_block()
        return ForStmt(
            var_name=var_tok.value, iterable=iterable, body=body,
            line=for_tok.line, col=for_tok.col,
        )

    # -----------------------------------------------------------------------
    # 4.4 — Error handling and special statements  (Phase 4.4)
    # -----------------------------------------------------------------------

    def _parse_try_catch(self) -> TryCatch:
        """Parse try +/ body ECB catch name +/ body ECB"""
        try_tok = self.consume()  # try
        try_body = self._parse_block()
        self.skip_newlines()
        self.expect(TokenType.CATCH)
        catch_var_tok = self.expect(TokenType.IDENT)
        catch_body = self._parse_block()
        return TryCatch(
            try_body=try_body, catch_var=catch_var_tok.value, catch_body=catch_body,
            line=try_tok.line, col=try_tok.col,
        )

    def _parse_uselib(self) -> UselibStmt:
        """
        Parse uselib -modulename- or uselib -"./path"-
        Scans the module name between the two '-' delimiters.
        """
        use_tok = self.consume()  # uselib
        self.expect(TokenType.MINUS)
        # Module name: either a bare IDENT like "math" or a STRING like "./mymodule"
        if self.check(TokenType.STRING):
            mod_name = self.consume().value
        elif self.check(TokenType.IDENT):
            mod_name = self.consume().value
        else:
            raise self._error("Expected module name after uselib -")
        self.expect(TokenType.MINUS)
        return UselibStmt(module_name=mod_name, line=use_tok.line, col=use_tok.col)

    def _parse_raise(self) -> RaiseStmt:
        """Parse raise expr"""
        raise_tok = self.consume()  # raise
        message = self.parse_expr(0)
        return RaiseStmt(message=message, line=raise_tok.line, col=raise_tok.col)

    def _parse_return(self) -> ReturnStmt:
        """Parse return [expr]"""
        ret_tok = self.consume()  # return
        # If the next meaningful token ends the statement, return null
        value: object = NullLiteral(line=ret_tok.line, col=ret_tok.col)
        if not self.check(TokenType.NEWLINE, TokenType.EOF, TokenType.ECB, TokenType.DEDENT):
            value = self.parse_expr(0)
        return ReturnStmt(value=value, line=ret_tok.line, col=ret_tok.col)

    # -----------------------------------------------------------------------
    # 4.5 — Statement dispatcher and Program  (Phase 4.5)
    # -----------------------------------------------------------------------

    def parse_statement(self) -> Optional[object]:
        """
        Dispatch to the appropriate statement parser based on the current token.
        Skips NEWLINE, INDENT, DEDENT tokens (whitespace-only lines).
        Returns None for skippable tokens; callers should filter None out.
        """
        self.skip_newlines()
        tok = self.peek()

        # Skip structural whitespace tokens
        if tok.type in (TokenType.INDENT, TokenType.DEDENT, TokenType.EOF):
            if tok.type != TokenType.EOF:
                self.consume()
            return None

        if tok.type == TokenType.BLADEFN:
            return self._parse_fn_def()

        if tok.type == TokenType.CLASS:
            return self._parse_bladegrp_def()

        if tok.type == TokenType.IF:
            return self._parse_if_stmt()

        if tok.type == TokenType.WHILE:
            return self._parse_while_stmt()

        if tok.type == TokenType.FOR:
            return self._parse_for_stmt()

        if tok.type == TokenType.TRY:
            return self._parse_try_catch()

        if tok.type == TokenType.USELIB:
            return self._parse_uselib()

        if tok.type == TokenType.RAISE:
            return self._parse_raise()

        if tok.type == TokenType.RETURN:
            return self._parse_return()

        # Variable declaration, re-assignment, or expression statement
        return self._parse_assign_or_expr_stmt()

    def parse_program(self) -> Program:
        """
        Parse a full AxonBlade source file into a Program node.

        Week 4 full implementation: handles all statement types, skips
        whitespace tokens (NEWLINE, INDENT, DEDENT), and collects all
        top-level statements into Program.statements.
        """
        stmts: list = []
        self.skip_newlines()
        while not self.check(TokenType.EOF):
            stmt = self.parse_statement()
            if stmt is not None:
                stmts.append(stmt)
            self.skip_newlines()
        return Program(statements=stmts)


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

def parse_expr_source(source: str) -> object:
    """Lex and parse a single AxonBlade expression, returning the AST node."""
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse_expr(0)


def parse_source(source: str) -> Program:
    """Lex and parse AxonBlade source code, returning a Program AST node."""
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse_program()
