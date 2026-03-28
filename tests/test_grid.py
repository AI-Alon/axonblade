"""
tests/test_grid.py — Week 8 grid tests (Phases 8.1-8.5).

Covers:
  - AxonGrid construction and properties
  - set/get/fill/set_char/get_char/clear
  - Terminal renderer output
  - on_key callback registration
  - Built-in grid() function
  - Evaluator integration: grid used from AxonBlade programs
"""

import pytest

from grid.grid_object import AxonGrid, ANSI_BG_COLORS, _DEFAULT_BG, _to_bg
from grid.renderer_term import render_grid


# ---------------------------------------------------------------------------
# Phase 8.1 — AxonGrid construction
# ---------------------------------------------------------------------------

class TestGridConstruction:
    def test_basic_construction(self):
        g = AxonGrid(10, 5)
        assert g.cols == 10
        assert g.rows == 5

    def test_width_height(self):
        g = AxonGrid(20, 15)
        assert g.width() == 20
        assert g.height() == 15

    def test_tile_defaults(self):
        g = AxonGrid(3, 3)
        # Default tile: black background, space char
        assert g.get(0, 0) == _DEFAULT_BG
        assert g.get_char(0, 0) == " "

    def test_single_tile_grid(self):
        g = AxonGrid(1, 1)
        assert g.width() == 1
        assert g.height() == 1

    def test_repr(self):
        g = AxonGrid(10, 5)
        assert "10x5" in repr(g)


# ---------------------------------------------------------------------------
# Phase 8.2 — Grid state manipulation
# ---------------------------------------------------------------------------

class TestGridSet:
    def test_set_color(self):
        g = AxonGrid(5, 5)
        red_bg = "\033[41m"
        g.set(2, 3, red_bg)
        assert g.get(2, 3) == red_bg

    def test_set_fg_color_converts_to_bg(self):
        g = AxonGrid(5, 5)
        # Foreground red → background red
        g.set(0, 0, "\033[31m")
        assert g.get(0, 0) == "\033[41m"

    def test_set_out_of_bounds_ignored(self):
        g = AxonGrid(5, 5)
        # Should not raise
        g.set(10, 10, "\033[41m")
        # Grid unchanged
        assert g.get(0, 0) == _DEFAULT_BG

    def test_fill(self):
        g = AxonGrid(3, 3)
        g.fill("\033[34m")  # blue foreground → blue background
        for y in range(3):
            for x in range(3):
                assert g.get(x, y) == "\033[44m"

    def test_fill_with_bg_color(self):
        g = AxonGrid(4, 4)
        g.fill("\033[42m")
        assert g.get(2, 2) == "\033[42m"

    def test_set_char(self):
        g = AxonGrid(5, 5)
        g.set_char(2, 2, "@")
        assert g.get_char(2, 2) == "@"

    def test_set_char_takes_first_char(self):
        g = AxonGrid(5, 5)
        g.set_char(0, 0, "AB")
        assert g.get_char(0, 0) == "A"

    def test_set_char_empty_string(self):
        g = AxonGrid(5, 5)
        g.set_char(0, 0, "")
        assert g.get_char(0, 0) == " "

    def test_get_out_of_bounds_returns_default(self):
        g = AxonGrid(5, 5)
        assert g.get(99, 99) == _DEFAULT_BG

    def test_clear(self):
        g = AxonGrid(3, 3)
        g.fill("\033[41m")
        g.set_char(1, 1, "X")
        g.clear()
        for y in range(3):
            for x in range(3):
                assert g.get(x, y) == _DEFAULT_BG
                assert g.get_char(x, y) == " "


# ---------------------------------------------------------------------------
# Phase 8.3 — Terminal rendering
# ---------------------------------------------------------------------------

class TestTerminalRenderer:
    def test_render_produces_output(self, capsys):
        g = AxonGrid(3, 2)
        render_grid(g)
        captured = capsys.readouterr()
        assert len(captured.out) > 0

    def test_render_contains_newlines(self, capsys):
        g = AxonGrid(3, 2)
        render_grid(g)
        captured = capsys.readouterr()
        # Should have one newline per row
        assert captured.out.count("\n") >= 2

    def test_render_contains_reset(self, capsys):
        g = AxonGrid(2, 2)
        render_grid(g)
        captured = capsys.readouterr()
        assert "\033[0m" in captured.out

    def test_render_inplace_uses_cursor_up(self, capsys):
        g = AxonGrid(2, 2)
        render_grid(g, in_place=True)
        captured = capsys.readouterr()
        # Cursor-up sequence
        assert "\033[" in captured.out
        assert "A" in captured.out

    def test_render_colored_tile(self, capsys):
        g = AxonGrid(2, 2)
        g.set(0, 0, "\033[41m")  # red background
        render_grid(g)
        captured = capsys.readouterr()
        assert "\033[41m" in captured.out

    def test_render_with_char(self, capsys):
        g = AxonGrid(2, 2)
        g.set_char(0, 0, "X")
        render_grid(g)
        captured = capsys.readouterr()
        assert "X" in captured.out


# ---------------------------------------------------------------------------
# Phase 8.4 — Input and game loop
# ---------------------------------------------------------------------------

class TestGridInput:
    def test_on_key_registers(self):
        g = AxonGrid(5, 5)
        callback = lambda: None
        g.on_key("q", callback)
        assert g._key_handlers["q"] is callback

    def test_on_click_registers(self):
        g = AxonGrid(5, 5)
        callback = lambda: None
        g.on_click(callback)
        assert g._click_handler is callback

    def test_stop_sets_running_false(self):
        g = AxonGrid(5, 5)
        g._running = True
        g.stop()
        assert g._running is False


# ---------------------------------------------------------------------------
# Phase 8.5 — Built-in integration and color mapping
# ---------------------------------------------------------------------------

class TestColorMapping:
    def test_fg_to_bg_red(self):
        assert _to_bg("\033[31m") == "\033[41m"

    def test_fg_to_bg_green(self):
        assert _to_bg("\033[32m") == "\033[42m"

    def test_fg_to_bg_blue(self):
        assert _to_bg("\033[34m") == "\033[44m"

    def test_bg_color_passthrough(self):
        assert _to_bg("\033[41m") == "\033[41m"

    def test_ansi_bg_colors_map(self):
        assert ANSI_BG_COLORS["red"] == "\033[41m"
        assert ANSI_BG_COLORS["green"] == "\033[42m"
        assert ANSI_BG_COLORS["black"] == "\033[40m"


class TestGridBuiltin:
    def test_grid_builtin_creates_axongrid(self):
        from stdlib.builtins import _builtin_grid
        g = _builtin_grid(10, 5)
        assert isinstance(g, AxonGrid)
        assert g.cols == 10
        assert g.rows == 5

    def test_grid_builtin_type_check(self):
        from stdlib.builtins import _builtin_grid
        from core.errors import AxonTypeError
        with pytest.raises(AxonTypeError):
            _builtin_grid(3.5, 5)

    def test_grid_from_axonblade(self):
        from core.parser import parse_source
        from core.evaluator import Evaluator
        from stdlib.builtins import build_global_env
        src = ">> g = grid(5, 5)\n"
        ev = Evaluator()
        env = build_global_env()
        prog = parse_source(src)
        ev.eval(prog, env)
        g = env.get("g")
        assert isinstance(g, AxonGrid)
        assert g.cols == 5
        assert g.rows == 5

    def test_grid_set_from_axonblade(self):
        from core.parser import parse_source
        from core.evaluator import Evaluator
        from stdlib.builtins import build_global_env
        src = (
            ">> g = grid(5, 5)\n"
            "g.set(2, 2, -*red*-)\n"
        )
        ev = Evaluator()
        env = build_global_env()
        prog = parse_source(src)
        ev.eval(prog, env)
        g = env.get("g")
        assert g.get(2, 2) == "\033[41m"

    def test_grid_fill_from_axonblade(self):
        from core.parser import parse_source
        from core.evaluator import Evaluator
        from stdlib.builtins import build_global_env
        src = (
            ">> g = grid(3, 3)\n"
            "g.fill(-*blue*-)\n"
        )
        ev = Evaluator()
        env = build_global_env()
        prog = parse_source(src)
        ev.eval(prog, env)
        g = env.get("g")
        assert g.get(1, 1) == "\033[44m"

    def test_grid_width_height_from_axonblade(self):
        from core.parser import parse_source
        from core.evaluator import Evaluator
        from stdlib.builtins import build_global_env
        src = (
            ">> g = grid(8, 6)\n"
            ">> w = g.width()\n"
            ">> h = g.height()\n"
        )
        ev = Evaluator()
        env = build_global_env()
        prog = parse_source(src)
        ev.eval(prog, env)
        assert env.get("w") == 8
        assert env.get("h") == 6
