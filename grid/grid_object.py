"""
grid/grid_object.py — AxonGrid Python class (Week 8, Phases 8.1-8.4).

Implements the AxonBlade grid primitive per ProjectPlan.md §9.5.

AxonGrid stores a 2D array of tiles, each tile having:
  - color: ANSI background escape string
  - char:  single character displayed on the tile

The game loop (loop/stop/on_key/on_click) uses non-blocking keyboard
input via select + termios on Unix, or msvcrt on Windows.
"""

from __future__ import annotations

import sys
import time


# ---------------------------------------------------------------------------
# §9.3 — ANSI background color map
# ---------------------------------------------------------------------------

ANSI_BG_COLORS: dict[str, str] = {
    "black":   "\033[40m",
    "red":     "\033[41m",
    "green":   "\033[42m",
    "yellow":  "\033[43m",
    "blue":    "\033[44m",
    "magenta": "\033[45m",
    "cyan":    "\033[46m",
    "white":   "\033[47m",
    "reset":   "\033[0m",
}

# Map foreground ANSI codes → background codes (for color literals used in grid)
_FG_TO_BG: dict[str, str] = {
    "\033[30m": "\033[40m",
    "\033[31m": "\033[41m",
    "\033[32m": "\033[42m",
    "\033[33m": "\033[43m",
    "\033[34m": "\033[44m",
    "\033[35m": "\033[45m",
    "\033[36m": "\033[46m",
    "\033[37m": "\033[47m",
    "\033[0m":  "\033[0m",
}

_DEFAULT_BG = "\033[40m"  # black background
_RESET = "\033[0m"


def _to_bg(color: str) -> str:
    """Convert a foreground ANSI code or bg code to a bg code for grid tiles."""
    if color in _FG_TO_BG:
        return _FG_TO_BG[color]
    # Already a background code or unknown — return as-is
    return color


# ---------------------------------------------------------------------------
# §8.1–8.4 — AxonGrid class
# ---------------------------------------------------------------------------


class AxonGrid:
    """
    AxonBlade grid primitive.  Stores colored tiles with optional characters.
    Renders to the terminal using ANSI background colors.
    """

    def __init__(self, cols: int, rows: int) -> None:
        self.cols = cols
        self.rows = rows
        self._tiles: list[list[dict]] = [
            [{"color": _DEFAULT_BG, "char": " "} for _ in range(cols)]
            for _ in range(rows)
        ]
        self._key_handlers: dict[str, object] = {}
        self._click_handler: object = None
        self._running: bool = False
        self._first_render: bool = True

    # -----------------------------------------------------------------------
    # §8.2 — Grid state manipulation
    # -----------------------------------------------------------------------

    def set(self, x: int, y: int, color: str) -> None:
        """Set the background color of tile at (x, y)."""
        if 0 <= x < self.cols and 0 <= y < self.rows:
            self._tiles[y][x]["color"] = _to_bg(color)

    def get(self, x: int, y: int) -> str:
        """Get the color of tile at (x, y)."""
        if 0 <= x < self.cols and 0 <= y < self.rows:
            return self._tiles[y][x]["color"]
        return _DEFAULT_BG

    def fill(self, color: str) -> None:
        """Set all tiles to the given color and reset their characters."""
        bg = _to_bg(color)
        for row in self._tiles:
            for tile in row:
                tile["color"] = bg
                tile["char"] = " "

    def set_char(self, x: int, y: int, char: str) -> None:
        """Set the character displayed on tile at (x, y)."""
        if 0 <= x < self.cols and 0 <= y < self.rows:
            self._tiles[y][x]["char"] = (char[0] if char else " ")

    def get_char(self, x: int, y: int) -> str:
        """Get the character on tile at (x, y)."""
        if 0 <= x < self.cols and 0 <= y < self.rows:
            return self._tiles[y][x]["char"]
        return " "

    def clear(self) -> None:
        """Reset all tiles to default (black background, space char)."""
        for row in self._tiles:
            for tile in row:
                tile["color"] = _DEFAULT_BG
                tile["char"] = " "

    def width(self) -> int:
        """Return the column count."""
        return self.cols

    def height(self) -> int:
        """Return the row count."""
        return self.rows

    # -----------------------------------------------------------------------
    # §8.3 — Terminal rendering
    # -----------------------------------------------------------------------

    def render(self) -> None:
        """
        Render the grid to the terminal using ANSI background colors.
        Each tile is 2 characters wide.  After the first render, uses
        cursor-up to redraw in place.
        """
        from grid.renderer_term import render_grid
        render_grid(self, in_place=not self._first_render)
        self._first_render = False

    # -----------------------------------------------------------------------
    # §8.4 — Input and game loop
    # -----------------------------------------------------------------------

    def on_key(self, key: str, callback: object) -> None:
        """Register a callback for a key press."""
        self._key_handlers[key] = callback

    def on_click(self, callback: object) -> None:
        """Register a callback for mouse clicks (reserved for future use)."""
        self._click_handler = callback

    def loop(self, update_fn: object, fps: int = 10) -> None:
        """
        Start the game loop at *fps* frames per second (§9.4):
          1. Call update_fn()
          2. Render the grid
          3. Handle keyboard input (non-blocking)
          4. Sleep 1/fps seconds
        """
        from core.evaluator import Evaluator
        ev = Evaluator()
        self._running = True
        interval = 1.0 / max(fps, 1)

        try:
            _setup_terminal()
            while self._running:
                # 1. Update
                _call_fn(ev, update_fn, [])
                # 2. Render
                self.render()
                # 3. Handle input
                key = _read_key_nonblocking()
                if key is not None:
                    handler = self._key_handlers.get(key)
                    if handler is not None:
                        _call_fn(ev, handler, [])
                # 4. Sleep
                time.sleep(interval)
        finally:
            _restore_terminal()

    def stop(self) -> None:
        """Stop the game loop."""
        self._running = False

    def __repr__(self) -> str:
        return f"<AxonGrid {self.cols}x{self.rows}>"


# ---------------------------------------------------------------------------
# Terminal raw-mode helpers  (§8.4)
# ---------------------------------------------------------------------------

_old_termios = None


def _setup_terminal() -> None:
    """Put stdin into raw mode for non-blocking single-char reads (Unix)."""
    global _old_termios
    if sys.platform == "win32":
        return
    try:
        import termios
        import tty
        fd = sys.stdin.fileno()
        _old_termios = termios.tcgetattr(fd)
        tty.setraw(fd)
    except Exception:
        pass


def _restore_terminal() -> None:
    """Restore original terminal settings."""
    global _old_termios
    if sys.platform == "win32" or _old_termios is None:
        return
    try:
        import termios
        fd = sys.stdin.fileno()
        termios.tcsetattr(fd, termios.TCSADRAIN, _old_termios)
        _old_termios = None
    except Exception:
        pass


def _read_key_nonblocking() -> str | None:
    """
    Read a single keypress without blocking.
    Returns the character string, or None if no key was pressed.
    """
    if sys.platform == "win32":
        import msvcrt  # type: ignore[import]
        if msvcrt.kbhit():
            ch = msvcrt.getch()
            return ch.decode("utf-8", errors="ignore")
        return None
    else:
        import select
        r, _, _ = select.select([sys.stdin], [], [], 0)
        if r:
            return sys.stdin.read(1)
        return None


def _call_fn(ev: object, fn: object, args: list) -> object:
    """Call an AxonBlade function or Python callable, ignoring None."""
    if fn is None:
        return None
    from core.evaluator import AxonFunction, BoundMethod, ReturnException
    if isinstance(fn, AxonFunction):
        try:
            ev.eval_body(fn.body, fn.closure_env.child())  # type: ignore
        except ReturnException as ret:
            return ret.value
        return None
    if isinstance(fn, BoundMethod):
        call_env = fn.fn.closure_env.child()
        call_env.define("blade", fn.instance)
        try:
            ev.eval_body(fn.fn.body, call_env)  # type: ignore
        except ReturnException as ret:
            return ret.value
        return None
    if callable(fn):
        return fn(*args)
    return None
