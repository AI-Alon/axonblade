/**
 * playground/canvas_grid.js — HTML Canvas grid renderer (Week 9, Phase 9.4).
 *
 * Reads grid state from the Pyodide bridge and draws coloured tiles on an
 * HTML <canvas> element.
 *
 * Usage:
 *   renderGrid(gridState, canvas, tileSize)
 *
 * gridState is the array of {x, y, color_name, char} objects returned by
 * playground/bridge.py.
 */

// §9.4 — AxonBlade color name → CSS hex
const AXON_COLORS = {
  black:   "#1a1a1a",
  red:     "#cc0000",
  green:   "#00aa00",
  yellow:  "#ccaa00",
  blue:    "#0055cc",
  magenta: "#aa00aa",
  cyan:    "#00aacc",
  white:   "#dddddd",
  reset:   "#1a1a1a",
};

const DEFAULT_TILE_SIZE = 20;   // pixels per tile side
const CHAR_COLOR = "#ffffff";   // character foreground colour

/**
 * Render a grid state onto a canvas element.
 *
 * @param {Array<{x:number, y:number, color_name:string, char:string}>} gridState
 * @param {HTMLCanvasElement} canvas
 * @param {number} [tileSize] - optional pixel size of each tile (default 20)
 */
function renderGrid(gridState, canvas, tileSize = DEFAULT_TILE_SIZE) {
  if (!gridState || gridState.length === 0) return;

  // Determine grid dimensions from the data
  const maxX = Math.max(...gridState.map(t => t.x)) + 1;
  const maxY = Math.max(...gridState.map(t => t.y)) + 1;

  // Resize canvas to fit the grid
  canvas.width  = maxX * tileSize;
  canvas.height = maxY * tileSize;

  const ctx = canvas.getContext("2d");

  for (const tile of gridState) {
    const px = tile.x * tileSize;
    const py = tile.y * tileSize;

    // Background fill
    ctx.fillStyle = AXON_COLORS[tile.color_name] ?? AXON_COLORS.black;
    ctx.fillRect(px, py, tileSize, tileSize);

    // Character (if non-space)
    const ch = tile.char ?? " ";
    if (ch !== " ") {
      ctx.fillStyle = CHAR_COLOR;
      ctx.font = `${Math.floor(tileSize * 0.75)}px monospace`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(ch, px + tileSize / 2, py + tileSize / 2);
    }
  }
}

/**
 * Clear the canvas to a solid background colour.
 *
 * @param {HTMLCanvasElement} canvas
 * @param {string} [color] - CSS colour (default dark background)
 */
function clearCanvas(canvas, color = AXON_COLORS.black) {
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = color;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
}
