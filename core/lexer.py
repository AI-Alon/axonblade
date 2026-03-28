from core.tokens import Token, TokenType, KEYWORDS, VALID_COLORS
from typing import Optional


class Lexer:
    """Character-by-character lexer for AxonBlade source code."""

    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens = []
        self.indent_stack = [0]
        self.in_params = False  # True while inside a bladeFN parameter list
        self._after_bladefn = False  # True after bladeFN, waiting for opening (
        self.at_line_start = True  # track if we're at start of logical line

    def peek(self, offset: int = 0) -> Optional[str]:
        """Look ahead at character without consuming. Returns None if at EOF."""
        idx = self.pos + offset
        return self.source[idx] if idx < len(self.source) else None

    def advance(self) -> Optional[str]:
        """Consume and return current character, updating line/col."""
        if self.at_end():
            return None
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
            self.at_line_start = True
        else:
            self.col += 1
        return ch

    def match(self, expected: str) -> bool:
        """
        If next characters match expected string, consume and return True.
        Otherwise return False without consuming.
        """
        for i, ch in enumerate(expected):
            if self.peek(i) != ch:
                return False
        for _ in expected:
            self.advance()
        return True

    def add_token(self, token_type: TokenType, value: any = None) -> None:
        """Create and append a token to the tokens list."""
        token = Token(type=token_type, value=value, line=self.line, col=self.col)
        self.tokens.append(token)

    def at_end(self) -> bool:
        """Check if we've reached the end of source."""
        return self.pos >= len(self.source)

    def _handle_indent(self, spaces: int) -> None:
        """
        Compare indentation level to stack.
        Emit INDENT if deeper, one or more DEDENT(s) if shallower.
        """
        current_level = self.indent_stack[-1]

        if spaces > current_level:
            self.indent_stack.append(spaces)
            self.add_token(TokenType.INDENT)
        elif spaces < current_level:
            self._emit_dedents_to(spaces)

    def _emit_dedents_to(self, level: int) -> None:
        """Pop indent stack and emit DEDENT tokens until reaching level."""
        while len(self.indent_stack) > 1 and self.indent_stack[-1] > level:
            self.indent_stack.pop()
            self.add_token(TokenType.DEDENT)

    def scan_token(self) -> None:
        """
        Dispatch token scanning based on current character.
        Handles indentation, whitespace, newlines, and other tokens.
        """
        # Handle indentation at start of logical line
        if self.at_line_start and not self.at_end():
            ch = self.peek()
            if ch == " " or ch == "\t":
                spaces = 0
                while self.peek() in (" ", "\t"):
                    if self.peek() == " ":
                        spaces += 1
                    else:
                        spaces += 4  # treat tab as 4 spaces
                    self.advance()
                # Check if line is non-empty after indentation
                if self.peek() and self.peek() not in ("\n", "#"):
                    self._handle_indent(spaces)
                self.at_line_start = False
                return
            elif ch != "\n":
                # Non-indented non-empty line: emit any pending DEDENTs back to level 0
                self._handle_indent(0)
                self.at_line_start = False

        if self.at_end():
            return

        ch = self.peek()
        self.at_line_start = False

        # Whitespace (skip, but not newlines)
        if ch in (" ", "\t"):
            self.advance()
            return

        # Newline
        if ch == "\n":
            self.advance()
            self.add_token(TokenType.NEWLINE)
            self.at_line_start = True
            return

        # Comments (# outside param context)
        if ch == "#" and not self.in_params:
            # Multi-line comment: #/ ... /#
            if self.peek(1) == "/":
                self.advance()  # consume #
                self.advance()  # consume /
                while not self.at_end():
                    if self.peek() == "/" and self.peek(1) == "#":
                        self.advance()  # consume /
                        self.advance()  # consume #
                        break
                    self.advance()
                return
            # Single-line comment: skip to end of line
            while self.peek() and self.peek() != "\n":
                self.advance()
            return

        # String literals (double-quoted with &{} interpolation support)
        if ch == '"':
            self._scan_string()
            return

        # Color literals (-*name*-)
        if ch == "-" and self.peek(1) == "*":
            self._scan_color()
            return

        # Logical keyword operators: -n (not), -a (and), -o (or)
        if ch == "-" and self.peek(1) in ("n", "a", "o"):
            two = ch + self.peek(1)
            if two in ("-n", "-a", "-o"):
                # Only emit as keyword if NOT followed by alphanumeric/underscore
                # (so -name or -other identifiers are not consumed)
                after = self.peek(2)
                if after is None or not (after.isalnum() or after == "_"):
                    from core.tokens import KEYWORDS
                    tok_col = self.col
                    self.advance()  # -
                    self.advance()  # n/a/o
                    self.tokens.append(Token(KEYWORDS[two], two, self.line, tok_col))
                    return

        # Numbers
        if ch.isdigit():
            self._scan_number()
            return

        # Identifiers and keywords
        if ch.isalpha() or ch == "_":
            self._scan_identifier()
            return

        # Multi-character operators and single-char tokens
        self._scan_operator()

    def _scan_operator(self) -> None:
        """Scan operators and single-character delimiters."""
        ch = self.peek()
        tok_col = self.col  # save col before any advance

        # Two-character operators
        next_ch = self.peek(1)

        if ch == ">" and next_ch == ">":
            self.advance()
            self.advance()
            self.tokens.append(Token(TokenType.VARDECL, None, self.line, tok_col))
            return

        if ch == "+" and next_ch == "/":
            self.advance()
            self.advance()
            self.tokens.append(Token(TokenType.BLOCKOPEN, None, self.line, tok_col))
            return

        if ch == "*" and next_ch == "*":
            self.advance()
            self.advance()
            self.tokens.append(Token(TokenType.POWER, None, self.line, tok_col))
            return

        if ch == "=" and next_ch == "=":
            self.advance()
            self.advance()
            self.tokens.append(Token(TokenType.EQ, None, self.line, tok_col))
            return

        if ch == "!" and next_ch == "=":
            self.advance()
            self.advance()
            self.tokens.append(Token(TokenType.NEQ, None, self.line, tok_col))
            return

        if ch == "<" and next_ch == "=":
            self.advance()
            self.advance()
            self.tokens.append(Token(TokenType.LTE, None, self.line, tok_col))
            return

        if ch == ">" and next_ch == "=":
            self.advance()
            self.advance()
            self.tokens.append(Token(TokenType.GTE, None, self.line, tok_col))
            return

        if ch == "|" and next_ch == ">":
            self.advance()
            self.advance()
            self.tokens.append(Token(TokenType.PIPE, None, self.line, tok_col))
            return

        # Single-character tokens
        single_char_tokens = {
            "+": TokenType.PLUS,
            "-": TokenType.MINUS,
            "*": TokenType.STAR,
            "/": TokenType.SLASH,
            "%": TokenType.PERCENT,
            "=": TokenType.ASSIGN,
            ".": TokenType.DOT,
            ",": TokenType.COMMA,
            ":": TokenType.COLON,
            "(": TokenType.LPAREN,
            ")": TokenType.RPAREN,
            "[": TokenType.LBRACKET,
            "]": TokenType.RBRACKET,
            "{": TokenType.LBRACE,
            "}": TokenType.RBRACE,
            "<": TokenType.LT,
            ">": TokenType.GT,
            "~": TokenType.TILDE,
        }

        if ch in single_char_tokens:
            tok_type = single_char_tokens[ch]
            self.advance()
            # Track in_params: set True on ( immediately after bladeFN, False on )
            if tok_type == TokenType.LPAREN and self._after_bladefn:
                self.in_params = True
                self._after_bladefn = False
            elif tok_type == TokenType.RPAREN:
                self.in_params = False
            self.tokens.append(Token(tok_type, None, self.line, tok_col))
            return

        # Unknown character
        raise SyntaxError(
            f"Unexpected character '{ch}' at line {self.line}, col {self.col}"
        )

    def _scan_number(self) -> None:
        """Scan numeric literal (integers and floats)."""
        start_pos = self.pos
        start_col = self.col

        # Consume digits
        while self.peek() and self.peek().isdigit():
            self.advance()

        # Check for decimal point
        if self.peek() == "." and self.peek(1) and self.peek(1).isdigit():
            self.advance()  # consume '.'
            while self.peek() and self.peek().isdigit():
                self.advance()

        value_str = self.source[start_pos : self.pos]
        value = float(value_str) if "." in value_str else int(value_str)
        token = Token(type=TokenType.NUMBER, value=value, line=self.line, col=start_col)
        self.tokens.append(token)

    def _scan_string(self) -> None:
        """
        Scan string literal with &{} interpolation support.
        Returns FSTRING if contains interpolation, otherwise STRING.
        """
        start_col = self.col
        start_line = self.line
        self.advance()  # consume opening "

        parts = []  # For f-strings: alternating strings and expressions
        current_str = ""
        is_fstring = False

        while self.peek() and self.peek() != '"':
            if self.peek() == "\\":
                # Escape sequence
                self.advance()
                if self.peek():
                    escaped_char = self.peek()
                    if escaped_char == "n":
                        current_str += "\n"
                    elif escaped_char == "t":
                        current_str += "\t"
                    elif escaped_char == "r":
                        current_str += "\r"
                    elif escaped_char == "\\":
                        current_str += "\\"
                    elif escaped_char == '"':
                        current_str += '"'
                    else:
                        current_str += escaped_char
                    self.advance()
            elif self.peek() == "&" and self.peek(1) == "{":
                # Interpolation marker
                is_fstring = True
                # Save current string part
                if current_str or not parts:
                    parts.append(("str", current_str))
                current_str = ""
                self.advance()  # consume &
                self.advance()  # consume {

                # Scan expression until }
                expr_tokens = []
                brace_depth = 1
                while brace_depth > 0 and self.peek():
                    if self.peek() == "{":
                        brace_depth += 1
                    elif self.peek() == "}":
                        brace_depth -= 1
                        if brace_depth == 0:
                            break

                    # Collect raw expression text
                    expr_tokens.append(self.peek())
                    self.advance()

                if self.peek() == "}":
                    self.advance()  # consume closing }
                    expr_str = "".join(expr_tokens).strip()
                    parts.append(("expr", expr_str))
            else:
                current_str += self.peek()
                self.advance()

        if self.peek() == '"':
            self.advance()  # consume closing "
        else:
            raise SyntaxError(
                f"Unterminated string starting at line {start_line}, col {start_col}"
            )

        # Finalize parts
        if is_fstring:
            if current_str or not parts:
                parts.append(("str", current_str))
            token = Token(
                type=TokenType.FSTRING, value=parts, line=start_line, col=start_col
            )
        else:
            value = current_str
            token = Token(
                type=TokenType.STRING, value=value, line=start_line, col=start_col
            )

        self.tokens.append(token)

    def _scan_color(self) -> None:
        """
        Scan color literal: -*name*-
        Validates the format and the color name against the known color set.
        """
        start_col = self.col
        start_line = self.line
        self.advance()  # consume -
        self.advance()  # consume *

        color_name = ""
        while self.peek() and self.peek() != "*":
            color_name += self.peek()
            self.advance()

        if self.peek() != "*":
            raise SyntaxError(
                f"Unterminated color literal at line {start_line}, col {start_col}"
            )
        self.advance()  # consume *

        if self.peek() != "-":
            raise SyntaxError(
                f"Color literal must end with *- at line {start_line}, col {start_col}"
            )
        self.advance()  # consume -

        # Validate color name against known color set (ProjectPlan.md 10.2)
        if color_name not in VALID_COLORS:
            raise SyntaxError(
                f"Unknown color '{color_name}' at line {start_line}, col {start_col}. "
                f"Valid colors: {', '.join(sorted(VALID_COLORS))}"
            )

        token = Token(
            type=TokenType.COLOR, value=color_name, line=start_line, col=start_col
        )
        self.tokens.append(token)

    def _scan_identifier(self) -> None:
        """
        Scan identifier or keyword.
        AxonBlade has no f-string prefix — all strings support &{} interpolation.
        """
        start_pos = self.pos
        start_col = self.col

        # Regular identifier
        while self.peek() and (self.peek().isalnum() or self.peek() == "_"):
            self.advance()

        value = self.source[start_pos : self.pos]

        # Check for #type annotation (only in param context)
        token_type = KEYWORDS.get(value, TokenType.IDENT)

        # Track when bladeFN is seen so ( opens param context
        if token_type == TokenType.BLADEFN:
            self._after_bladefn = True

        # If inside params and next is #, scan as type annotation
        if self.peek() == "#" and token_type == TokenType.IDENT and self.in_params:
            self.advance()  # consume #
            # Scan type name
            type_start = self.pos
            while self.peek() and (self.peek().isalnum() or self.peek() == "_"):
                self.advance()
            type_name = self.source[type_start : self.pos]

            token = Token(
                type=TokenType.TYPE_ANN,
                value=(value, type_name),
                line=self.line,
                col=start_col,
            )
            self.tokens.append(token)
            return

        token = Token(
            type=token_type, value=value if token_type == TokenType.IDENT else None, line=self.line, col=start_col
        )
        self.tokens.append(token)

    def tokenize(self) -> list[Token]:
        """Scan entire source and return list of tokens."""
        while not self.at_end():
            self.scan_token()

        # Emit pending DEDENTs then EOF
        self._emit_dedents_to(0)
        self.add_token(TokenType.EOF)
        return self.tokens
