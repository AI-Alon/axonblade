from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class TokenType(Enum):
    """Token type enumeration covering all AxonBlade tokens (40+ types)."""

    # Keywords (21)
    BLADEFN = auto()
    CLASS = auto()
    RETURN = auto()
    IF = auto()
    ELIF = auto()
    ELSE = auto()
    WHILE = auto()
    FOR = auto()
    IN = auto()
    TRY = auto()
    CATCH = auto()
    RAISE = auto()
    USELIB = auto()
    TRUE = auto()
    FALSE = auto()
    NULL = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    SELF = auto()
    ECB = auto()

    # Structural tokens
    VARDECL = auto()  # >>
    BLOCKOPEN = auto()  # +/
    NEWLINE = auto()
    INDENT = auto()
    DEDENT = auto()
    EOF = auto()

    # Single-character operators
    PLUS = auto()  # +
    MINUS = auto()  # -
    STAR = auto()  # *
    SLASH = auto()  # /
    PERCENT = auto()  # %
    ASSIGN = auto()  # =
    DOT = auto()  # .
    COMMA = auto()  # ,
    COLON = auto()  # :
    LPAREN = auto()  # (
    RPAREN = auto()  # )
    LBRACKET = auto()  # [
    RBRACKET = auto()  # ]
    LBRACE = auto()  # {
    RBRACE = auto()  # }

    # Multi-character operators
    POWER = auto()  # **
    EQ = auto()  # ==
    NEQ = auto()  # !=
    LT = auto()  # <
    GT = auto()  # >
    LTE = auto()  # <=
    GTE = auto()  # >=
    TILDE = auto()  # ~
    PIPE = auto()  # |>
    HASH = auto()  # # (in param context only)

    # Literal tokens
    NUMBER = auto()
    STRING = auto()
    FSTRING = auto()
    COLOR = auto()
    IDENT = auto()
    TYPE_ANN = auto()


# Map string lexemes to TokenType for keyword lookup
KEYWORDS = {
    "bladeFN": TokenType.BLADEFN,
    "bladeGRP": TokenType.CLASS,
    "return": TokenType.RETURN,
    "if": TokenType.IF,
    "elif": TokenType.ELIF,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
    "for": TokenType.FOR,
    "in": TokenType.IN,
    "try": TokenType.TRY,
    "catch": TokenType.CATCH,
    "raise": TokenType.RAISE,
    "uselib": TokenType.USELIB,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "null": TokenType.NULL,
    "-a": TokenType.AND,
    "-o": TokenType.OR,
    "-n": TokenType.NOT,
    "blade": TokenType.SELF,
    "ECB": TokenType.ECB,
}

# Known color set from ProjectPlan.md section 10.2
VALID_COLORS = {
    "black",
    "red",
    "green",
    "yellow",
    "blue",
    "magenta",
    "cyan",
    "white",
    "reset",
}


@dataclass
class Token:
    """Represents a single token in the source code."""

    type: TokenType
    value: Any
    line: int
    col: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, {self.line}, {self.col})"
