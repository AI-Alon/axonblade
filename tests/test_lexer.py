"""
Test suite for AxonBlade Lexer (Phase 1.3-1.5).
Tests all token types, edge cases, and proper token recognition.
"""

import pytest
from core.lexer import Lexer
from core.tokens import TokenType, Token


class TestSingleCharTokens:
    """Test single-character token recognition."""

    def test_arithmetic_operators(self):
        """Test basic arithmetic operators."""
        lexer = Lexer("+ - * / %")
        tokens = lexer.tokenize()

        assert tokens[0].type == TokenType.PLUS
        assert tokens[1].type == TokenType.MINUS
        assert tokens[2].type == TokenType.STAR
        assert tokens[3].type == TokenType.SLASH
        assert tokens[4].type == TokenType.PERCENT
        assert tokens[5].type == TokenType.EOF

    def test_delimiters(self):
        """Test delimiter tokens."""
        lexer = Lexer("( ) [ ] { } , : .")
        tokens = lexer.tokenize()

        expected = [
            TokenType.LPAREN, TokenType.RPAREN,
            TokenType.LBRACKET, TokenType.RBRACKET,
            TokenType.LBRACE, TokenType.RBRACE,
            TokenType.COMMA, TokenType.COLON, TokenType.DOT,
            TokenType.EOF
        ]
        assert [t.type for t in tokens] == expected

    def test_assignment_and_comparison_start(self):
        """Test = and comparison operators."""
        lexer = Lexer("= < > ~")
        tokens = lexer.tokenize()

        assert tokens[0].type == TokenType.ASSIGN
        assert tokens[1].type == TokenType.LT
        assert tokens[2].type == TokenType.GT
        assert tokens[3].type == TokenType.TILDE


class TestMultiCharOperators:
    """Test multi-character operator recognition."""

    def test_power_operator(self):
        """Test ** power operator."""
        lexer = Lexer("2 ** 3")
        tokens = lexer.tokenize()

        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == 2
        assert tokens[1].type == TokenType.POWER
        assert tokens[2].type == TokenType.NUMBER
        assert tokens[2].value == 3

    def test_comparison_operators(self):
        """Test ==, !=, <=, >= operators."""
        lexer = Lexer("== != <= >=")
        tokens = lexer.tokenize()

        expected = [
            TokenType.EQ, TokenType.NEQ, TokenType.LTE, TokenType.GTE,
            TokenType.EOF
        ]
        assert [t.type for t in tokens] == expected

    def test_vardecl_operator(self):
        """Test >> variable declaration operator."""
        lexer = Lexer(">> x = 10")
        tokens = lexer.tokenize()

        assert tokens[0].type == TokenType.VARDECL
        assert tokens[1].type == TokenType.IDENT
        assert tokens[1].value == "x"
        assert tokens[2].type == TokenType.ASSIGN
        assert tokens[3].type == TokenType.NUMBER

    def test_blockopen_operator(self):
        """Test +/ block open operator."""
        lexer = Lexer("+/ body")
        tokens = lexer.tokenize()

        assert tokens[0].type == TokenType.BLOCKOPEN
        assert tokens[1].type == TokenType.IDENT

    def test_pipe_operator(self):
        """Test |> pipeline operator."""
        lexer = Lexer("a |> f")
        tokens = lexer.tokenize()

        assert tokens[0].type == TokenType.IDENT
        assert tokens[1].type == TokenType.PIPE
        assert tokens[2].type == TokenType.IDENT


class TestNumbers:
    """Test numeric literal scanning."""

    def test_integers(self):
        """Test integer literal recognition."""
        lexer = Lexer("0 42 999 1000")
        tokens = lexer.tokenize()

        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == 0
        assert tokens[1].value == 42
        assert tokens[2].value == 999
        assert tokens[3].value == 1000

    def test_floats(self):
        """Test float literal recognition."""
        lexer = Lexer("3.14 0.5 99.99")
        tokens = lexer.tokenize()

        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == 3.14
        assert tokens[1].value == 0.5
        assert tokens[2].value == 99.99

    def test_number_in_expression(self):
        """Test number recognition in expressions."""
        lexer = Lexer("x = 123 + 456")
        tokens = lexer.tokenize()

        assert tokens[0].type == TokenType.IDENT
        assert tokens[1].type == TokenType.ASSIGN
        assert tokens[2].type == TokenType.NUMBER
        assert tokens[2].value == 123
        assert tokens[3].type == TokenType.PLUS
        assert tokens[4].type == TokenType.NUMBER
        assert tokens[4].value == 456


class TestKeywords:
    """Test keyword recognition."""

    def test_all_keywords(self):
        """Test recognition of all AxonBlade keywords."""
        keywords_to_test = [
            ("bladeFN", TokenType.BLADEFN),
            ("bladeGRP", TokenType.CLASS),
            ("return", TokenType.RETURN),
            ("if", TokenType.IF),
            ("elif", TokenType.ELIF),
            ("else", TokenType.ELSE),
            ("while", TokenType.WHILE),
            ("for", TokenType.FOR),
            ("in", TokenType.IN),
            ("try", TokenType.TRY),
            ("catch", TokenType.CATCH),
            ("raise", TokenType.RAISE),
            ("uselib", TokenType.USELIB),
            ("true", TokenType.TRUE),
            ("false", TokenType.FALSE),
            ("null", TokenType.NULL),
            ("-a", TokenType.AND),
            ("-o", TokenType.OR),
            ("-n", TokenType.NOT),
            ("blade", TokenType.SELF),
            ("ECB", TokenType.ECB),
        ]

        for keyword, expected_type in keywords_to_test:
            lexer = Lexer(keyword)
            tokens = lexer.tokenize()
            assert tokens[0].type == expected_type, f"Keyword {keyword} not recognized"

    def test_ecb_is_keyword_not_identifier(self):
        """Verify ECB is a keyword, not an identifier."""
        lexer = Lexer("ECB")
        tokens = lexer.tokenize()

        assert tokens[0].type == TokenType.ECB
        assert tokens[0].value is None  # Keywords don't store values


class TestIdentifiers:
    """Test identifier scanning."""

    def test_simple_identifiers(self):
        """Test basic identifier recognition."""
        lexer = Lexer("x foo bar_baz _private __dunder")
        tokens = lexer.tokenize()

        idents = [t for t in tokens if t.type == TokenType.IDENT]
        assert len(idents) == 5
        assert idents[0].value == "x"
        assert idents[1].value == "foo"
        assert idents[2].value == "bar_baz"
        assert idents[3].value == "_private"
        assert idents[4].value == "__dunder"

    def test_identifier_with_numbers(self):
        """Test identifiers containing numbers."""
        lexer = Lexer("var1 test2name x123y456")
        tokens = lexer.tokenize()

        idents = [t for t in tokens if t.type == TokenType.IDENT]
        assert idents[0].value == "var1"
        assert idents[1].value == "test2name"
        assert idents[2].value == "x123y456"


class TestStrings:
    """Test string literal scanning."""

    def test_simple_string(self):
        """Test basic string literal."""
        lexer = Lexer('"hello world"')
        tokens = lexer.tokenize()

        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == "hello world"

    def test_empty_string(self):
        """Test empty string."""
        lexer = Lexer('""')
        tokens = lexer.tokenize()

        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == ""

    def test_string_with_escapes(self):
        """Test string escape sequences."""
        lexer = Lexer('"line1\\nline2\\ttab"')
        tokens = lexer.tokenize()

        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == "line1\nline2\ttab"

    def test_string_with_quotes(self):
        """Test escaped quotes in string."""
        lexer = Lexer('"say \\"hello\\""')
        tokens = lexer.tokenize()

        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == 'say "hello"'

    def test_fstring_basic(self):
        """Test f-string with single interpolation."""
        lexer = Lexer('"Hello &{name}"')
        tokens = lexer.tokenize()

        assert tokens[0].type == TokenType.FSTRING
        assert isinstance(tokens[0].value, list)
        assert tokens[0].value[0] == ("str", "Hello ")
        assert tokens[0].value[1] == ("expr", "name")

    def test_fstring_multiple_interpolations(self):
        """Test f-string with multiple interpolations."""
        lexer = Lexer('"&{x} + &{y} = &{x + y}"')
        tokens = lexer.tokenize()

        assert tokens[0].type == TokenType.FSTRING
        parts = tokens[0].value
        # When string starts with interpolation, there's an empty string part first
        assert parts[0] == ("str", "")
        assert parts[1] == ("expr", "x")
        assert parts[2] == ("str", " + ")
        assert parts[3] == ("expr", "y")
        assert parts[4] == ("str", " = ")
        assert parts[5] == ("expr", "x + y")

    def test_fstring_f_prefix(self):
        """Test that f-prefix is not supported in AxonBlade.
        f"..." is tokenized as IDENT(f) followed by FSTRING, not a single FSTRING."""
        lexer = Lexer('f"value: &{val}"')
        tokens = lexer.tokenize()

        # f is just an identifier, not a string prefix
        assert tokens[0].type == TokenType.IDENT
        assert tokens[0].value == "f"
        # The string follows as a normal FSTRING
        assert tokens[1].type == TokenType.FSTRING
        assert tokens[1].value[0] == ("str", "value: ")
        assert tokens[1].value[1] == ("expr", "val")

    def test_unterminated_string(self):
        """Test error on unterminated string."""
        lexer = Lexer('"unclosed')

        with pytest.raises(SyntaxError):
            lexer.tokenize()


class TestColors:
    """Test color literal scanning."""

    def test_simple_color(self):
        """Test basic color literal."""
        lexer = Lexer("-*red*-")
        tokens = lexer.tokenize()

        assert tokens[0].type == TokenType.COLOR
        assert tokens[0].value == "red"

    def test_multiple_colors(self):
        """Test multiple color literals."""
        lexer = Lexer("-*blue*- -*cyan*- -*green*-")
        tokens = lexer.tokenize()

        colors = [t for t in tokens if t.type == TokenType.COLOR]
        assert len(colors) == 3
        assert colors[0].value == "blue"
        assert colors[1].value == "cyan"
        assert colors[2].value == "green"

    def test_valid_color_names(self):
        """Test all valid color names."""
        valid_colors = ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white", "reset"]
        for color in valid_colors:
            lexer = Lexer(f"-*{color}*-")
            tokens = lexer.tokenize()
            color_tokens = [t for t in tokens if t.type == TokenType.COLOR]
            assert len(color_tokens) == 1
            assert color_tokens[0].value == color

    def test_unterminated_color(self):
        """Test error on malformed color."""
        lexer = Lexer("-*red*")  # missing closing -

        with pytest.raises(SyntaxError):
            lexer.tokenize()

    def test_invalid_color_name(self):
        """Test error on unknown color name."""
        lexer = Lexer("-*invalid_color*-")

        with pytest.raises(SyntaxError) as exc_info:
            lexer.tokenize()
        assert "Unknown color" in str(exc_info.value)

    def test_color_missing_asterisk(self):
        """Test that -red*- is parsed as separate tokens, not a color."""
        # This should be tokenized as: MINUS, IDENT(red), STAR, MINUS
        # Not as an error, but as separate tokens
        lexer = Lexer("-red*-")
        tokens = lexer.tokenize()

        non_eof = [t for t in tokens if t.type != TokenType.EOF]
        assert non_eof[0].type == TokenType.MINUS
        assert non_eof[1].type == TokenType.IDENT
        assert non_eof[1].value == "red"
        assert non_eof[2].type == TokenType.STAR
        assert non_eof[3].type == TokenType.MINUS


class TestComments:
    """Test comment handling."""

    def test_line_comment(self):
        """Test comments skip to end of line."""
        lexer = Lexer("x = 10 # this is a comment")
        tokens = lexer.tokenize()

        # Should only get x, =, 10, EOF (comment ignored)
        non_eof = [t for t in tokens if t.type != TokenType.EOF]
        assert len(non_eof) == 3
        assert non_eof[0].type == TokenType.IDENT
        assert non_eof[1].type == TokenType.ASSIGN
        assert non_eof[2].type == TokenType.NUMBER

    def test_comment_ignores_tokens(self):
        """Test that comments ignore all following text."""
        lexer = Lexer(">> x = 5 # >> y = 10 is not parsed")
        tokens = lexer.tokenize()

        # Only x and 5 should be parsed
        non_eof = [t for t in tokens if t.type != TokenType.EOF]
        idents = [t for t in non_eof if t.type == TokenType.IDENT]
        assert len(idents) == 1
        assert idents[0].value == "x"

    def test_empty_comment_line(self):
        """Test line with only comment."""
        lexer = Lexer("# just a comment\nx = 1")
        tokens = lexer.tokenize()

        # First token should be IDENT (x) after the comment
        non_newline = [t for t in tokens if t.type != TokenType.NEWLINE and t.type != TokenType.EOF]
        assert non_newline[0].type == TokenType.IDENT


class TestIndentation:
    """Test indentation tracking and INDENT/DEDENT tokens."""

    def test_simple_indent(self):
        """Test single level indentation."""
        source = """+/
  x = 1
ECB"""
        lexer = Lexer(source)
        tokens = lexer.tokenize()

        token_types = [t.type for t in tokens]
        assert TokenType.INDENT in token_types
        assert TokenType.DEDENT in token_types

    def test_multiple_indents(self):
        """Test nested indentation levels."""
        source = """+/
  x = 1
  +/
    y = 2
  ECB
ECB"""
        lexer = Lexer(source)
        tokens = lexer.tokenize()

        token_types = [t.type for t in tokens]
        indent_count = token_types.count(TokenType.INDENT)
        dedent_count = token_types.count(TokenType.DEDENT)

        # Should have at least 2 indents and 2 dedents
        assert indent_count >= 2
        assert dedent_count >= 2

    def test_dedent_to_zero(self):
        """Test dedent back to original level."""
        source = """>> x = 1
  >> y = 2
>> z = 3"""
        lexer = Lexer(source)
        tokens = lexer.tokenize()

        token_types = [t.type for t in tokens]
        assert TokenType.INDENT in token_types
        assert TokenType.DEDENT in token_types


class TestWhitespaceHandling:
    """Test whitespace and newline handling."""

    def test_whitespace_between_tokens(self):
        """Test that whitespace between tokens is ignored."""
        lexer = Lexer("x   =   10")
        tokens = lexer.tokenize()

        non_eof = [t for t in tokens if t.type != TokenType.EOF]
        assert len(non_eof) == 3
        assert non_eof[0].type == TokenType.IDENT
        assert non_eof[1].type == TokenType.ASSIGN
        assert non_eof[2].type == TokenType.NUMBER

    def test_newline_tokens(self):
        """Test newline token emission."""
        lexer = Lexer("x = 1\ny = 2")
        tokens = lexer.tokenize()

        token_types = [t.type for t in tokens]
        assert TokenType.NEWLINE in token_types

    def test_tabs_as_indentation(self):
        """Test tab indentation (treated as 4 spaces)."""
        source = """+/
\tx = 1
ECB"""
        lexer = Lexer(source)
        tokens = lexer.tokenize()

        token_types = [t.type for t in tokens]
        assert TokenType.INDENT in token_types


class TestEmptyAndEdgeCases:
    """Test edge cases and empty input."""

    def test_empty_file(self):
        """Test lexing empty file."""
        lexer = Lexer("")
        tokens = lexer.tokenize()

        assert len(tokens) == 1
        assert tokens[0].type == TokenType.EOF

    def test_only_whitespace(self):
        """Test file with only whitespace."""
        lexer = Lexer("   \n  \n  ")
        tokens = lexer.tokenize()

        # Should only have NEWLINE and EOF
        assert all(t.type in (TokenType.NEWLINE, TokenType.EOF) for t in tokens)

    def test_only_comments(self):
        """Test file with only comments."""
        lexer = Lexer("# comment\n# another comment")
        tokens = lexer.tokenize()

        non_eof = [t for t in tokens if t.type != TokenType.EOF and t.type != TokenType.NEWLINE]
        assert len(non_eof) == 0

    def test_deeply_nested_indentation(self):
        """Test deeply nested indentation levels."""
        source = """+/
  +/
    +/
      x = 1
    ECB
  ECB
ECB"""
        lexer = Lexer(source)
        tokens = lexer.tokenize()

        token_types = [t.type for t in tokens]
        indent_count = token_types.count(TokenType.INDENT)

        # Should have 3 indents
        assert indent_count >= 3


class TestComplexPrograms:
    """Test realistic program fragments."""

    def test_simple_assignment(self):
        """Test simple variable declaration."""
        lexer = Lexer(">> x = 42")
        tokens = lexer.tokenize()

        assert tokens[0].type == TokenType.VARDECL
        assert tokens[1].type == TokenType.IDENT
        assert tokens[1].value == "x"
        assert tokens[2].type == TokenType.ASSIGN
        assert tokens[3].type == TokenType.NUMBER

    def test_function_definition(self):
        """Test function definition syntax."""
        source = """bladeFN add(a, b) +/
  return a + b
ECB"""
        lexer = Lexer(source)
        tokens = lexer.tokenize()

        token_types = [t.type for t in tokens]
        assert TokenType.BLADEFN in token_types
        assert TokenType.BLOCKOPEN in token_types
        assert TokenType.RETURN in token_types
        assert TokenType.ECB in token_types

    def test_if_statement(self):
        """Test if statement syntax."""
        source = """if x > 0 +/
  y = x
else +/
  y = 0
ECB"""
        lexer = Lexer(source)
        tokens = lexer.tokenize()

        token_types = [t.type for t in tokens]
        assert TokenType.IF in token_types
        assert TokenType.GT in token_types
        assert TokenType.BLOCKOPEN in token_types
        assert TokenType.ELSE in token_types
        assert TokenType.ECB in token_types

    def test_for_loop(self):
        """Test for loop syntax."""
        source = """for i in list +/
  print(i)
ECB"""
        lexer = Lexer(source)
        tokens = lexer.tokenize()

        token_types = [t.type for t in tokens]
        assert TokenType.FOR in token_types
        assert TokenType.IN in token_types
        assert TokenType.BLOCKOPEN in token_types

    def test_pipeline_operation(self):
        """Test pipeline operator."""
        lexer = Lexer("result = data |> transform")
        tokens = lexer.tokenize()

        token_types = [t.type for t in tokens]
        assert TokenType.PIPE in token_types

    def test_color_in_expression(self):
        """Test color literal in expression."""
        lexer = Lexer("grid.set(x, y, -*red*-)")
        tokens = lexer.tokenize()

        colors = [t for t in tokens if t.type == TokenType.COLOR]
        assert len(colors) == 1
        assert colors[0].value == "red"

    def test_interpolated_string_in_call(self):
        """Test f-string in function call."""
        lexer = Lexer('print(f"Value: &{x}")')
        tokens = lexer.tokenize()

        fstrings = [t for t in tokens if t.type == TokenType.FSTRING]
        assert len(fstrings) == 1


class TestTokenProperties:
    """Test token line and column tracking."""

    def test_token_line_numbers(self):
        """Test that tokens track correct line numbers."""
        source = """x = 1
y = 2
z = 3"""
        lexer = Lexer(source)
        tokens = lexer.tokenize()

        idents = [t for t in tokens if t.type == TokenType.IDENT]
        assert idents[0].line == 1  # x
        assert idents[1].line == 2  # y
        assert idents[2].line == 3  # z

    def test_token_column_tracking(self):
        """Test that tokens track column positions."""
        lexer = Lexer("  x = 10")
        tokens = lexer.tokenize()

        ident_token = next(t for t in tokens if t.type == TokenType.IDENT)
        # x should be at column 3 (after 2 spaces)
        assert ident_token.col == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
