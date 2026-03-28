# AxonBlade — Detailed Phases

## Week 1 — Tokens + Lexer @done

### Phase 1.1: Token Type Specification 
- Define `TokenType` enum covering all 40+ token types
- Categorize tokens: keywords, operators, literals, delimiters, special tokens
- Document each token type with examples

### Phase 1.2: Token Dataclass & Lexer Architecture 
- Write `Token` dataclass with `type`, `value`, `line`, `col` fields
- Create `Lexer` class skeleton with initialization and position tracking
- Set up character-by-character scanning loop with line/column tracking

### Phase 1.3: Basic Token Recognition 
- Implement single-character token recognition (operators, delimiters, etc.)
- Add multi-character operator handling (`>>`, `+/`, `**`, `==`, `!=`, `<=`, `>=`, `|>`)
- Handle whitespace and maintain position tracking

### Phase 1.4: Advanced Scanning Features 
- Implement string scanning with `&{}` interpolation marker detection
- Implement color literal scanning (detect `-*`, scan name, validate `*-`)
- Handle `#type` annotation scanning inside parameter contexts
- Handle comments (`#` outside param context skips to EOL)

### Phase 1.5: Testing & Finalization 
- Write `tests/test_lexer.py` with 30+ test cases covering all token types
- Test edge cases: empty files, only comments, deeply nested indentation
- Emit `INDENT`/`DEDENT` tokens correctly
- Verify `ECB` is a keyword distinct from identifiers
- **Deliverable:** `core/lexer.py` + `core/tokens.py` fully tested

---

## Week 2 — AST Nodes + Pretty-writeer @done

### Phase 2.1: AST Node Hierarchy Design
- Define base AST node structure with `line` and `col` fields
- Design node types for literals: `NumberLiteral`, `StringLiteral`, `ColorLiteral`, `BoolLiteral`, `NullLiteral`
- Design collection nodes: `ListLiteral`, `DictLiteral`

### Phase 2.2: Expression Node Types
- Implement expression nodes: `BinaryOp`, `UnaryOp`, `CallExpr`, `DotAccess`, `IndexAccess`, `SliceAccess`, `PipelineExpr`
- Implement `FStringLiteral` with `parts: list` (alternating raw strings and AST expressions)
- Implement `Identifier` and `Param` dataclass (with optional type annotation)

### Phase 2.3: Statement Node Types
- Implement statement nodes: `AssignStmt`, `FnDef`, `BladeGRPDef`, `IfStmt`, `WhileStmt`, `ForStmt`, `TryCatch`, `RaiseStmt`, `ReturnStmt`, `UselibStmt`
- `FnDef` stores `params: list[Param]` where `Param` has `name` and optional `type_ann`
- Implement `Program` node as top-level container

### Phase 2.4: Pretty-writeer Implementation
- Write `pretty_write(node, indent=0) -> str` function for AST debugging
- Support nested indentation for readability
- Handle all node types with consistent formatting

### Phase 2.5: Node Validation & Testing
- Write tests for every node constructor ensuring fields are correct
- Test pretty-writeer output against expected formats
- Verify all field types and constraints
- **Deliverable:** `core/ast_nodes.py` with all node types and working pretty-writeer

---

## Week 3 — Expression Parser @done

### Phase 3.1: Parser Scaffold & Helpers
- Write `Parser` class with `tokens`, `pos` cursor, `peek()`, `consume()`, `expect()` helpers
- Implement error reporting with line/column information
- Set up main parsing dispatch method

### Phase 3.2: Literal & Grouping Expressions
- Parse number, string, f-string, color, bool, null literals
- Parse list literals `[a, b, c]` and dict literals `{k: v}`
- Parse grouped expressions `(expr)`

### Phase 3.3: Prefix & Postfix Operators
- Implement Pratt parsing (top-down operator precedence)
- Define precedence table: `**` > `* / %` > `+ -` > comparisons > `not` > `and` > `or`
- Parse unary minus and `not` operators
- Parse postfix operations: function calls, method calls, index/slice access

### Phase 3.4: Binary Operators & Complex Expressions
- Implement all binary operators with correct precedence
- Parse dot access `obj.method` and method calls `obj.method(args)`
- Parse index access `list[0]` and slices `list[1:3]`
- Parse function calls `foo(a, b)` and chained calls `foo(a)(b)`

### Phase 3.5: Pipeline Operator & Testing
- Implement pipeline operator `expr |> func`
- Write comprehensive expression tests verifying all types parse correctly
- Verify output via pretty-writeer
- **Deliverable:** All expressions parse correctly with proper precedence

---

## Week 4 — Statement Parser @in-progress

### Phase 4.1: Variable & Assignment Parsing
- Parse `>> name = expr` variable declarations
- Parse bare `name = expr` re-assignments
- Validate declaration vs. assignment contexts

### Phase 4.2: Function & Class Definitions
- Parse `bladeFN name(params) +/ body ECB` with param type annotations
- Parse nested `bladeFN` inside `bladeFN` (closures)
- Parse `bladeGRP Name +/ methods ECB`
- Validate proper block delimiters (`+/` and `ECB`)

### Phase 4.3: Control Flow Statements
- Parse `if expr +/ body ECB elif ... else +/ body ECB` with proper nesting
- Parse `while expr +/ body ECB`
- Parse `for name in expr +/ body ECB`

### Phase 4.4: Error Handling & Special Statements
- Parse `try +/ body ECB catch e +/ body ECB`
- Parse `uselib -modulename-` for module imports
- Parse `raise expr`
- Parse `return expr`

### Phase 4.5: Program & Test Coverage
- Parse top-level `Program` node (list of all statements)
- Write `tests/test_parser.py` with 40+ test cases covering all constructs
- Test nested structures, error recovery, edge cases
- **Deliverable:** Full parser handling every AxonBlade construct

---

## Week 5 — Environment + Core Evaluator @waiting

### Phase 5.1: Environment Chain Implementation
- Write `Environment` class with scope chain for nested lookups
- Implement `define(name, value)` for new variables
- Implement `get(name)` with chain lookup
- Implement `set(name, value)` for re-assignment with scope checking

### Phase 5.2: Evaluator Dispatch & Literals
- Write `Evaluator` class with `eval(node, env)` dispatch method
- Evaluate all literal nodes → Python values (numbers, strings, bools, null)
- Evaluate `ColorLiteral` → ANSI escape string
- Evaluate `Identifier` → `env.get(name)`

### Phase 5.3: Operators & Type System
- Evaluate `BinaryOp` with type checks and `AxonTypeError` on invalid combos
- Evaluate `UnaryOp` (`-`, `not`)
- Implement type checking for mixed operations
- Define and enforce AxonBlade type semantics

### Phase 5.4: Collections & Control Flow
- Evaluate `ListLiteral`, `DictLiteral`, `IndexAccess`, `SliceAccess`
- Evaluate `AssignStmt` — `define` for declarations, `set` for re-assignments
- Evaluate `IfStmt`, `WhileStmt`, `ForStmt`
- Handle control flow return values

### Phase 5.5: F-String Interpolation & Testing
- Evaluate `FStringLiteral` → concatenated string with interpolated parts
- Write comprehensive evaluator tests for basic operations
- Test variable scoping and environment chaining
- **Deliverable:** Basic programs with variables, math, colors, and control flow run correctly

---

## Week 6 — Functions, Closures, Classes, Built-ins @waiting

### Phase 6.1: Function Representation & Evaluation
- Implement `AxonFunction` class storing params, body, closure env
- Evaluate `FnDef` → create `AxonFunction`, define in current env
- Implement `ReturnException` for return statement unwinding
- Handle return value propagation

### Phase 6.2: Function Calls & Type Checking
- Evaluate `CallExpr` → create child env from closure env
- Bind arguments to parameters
- Enforce parameter count and type annotations
- Evaluate function body in child environment

### Phase 6.3: Closures & Nested Functions
- Implement closures — inner functions capture `env` at definition time, not call time
- Support nested `bladeFN` declarations
- Verify closure variables are mutable and shared

### Phase 6.4: Class System
- Implement `AxonClass`, `AxonInstance`, `BoundMethod`
- Evaluate `BladeGRPDef` → build method dict, define class in env
- Evaluate `CallExpr` on a class → create instance, call `init` if defined
- Evaluate `DotAccess` on instances → check fields then methods

### Phase 6.5: Pipeline & Built-ins Integration
- Evaluate `PipelineExpr` → rewrite `a |> f(b)` as `f(a, b)` at eval time
- Register all built-in functions in global env from `stdlib/builtins.py`
- Evaluate `FStringLiteral` fully with all expression types working
- **Deliverable:** Functions, closures, classes, type checking, built-ins all working

---

## Week 7 — Errors, Modules, REPL, CLI @waiting

### Phase 7.1: Error Classes & Formatting
- Write all error classes in `core/errors.py`
- Format error messages with line/col and source excerpt
- Implement stack trace generation for debugging

### Phase 7.2: Exception Handling
- Evaluate `TryCatch` — wrap body eval in Python try/except
- Bind error dict to catch variable
- Evaluate `RaiseStmt` — throw `AxonRuntimeError` with message

### Phase 7.3: Module System
- Implement module loader — run `.axb` file in fresh env
- Return namespace object from module evaluation
- Handle import statement evaluation
- Register `__builtin_*` hooks called by stdlib .axb files

### Phase 7.4: Standard Library
- Write `stdlib/math.axb` with math functions
- Write `stdlib/string.axb` with string utilities
- Integrate with built-in function system

### Phase 7.5: REPL, CLI & Integration Tests
- Write `repl.py` — readline loop with `>>` styled prompt
- Pretty-write return values, catch and display errors without crashing
- Write `main.py` — argparse CLI with `axb run file.axb`, `axb repl`, `axb version`
- Run `examples/fibonacci.axb` end-to-end integration test
- **Deliverable:** Full working language, any `.axb` file runs from terminal

---

## Week 8 — Grid Object + Terminal Renderer @waiting

### Phase 8.1: AxonGrid Class Architecture
- Write `grid/grid_object.py` — `AxonGrid` Python class with full tile state
- Implement tile storage (color, character)
- Implement width/height properties and constructor

### Phase 8.2: Grid State Manipulation
- Implement `set(x, y, color)` method
- Implement `get(x, y)` method
- Implement `fill(color)` method
- Implement `set_char(x, y, char)` and `get_char(x, y)`
- Implement `clear()` method

### Phase 8.3: Terminal Rendering
- Write `grid/renderer_term.py` — ANSI background color rendering
- Implement in-place re-render using cursor-up escape codes
- Map AxonBlade color names to ANSI escape codes
- Optimize render performance for repeated redraws

### Phase 8.4: Grid Interaction & Loop
- Implement `on_key(key, callback)` for keyboard input
- Implement `on_click(callback)` for mouse input
- Implement `loop(update_fn, interval_ms)` for game loop
- Implement `stop()` to exit loop

### Phase 8.5: Built-in Integration & Examples
- Register `grid(cols, rows)` as built-in returning `AxonGrid`
- Handle dot-method dispatch on `AxonGrid` in evaluator
- Write `examples/snake.axb` — playable Snake in ~40 lines
- Write `examples/life.axb` — Conway's Game of Life
- Write `tests/test_grid.py` covering all methods and rendering
- **Deliverable:** `grid()` fully usable, Snake and Life running in terminal

---

## Week 9 — Pyodide Bridge + Canvas Renderer @waiting

### Phase 9.1: Pyodide Environment Setup
- Set up Pyodide loading in HTML
- Load Python 3.11 WASM runtime
- Install axonblade package into Pyodide environment
- Handle async initialization and errors

### Phase 9.2: Bridge Implementation
- Write `playground/bridge.py` — `run(source: str) -> dict`
- Return dict with `{output, error, grid_state}`
- Capture stdout during execution
- Serialize grid state as JSON

### Phase 9.3: Grid State Serialization
- Serialize grid as JSON array of `{x, y, color_name, char}` objects
- Implement reverse mapping (Python → JSON)
- Handle color name standardization

### Phase 9.4: Canvas Grid Renderer
- Write `playground/canvas_grid.js` — reads grid state, draws on canvas
- Map AxonBlade color names to hex values for rendering
- Implement tile drawing with colors and characters
- Handle canvas resizing and scaling

### Phase 9.5: Round-trip Testing
- Test writing AxonBlade source in JS
- Run via Pyodide bridge
- Verify grid renders correctly on canvas
- Handle errors gracefully in browser
- **Deliverable:** AxonBlade runs in browser, grid renders on canvas

---

## Week 10 — Playground UI + Deploy @waiting

### Phase 10.1: CodeMirror 6 Integration
- Integrate CodeMirror 6 editor
- Create custom AxonBlade language definition
- Implement syntax highlighting for: `bladeFN`, `ECB`, `+/`, `>>`, color literals, string interpolation

### Phase 10.2: Editor Layout & Styling
- Build split-pane layout — editor (left 55%), output + canvas (right 45%)
- Implement responsive design
- Style editor with AxonBlade colors and theme
- Create output and canvas display panels

### Phase 10.3: Example Programs & Interactivity
- Add example program dropdown — Hello World, Fibonacci, Closures, Snake, Life
- Implement Run button + `Ctrl+Enter` keyboard shortcut
- Load examples into editor on selection
- Handle run button click and execution

### Phase 10.4: Error Display & Output
- Show runtime errors inline in editor with red underline
- Display errors in output panel with line/column info
- Show stdout output preserving ANSI-to-HTML color conversion
- Real-time error reporting as user types

### Phase 10.5: Sharing & Deployment
- Implement "Share" button that encodes source in URL hash
- Add URL hash decoding on page load to restore shared code
- Deploy to GitHub Pages (zero backend, fully static)
- Test across browsers and devices
- **Deliverable:** Live playground at `AI-Alon.github.io/axonblade`
