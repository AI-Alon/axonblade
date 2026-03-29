# AxonBlade — Project Plan

> **Version:** 1.0  
> **File extension:** `.axb`  
> **Implementation language:** Python 3.11+  
> **Type:** Tree-walk interpreted scripting language  
> **Paradigm:** Imperative, dynamically typed, first-class functions  
> **Unique features:** Native ANSI grid primitive, color literals, bladeFN syntax  

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Language Design Philosophy](#2-language-design-philosophy)
3. [Syntax Reference](#3-syntax-reference)
4. [Token Specification](#4-token-specification)
5. [AST Node Specification](#5-ast-node-specification)
6. [Evaluator Specification](#6-evaluator-specification)
7. [Type System](#7-type-system)
8. [Standard Library](#8-standard-library)
9. [Grid System](#9-grid-system)
10. [ANSI Color Literals](#10-ansi-color-literals)
11. [Error System](#11-error-system)
12. [Module System](#12-module-system)
13. [Project File Structure](#13-project-file-structure)
14. [Week-by-Week Roadmap](#14-week-by-week-roadmap)
15. [Testing Strategy](#15-testing-strategy)
16. [Website](#16-website)
17. [Example Programs](#17-example-programs)
18. [Future Roadmap (Post v1)](#18-future-roadmap-post-v1)

---

## 1. Project Overview

AxonBlade is a custom interpreted scripting language implemented entirely in Python. It is designed to be genuinely usable, visually distinctive, and educational — demonstrating mastery of language theory including lexing, parsing, AST construction, and tree-walk evaluation.

The language distinguishes itself from existing scripting languages through three core innovations:

- **Unique syntax** — `bladeFN`, `+/`, `ECB`, `>>`, `&{}`, and `#type` make AxonBlade immediately recognizable and unlike any existing language.
- **Native color literals** — `-*red*-`, `-*cyan*-` etc. are first-class values that resolve to ANSI escape codes, usable anywhere a string is usable.
- **Built-in grid primitive** — `grid(cols, rows)` creates a visual tile grid rendered directly in the terminal using ANSI background colors, enabling games, simulations, and visual programs in just a few lines.

### Goals

| Goal | Description |
|------|-------------|
| Learn | Deeply understand how interpreters work — lexing, parsing, evaluation, environments, closures |
| Build | Produce a real, runnable programming language with a complete feature set |
| Portfolio | Ship a full website at `AI-Alon.github.io/axonblade` with docs and examples — a flagship portfolio piece |

### Non-goals (v1)

- Compiling to bytecode or native machine code
- Static type checking (types are checked at runtime only)
- Inheritance or mixins in the bladeGRP system
- Concurrency or async/await
- A package manager

---

## 2. Language Design Philosophy

**AxonBlade is opinionated.** Every syntax decision was made to make the language feel like its own thing, not a Python clone.

- Blocks always open with `+/` and close with `ECB` (End Code Block) — there are no braces and no colon-only delimiters.
- Variable declaration uses `>>` — it is explicit and visually distinct from assignment in other languages.
- Functions are always declared with `bladeFN` — there is no `def`, `func`, or `function` keyword.
- String interpolation uses `&{}` — no `f` prefix needed, all strings support it.
- Type annotations use `#` — lightweight, optional, and enforced at runtime.
- Color is a first-class concept — `-*red*-` is a literal value, not a function call or import.

**AxonBlade is practical.** Despite its unique syntax, it is a fully featured language capable of real programs. The grid system means a developer can write a Snake game or Game of Life in under 50 lines.

**AxonBlade is readable.** `ECB` closing blocks makes it immediately clear where nested structures end, unlike languages where you count closing braces or rely on indentation alone.

---

## 3. Syntax Reference

### 3.1 Variables

```axb
>> name = "AxonBlade"
>> version = 1
>> pi = 3.14159
>> active = true
>> nothing = null
```

Re-assignment does not require `>>`:

```axb
>> x = 10
x = 20
```

### 3.2 String Interpolation

All strings support `&{}` interpolation. Any expression is valid inside the braces.

```axb
>> name = "Alon"
>> age = 11
write("Hello &{name}, you are &{age} years old")
write("Next year you will be &{age + 1}")
write("Type: &{type(name)}")
```

### 3.3 Functions

All functions are declared with `bladeFN`. Blocks open with `+/` and close with `ECB`.

```axb
bladeFN greet(name) +/
    write("Hello &{name}")
ECB

bladeFN add(a, b) +/
    return a + b
ECB
```

#### Type-annotated parameters

The `#` annotation is optional. If present, the evaluator enforces the type at call time.

```axb
bladeFN greet(name#str, age#int) +/
    write("Hello &{name}, you are &{age}")
ECB
```

Supported annotation types: `str`, `int`, `float`, `bool`, `list`, `dict`, `grid`, `fn`, `any`

#### First-class functions

```axb
bladeFN apply(func#fn, value) +/
    return func(value)
ECB

bladeFN double(x#int) +/
    return x * 2
ECB

write(apply(double, 5))
```

#### Closures

```axb
bladeFN make_counter() +/
    >> count = 0
    bladeFN increment() +/
        count = count + 1
        return count
    ECB
    return increment
ECB

>> counter = make_counter()
write(counter())
write(counter())
write(counter())
```

### 3.4 Control Flow

#### if / elif / else

```axb
>> score = 85

if score >= 90 +/
    write("A grade")
ECB
elif score >= 75 +/
    write("B grade")
ECB
else +/
    write("C grade")
ECB
```

#### while loop

```axb
>> i = 0
while i < 5 +/
    write("i = &{i}")
    i = i + 1
ECB
```

#### for loop

```axb
>> nums = [1, 2, 3, 4, 5]
for n in nums +/
    write(n)
ECB
```

### 3.5 Lists

```axb
>> items = [10, 20, 30, 40]
write(items~0~)
write(items~1:3~)
items.append(50)
write(len(items))

for item in items +/
    write(item)
ECB
```

### 3.6 Dicts

```axb
>> player = {name: "Ada", hp: 100, level: 5}
write(player~"name"~)
player~"hp"~ = 90
write(player.keys())
```

### 3.7 Classes (bladeGRP)

```axb
bladeGRP Animal +/
    bladeFN init(blade, name#str, sound#str) +/
        blade.name = name
        blade.sound = sound
    ECB

    bladeFN speak(blade) +/
        write("&{blade.name} says &{blade.sound}")
    ECB

    bladeFN describe(blade) +/
        return "I am &{blade.name}"
    ECB
ECB

>> dog = Animal("Rex", "woof")
dog.speak()
write(dog.describe())
```

### 3.8 Error Handling

```axb
try +/
    >> x = 10 / 0
ECB
catch e +/
    write("Caught error: &{e}")
ECB
```

Raising errors manually:

```axb
bladeFN divide(a#int, b#int) +/
    if b == 0 +/
        raise "Cannot divide by zero"
    ECB
    return a / b
ECB
```

### 3.9 Imports

```axb
uselib -math-
>> r = math.sqrt(25)

uselib -"./mymodule"-
mymodule.hello()
```

### 3.10 Color Literals

```axb
write(-*red*- + "Error occurred" + -*reset*-)
write(-*green*- + "Success!" + -*reset*-)
write(-*cyan*- + "Info: &{message}" + -*reset*-)
```

### 3.11 Grid

```axb
>> g = grid(10, 10)
g.fill(-*black*-)
g.set(5, 5, -*red*-)
g.set_char(5, 5, "@")
g.on_key("q", quit_fn)
g.loop(update_fn, 10)
```

---

## 4. Token Specification

All token types the lexer must recognize:

### 4.1 Keyword Tokens

| Token | Lexeme | Notes |
|-------|--------|-------|
| `BLADEFN` | `bladeFN` | Function declaration keyword |
| `CLASS` | `bladeGRP` | Class declaration keyword |
| `RETURN` | `return` | Return statement |
| `IF` | `if` | Conditional |
| `ELIF` | `elif` | Else-if branch |
| `ELSE` | `else` | Else branch |
| `WHILE` | `while` | While loop |
| `FOR` | `for` | For loop |
| `IN` | `in` | For-in operator |
| `TRY` | `try` | Try block |
| `CATCH` | `catch` | Catch block |
| `RAISE` | `raise` | Raise error |
| `USELIB` | `uselib` | Module import |
| `RETURN` | `return` | Return value |
| `TRUE` | `true` | Boolean true |
| `FALSE` | `false` | Boolean false |
| `NULL` | `null` | Null value |
| `AND` | `-a` | Logical and |
| `OR` | `-o` | Logical or |
| `NOT` | `-n` | Logical not |
| `SELF` | `blade` | Instance reference |

### 4.2 Structural Tokens

| Token | Lexeme | Notes |
|-------|--------|-------|
| `VARDECL` | `>>` | Variable declaration |
| `BLOCKOPEN` | `+/` | Opens an indented block |
| `ECB` | `ECB` | Closes an indented block |
| `INDENT` | (generated) | Indentation increase |
| `DEDENT` | (generated) | Indentation decrease |
| `NEWLINE` | `\n` | Line ending |
| `EOF` | (generated) | End of file |

### 4.3 Operator Tokens

| Token | Lexeme |
|-------|--------|
| `PLUS` | `+` |
| `MINUS` | `-` |
| `STAR` | `*` |
| `SLASH` | `/` |
| `PERCENT` | `%` |
| `POWER` | `**` |
| `EQ` | `==` |
| `NEQ` | `!=` |
| `LT` | `<` |
| `GT` | `>` |
| `LTE` | `<=` |
| `GTE` | `>=` |
| `ASSIGN` | `=` |
| `DOT` | `.` |
| `COMMA` | `,` |
| `COLON` | `:` |
| `TILDE` | `~` |
| `LPAREN` | `(` |
| `RPAREN` | `)` |
| `LBRACKET` | `[` |
| `RBRACKET` | `]` |
| `LBRACE` | `{` |
| `RBRACE` | `}` |
| `PIPE` | `\|>` |
| `HASH` | `#` (in param context) |

### 4.4 Literal Tokens

| Token | Example | Notes |
|-------|---------|-------|
| `NUMBER` | `42`, `3.14` | Int or float |
| `STRING` | `"hello"` | Supports `&{}` segments |
| `FSTRING` | `"Hi &{name}"` | Detected during string lex |
| `COLOR` | `-*red*-` | Scanned between `-*` and `*-` |
| `IDENT` | `foo`, `my_var` | Identifier |
| `TYPE_ANN` | `#str` | After param name in bladeFN |

### 4.5 Lexer Implementation Notes

- Indentation tracking uses a stack of indent levels. On each new non-empty line, compare the leading spaces to the top of the stack. Emit `INDENT` if deeper, `DEDENT` (possibly multiple) if shallower.
- Color tokens: when the lexer sees `-*`, scan forward until `*-`. Validate the name against the known color set. Emit `COLOR` with the name as value.
- Type annotations: when inside a `bladeFN` parameter list, after an `IDENT`, if the next char is `#`, consume `#` + the type name as a `TYPE_ANN` token.
- F-strings: scan a full string, detect all `&{...}` segments, emit an `FSTRING` token whose value is a list of alternating string parts and expression source strings.
- Comments: `#` at the start of a line or after whitespace (not inside a param list) begins a comment. Consume until end of line, emit nothing.
- Multi-line comments: `#/ ... /#` — consume everything between the delimiters, may span multiple lines. Not valid inside param lists.

---

## 5. AST Node Specification

All nodes are Python `@dataclass` classes. Every node carries `line: int` and `col: int` for error reporting.

### 5.1 Literal Nodes

```python
@dataclass
bladeGRP NumberLiteral:
    value: float
    line: int; col: int

@dataclass
bladeGRP StringLiteral:
    value: str
    line: int; col: int

@dataclass
bladeGRP FStringLiteral:
    # parts: alternating str and Expr nodes
    parts: list
    line: int; col: int

@dataclass
bladeGRP ColorLiteral:
    name: str   # "red", "blue", etc.
    line: int; col: int

@dataclass
bladeGRP BoolLiteral:
    value: bool
    line: int; col: int

@dataclass
bladeGRP NullLiteral:
    line: int; col: int

@dataclass
bladeGRP ListLiteral:
    elements: list  # list of Expr nodes
    line: int; col: int

@dataclass
bladeGRP DictLiteral:
    pairs: list  # list of (key_expr, val_expr) tuples
    line: int; col: int
```

### 5.2 Expression Nodes

```python
@dataclass
bladeGRP Identifier:
    name: str
    line: int; col: int

@dataclass
bladeGRP BinaryOp:
    left: object
    op: str       # "+", "-", "*", "/", "**", "%", "==", "!=", "<", ">", "<=", ">="
    right: object
    line: int; col: int

@dataclass
bladeGRP UnaryOp:
    op: str       # "-", "-n"
    operand: object
    line: int; col: int

@dataclass
bladeGRP CallExpr:
    callee: object     # Identifier or DotAccess
    args: list
    line: int; col: int

@dataclass
bladeGRP DotAccess:
    obj: object
    attr: str
    line: int; col: int

@dataclass
bladeGRP IndexAccess:
    obj: object
    index: object
    line: int; col: int

@dataclass
bladeGRP SliceAccess:
    obj: object
    start: object
    end: object
    line: int; col: int

@dataclass
bladeGRP PipelineExpr:
    left: object
    right: object   # must be a CallExpr; left is inserted as first arg
    line: int; col: int
```

### 5.3 Statement Nodes

```python
@dataclass
bladeGRP AssignStmt:
    name: str
    value: object
    is_declaration: bool   # True if >> was used
    line: int; col: int

@dataclass
bladeGRP Param:
    name: str
    type_ann: str | None   # "str", "int", etc. or None

@dataclass
bladeGRP FnDef:
    name: str
    params: list   # list of Param
    body: list     # list of statement nodes
    line: int; col: int

@dataclass
bladeGRP ReturnStmt:
    value: object
    line: int; col: int

@dataclass
bladeGRP RaiseStmt:
    message: object
    line: int; col: int

@dataclass
bladeGRP IfStmt:
    condition: object
    then_body: list
    elif_clauses: list   # list of (condition, body) tuples
    else_body: list | None
    line: int; col: int

@dataclass
bladeGRP WhileStmt:
    condition: object
    body: list
    line: int; col: int

@dataclass
bladeGRP ForStmt:
    var_name: str
    iterable: object
    body: list
    line: int; col: int

@dataclass
bladeGRP BladeGRPDef:
    name: str
    methods: list   # list of FnDef nodes
    line: int; col: int

@dataclass
bladeGRP TryCatch:
    try_body: list
    catch_var: str
    catch_body: list
    line: int; col: int

@dataclass
bladeGRP UselibStmt:
    module_name: str    # "math" or "./myfile"
    line: int; col: int

@dataclass
bladeGRP Program:
    statements: list
```

---

## 6. Evaluator Specification

The evaluator is a tree-walking interpreter. It recursively visits every AST node and returns a Python value.

### 6.1 Environment

```python
bladeGRP Environment:
    bladeFN __init__(self, parent=None):
        self.store = {}
        self.parent = parent

    bladeFN get(self, name):
        if name in self.store:
            return self.store[name]
        if self.parent:
            return self.parent.get(name)
        raise AxonNameError(f"Undefined variable '{name}'")

    bladeFN set(self, name, value):
        # Find the scope that owns this name
        if name in self.store:
            self.store[name] = value
        elif self.parent:
            self.parent.set(name, value)
        else:
            raise AxonNameError(f"Undefined variable '{name}'")

    bladeFN define(self, name, value):
        self.store[name] = value
```

### 6.2 AxonBlade Value Types

| AxonBlade type | Python representation |
|----------------|-----------------------|
| `int` / `float` | `int` / `float` |
| `str` | `str` |
| `bool` | `bool` |
| `null` | `None` |
| `list` | `list` |
| `dict` | `dict` |
| `fn` | `AxonFunction` instance |
| `bladeGRP` | `AxonBladeGRP` instance |
| `object` | `AxonInstance` instance |
| `grid` | `AxonGrid` instance |
| `color` | `str` (ANSI escape code) |

### 6.3 AxonFunction

```python
bladeGRP AxonFunction:
    bladeFN __init__(self, name, params, body, closure_env):
        self.name = name
        self.params = params         # list of Param
        self.body = body             # list of statement nodes
        self.closure_env = closure_env  # captured environment
```

When called:
1. Create a new `Environment` with `closure_env` as parent (not the calling env — this is what makes closures work).
2. Bind each argument to its parameter name in the new env.
3. Check type annotations — if `param.type_ann` is set, verify `type(arg)` matches, raise `AxonTypeError` on mismatch.
4. Evaluate the body statements one by one.
5. Catch `ReturnException` to get the return value.

### 6.4 Return Mechanism

Return statements unwind the call stack using a Python exception:

```python
bladeGRP ReturnException(Exception):
    bladeFN __init__(self, value):
        self.value = value
```

In `eval_return_stmt`: raise `ReturnException(eval(node.value, env))`.  
In `eval_call_expr`: wrap body eval in `try/except ReturnException as r: return r.value`.

### 6.5 bladeGRP System

```python
bladeGRP AxonBladeGRP:
    bladeFN __init__(self, name, methods):
        self.name = name
        self.methods = methods   # dict of name -> AxonFunction

bladeGRP AxonInstance:
    bladeFN __init__(self, klass):
        self.klass = klass
        self.fields = {}

    bladeFN get(self, name):
        if name in self.fields:
            return self.fields[name]
        if name in self.klass.methods:
            return BoundMethod(self, self.klass.methods[name])
        raise AxonNameError(f"No attribute '{name}'")
```

`init` is called automatically when `Animal("Rex", "woof")` (bladeGRP instance) is evaluated.

### 6.6 Color Literal Evaluation

```python
ANSI_COLORS = {
    "red":     "\033[31m",
    "green":   "\033[32m",
    "yellow":  "\033[33m",
    "blue":    "\033[34m",
    "magenta": "\033[35m",
    "cyan":    "\033[36m",
    "white":   "\033[37m",
    "black":   "\033[30m",
    "reset":   "\033[0m",
}

bladeFN eval_color_literal(node):
    return ANSI_COLORS[node.name]
```

### 6.7 F-String Evaluation

```python
bladeFN eval_fstring(node, env):
    result = ""
    for part in node.parts:
        if isinstance(part, str):
            result += part
        else:
            result += str(eval(part, env))
    return result
```

---

## 7. Type System

AxonBlade is dynamically typed. Types are associated with values, not variables. Type annotations on function parameters are optional but enforced at runtime when present.

### 7.1 Type Names

| Annotation | Matches Python type |
|------------|---------------------|
| `str` | `str` |
| `int` | `int` |
| `float` | `float` or `int` |
| `bool` | `bool` |
| `list` | `list` |
| `dict` | `dict` |
| `fn` | `AxonFunction` |
| `grid` | `AxonGrid` |
| `any` | anything (skips check) |

### 7.2 Runtime Type Checking

```python
bladeFN check_type(value, annotation, param_name, line):
    if annotation is None or annotation == "any":
        return
    type_map = {
        "str": str, "int": int, "bool": bool,
        "list": list, "dict": dict,
        "fn": AxonFunction, "grid": AxonGrid,
        "float": (float, int),
    }
    expected = type_map.get(annotation)
    if expected and not isinstance(value, expected):
        raise AxonTypeError(
            f"Parameter '{param_name}' expected {annotation}, "
            f"got {type(value).__name__}", line
        )
```

### 7.3 Type Coercion Rules

AxonBlade does NOT silently coerce types. The following all raise `AxonTypeError`:

- `"hello" + 42` — cannot add str and int
- `true + 1` — cannot add bool and int
- `[1,2,3] * "x"` — cannot multiply list and str

Use explicit conversion: `str(42)`, `int("42")`, `float("3.14")`

---

## 8. Standard Library

### 8.1 Built-in Functions (Python-implemented)

| Function | Signature | Description |
|----------|-----------|-------------|
| `write` | `write(value)` | Print to stdout with newline |
| `len` | `len(collection)` | Length of list, dict, or string |
| `type` | `type(value)` | Returns type name as string |
| `range` | `range(n)` or `range(start, end)` | Returns a list of integers |
| `input` | `input(prompt#str)` | Reads a line from stdin |
| `str` | `str(value)` | Convert to string |
| `int` | `int(value)` | Convert to integer |
| `float` | `float(value)` | Convert to float |
| `bool` | `bool(value)` | Convert to boolean |
| `grid` | `grid(cols#int, rows#int)` | Create a new Grid object |

### 8.2 math.axb

Written in AxonBlade itself:

```axb
bladeFN sqrt(n#float) +/
    return __builtin_sqrt(n)
ECB

bladeFN abs(n) +/
    if n < 0 +/
        return n * -1
    ECB
    return n
ECB

bladeFN floor(n#float) +/
    return __builtin_floor(n)
ECB

bladeFN ceil(n#float) +/
    return __builtin_ceil(n)
ECB

bladeFN pow(base, exp) +/
    return base ** exp
ECB

bladeFN max(a, b) +/
    if a > b +/
        return a
    ECB
    return b
ECB

bladeFN min(a, b) +/
    if a < b +/
        return a
    ECB
    return b
ECB
```

### 8.3 string.axb

```axb
bladeFN upper(s#str) +/
    return __builtin_upper(s)
ECB

bladeFN lower(s#str) +/
    return __builtin_lower(s)
ECB

bladeFN split(s#str, delim#str) +/
    return __builtin_split(s, delim)
ECB

bladeFN join(parts#list, delim#str) +/
    return __builtin_join(parts, delim)
ECB

bladeFN strip(s#str) +/
    return __builtin_strip(s)
ECB

bladeFN contains(s#str, sub#str) +/
    return __builtin_contains(s, sub)
ECB

bladeFN replace(s#str, old#str, new#str) +/
    return __builtin_replace(s, old, new)
ECB
```

---

## 9. Grid System

The grid is the most unique feature of AxonBlade. It is a native visual primitive — calling `grid(cols, rows)` creates an `AxonGrid` Python object that is a first-class AxonBlade value.

### 9.1 Grid Object Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `set` | `g.set(x#int, y#int, color)` | Set background color of tile at (x, y) |
| `get` | `g.get(x#int, y#int)` | Get color value of tile at (x, y) |
| `fill` | `g.fill(color)` | Set all tiles to color |
| `set_char` | `g.set_char(x#int, y#int, char#str)` | Set character displayed on tile |
| `get_char` | `g.get_char(x#int, y#int)` | Get character on tile |
| `clear` | `g.clear()` | Reset all tiles to default |
| `render` | `g.render()` | Print the grid to terminal using ANSI |
| `on_key` | `g.on_key(key#str, fn)` | Register a key press callback |
| `on_click` | `g.on_click(x#int, y#int, fn)` | Register a tile click callback |
| `loop` | `g.loop(update_fn, fps#int)` | Start a game loop at given FPS |
| `width` | `g.width()` | Returns column count |
| `height` | `g.height()` | Returns row count |

### 9.2 Terminal Renderer

Each tile is rendered as a 2-character wide cell using ANSI background color codes:

```
\033[{bg_color_code}m  \033[0m
```

For tiles with a character set, the character is rendered centered in the tile:

```
\033[{bg_color_code}m{char} \033[0m
```

The full grid is rendered by printing all rows sequentially, then moving the cursor back up by `rows` lines using `\033[{rows}A` to allow re-rendering in place (for animation).

### 9.3 ANSI Background Color Codes

| Color | ANSI Background Code |
|-------|----------------------|
| black | `\033[40m` |
| red | `\033[41m` |
| green | `\033[42m` |
| yellow | `\033[43m` |
| blue | `\033[44m` |
| magenta | `\033[45m` |
| cyan | `\033[46m` |
| white | `\033[47m` |

### 9.4 Game Loop

`g.loop(update_fn, fps)` runs the following cycle at the given FPS:

1. Call `update_fn()` — the user updates grid state here
2. Call `g.render()` — redraws the grid in place
3. Check for keyboard input (non-blocking) and fire any registered `on_key` callbacks
4. Sleep for `1/fps` seconds
5. Repeat until the loop is stopped (e.g. `g.stop()` called inside `update_fn`)

### 9.5 Python Implementation Sketch

```python
bladeGRP AxonGrid:
    bladeFN __init__(self, cols, rows):
        self.cols = cols
        self.rows = rows
        self.tiles = [[{"color": "\033[40m", "char": " "} for _ in range(cols)] for _ in range(rows)]
        self.key_handlers = {}
        self._running = False

    bladeFN set(self, x, y, color):
        self.tiles[y][x]["color"] = color

    bladeFN fill(self, color):
        for row in self.tiles:
            for tile in row:
                tile["color"] = color

    bladeFN set_char(self, x, y, char):
        self.tiles[y][x]["char"] = char[0]

    bladeFN render(self):
        output = ""
        for row in self.tiles:
            for tile in row:
                output += f"{tile['color']}{tile['char']} \033[0m"
            output += "\n"
        output += f"\033[{self.rows + 1}A"
        write(output, end="", flush=True)

    bladeFN on_key(self, key, fn):
        self.key_handlers[key] = fn

    bladeFN loop(self, update_fn, fps=10):
        import time
        self._running = True
        while self._running:
            update_fn()
            self.render()
            self._handle_input()
            time.sleep(1 / fps)

    bladeFN stop(self):
        self._running = False
```

---

## 10. ANSI Color Literals

Color literals are a first-class token type in AxonBlade. They are not strings — they are a distinct `COLOR` token that the lexer recognizes and the evaluator resolves to ANSI escape strings.

### 10.1 Syntax

```
-*colorname*-
```

### 10.2 Full Color Map

| Literal | Foreground Code | Background Code |
|---------|----------------|----------------|
| `-*black*-` | `\033[30m` | `\033[40m` |
| `-*red*-` | `\033[31m` | `\033[41m` |
| `-*green*-` | `\033[32m` | `\033[42m` |
| `-*yellow*-` | `\033[33m` | `\033[43m` |
| `-*blue*-` | `\033[34m` | `\033[44m` |
| `-*magenta*-` | `\033[35m` | `\033[45m` |
| `-*cyan*-` | `\033[36m` | `\033[46m` |
| `-*white*-` | `\033[37m` | `\033[47m` |
| `-*reset*-` | `\033[0m` | `\033[0m` |

### 10.3 Usage Contexts

Color literals resolve to foreground ANSI codes when used with `write()`, and to background ANSI codes when passed to `grid.set()` or `grid.fill()`. The evaluator detects context from the call site.

```axb
write(-*red*- + "Error!" + -*reset*-)      # foreground: red text
g.fill(-*blue*-)                            # background: blue tiles
g.set(3, 3, -*green*-)                      # background: green tile
```

---

## 11. Error System

### 11.1 Error Hierarchy

```
AxonError (base)
├── AxonParseError      — syntax errors during lexing/parsing
├── AxonRuntimeError    — general runtime failure
├── AxonNameError       — undefined variable or attribute
├── AxonTypeError       — type annotation mismatch or bad operation
├── AxonIndexError      — list index out of bounds
├── AxonImportError     — module not found
└── AxonDivisionError   — division by zero
```

### 11.2 Error Format

All errors display in the following format:

```
AxonTypeError on line 12, col 8:
  Parameter 'age' expected int, got str
  
    >> result = greet("Ada", "thirty")
                                ^
```

### 11.3 Error Object in catch blocks

Inside a `catch` block, the error variable is an AxonBlade dict with fields:

```axb
catch e +/
    write(e~"type"~)      # "AxonTypeError"
    write(e~"message"~)   # "Parameter 'age' expected int, got str"
    write(e~"line"~)      # 12
ECB
```

---

## 12. Module System

### 12.1 Import Resolution

When `uselib -math-` is encountered:

1. Check `stdlib/math.axb` — if found, execute and return namespace
2. Check `./math.axb` relative to the current file — if found, execute and return namespace
3. Raise `AxonImportError` if neither found

### 12.2 Module Namespace

A module's namespace is the `Environment` produced after running the module file from top to bottom. Exposed as a dict-like object — `math.sqrt(x)` is dot-access on the namespace object.

### 12.3 Circular Import Protection

Track a set of currently-loading modules. If a module is requested that is already in the set, raise `AxonImportError: circular import detected`.

---

## 13. Project File Structure

```
axonblade/                      ← project root
├── core/
│   ├── lexer.py                ← Lexer class, char-by-char scanner
│   ├── tokens.py               ← TokenType enum, Token dataclass
│   ├── ast_nodes.py            ← All AST node dataclasses
│   ├── parser.py               ← Recursive descent parser
│   ├── environment.py          ← Environment class (scope chain)
│   ├── evaluator.py            ← Tree-walk evaluator
│   └── errors.py               ← All AxonError subclasses
├── stdlib/
│   ├── builtins.py             ← Python-backed built-in functions
│   ├── math.axb                ← Math stdlib in AxonBlade
│   └── string.axb              ← String stdlib in AxonBlade
├── grid/
│   ├── grid_object.py          ← AxonGrid Python class
│   └── renderer_term.py        ← ANSI terminal render logic
├── tests/
│   ├── test_lexer.py           ← Lexer unit tests (30+ cases)
│   ├── test_parser.py          ← Parser unit tests (40+ cases)
│   ├── test_evaluator.py       ← Evaluator integration tests
│   ├── test_grid.py            ← Grid object + renderer tests
│   └── fixtures/               ← .axb files used as test inputs
│       ├── hello.axb
│       ├── closures.axb
│       ├── classes.axb
│       └── errors.axb
├── examples/
│   ├── hello.axb               ← Hello world
│   ├── fibonacci.axb           ← Fibonacci with closures
│   ├── closures.axb            ← Closure and factory patterns
│   ├── classes.axb             ← OOP with bladeGRP
│   ├── snake.axb               ← Playable snake game using grid
│   └── life.axb                ← Conway's Game of Life using grid
├── website/                    ← Static website (GitHub Pages)
│   ├── index.html              ← Home page (hero, features, get started)
│   ├── examples.html           ← Examples gallery
│   └── docs/
│       └── index.html          ← Full language documentation
├── axonblade/
│   └── __main__.py             ← Package entry point (sets sys.path)
├── main.py                     ← CLI entry point (ablade run / repl / version)
├── repl.py                     ← Interactive REPL
├── pyproject.toml              ← Build config + ablade script entry point
└── README.md                   ← Installation + usage guide
```

---

## 14. Week-by-Week Roadmap

### Phase 1 — Foundations (Weeks 1–2)

#### Week 1 — Tokens + Lexer

**Goal:** Turn raw AxonBlade source text into a flat stream of typed tokens.

**Tasks:**
- Define `TokenType` enum covering all 40+ token types
- Write `Token` dataclass: `type`, `value`, `line`, `col`
- Write `Lexer` class with `tokenize(source: str) -> list[Token]`
- Implement character-by-character scanning loop
- Handle multi-character operators: `>>`, `+/`, `**`, `==`, `!=`, `<=`, `>=`, `|>`
- Handle color literal scanning: detect `-*`, scan name, expect `*-`, validate name
- Handle string scanning with `&{}` interpolation markers
- Handle `#type` annotation scanning inside `bladeFN` param lists
- Handle indentation stack — emit `INDENT`/`DEDENT` tokens correctly
- Handle comments — `#` outside param context skips to end of line
- Handle `ECB` as a keyword token distinct from identifiers
- Write `tests/test_lexer.py` with 30+ cases covering every token type

**Deliverable:** `core/lexer.py` + `core/tokens.py` — fully tested, tokenizes any valid AxonBlade source

---

#### Week 2 — AST Nodes + Pretty-Printer

**Goal:** Design the complete schema of the abstract syntax tree.

**Tasks:**
- Write all AST node dataclasses in `core/ast_nodes.py`
- Every node has `line: int` and `col: int` fields
- `FnDef` node stores `params: list[Param]` where `Param` has `name` and optional `type_ann`
- `ColorLiteral` node stores `name: str` only — ANSI resolution happens in evaluator
- `FStringLiteral` stores `parts: list` — alternating raw strings and AST expression nodes
- Write `pretty_write(node, indent=0) -> str` function for debugging
- Write tests for every node constructor ensuring fields are correct

**Deliverable:** `core/ast_nodes.py` — all node types defined, pretty-printer working

---

### Phase 2 — Parsing (Weeks 3–4)

#### Week 3 — Expression Parser

**Goal:** Parse all AxonBlade expressions into correct AST nodes.

**Tasks:**
- Write `Parser` class with `tokens`, `pos` cursor, `peek()`, `consume()`, `expect()` helpers
- Implement Pratt parsing (top-down operator precedence) for expressions
- Define precedence table: `**` > `* / %` > `+ -` > comparisons > `-n` > `-a` > `-o`
- Parse number, string, f-string, color, bool, null literals
- Parse list literals `[a, b, c]` and dict literals `{k: v}`
- Parse grouped expressions `(expr)`
- Parse unary minus and `-n`
- Parse function calls `foo(a, b)` and chained calls `foo(a)(b)`
- Parse dot access `obj.method` and method calls `obj.method(args)`
- Parse index access `list[0]` and slices `list~1:3~`
- Parse pipeline operator `expr |> func`

**Deliverable:** All expressions parse correctly, verified by pretty-printer output

---

#### Week 4 — Statement Parser

**Goal:** Parse all AxonBlade statements and full programs.

**Tasks:**
- Parse `>> name = expr` variable declarations
- Parse bare `name = expr` re-assignments
- Parse `bladeFN name(params) +/ body ECB` — handle param type annotations
- Parse nested `bladeFN` inside `bladeFN` (for closures)
- Parse `bladeGRP Name +/ methods ECB`
- Parse `if expr +/ body ECB elif ... else +/ body ECB`
- Parse `while expr +/ body ECB`
- Parse `for name in expr +/ body ECB`
- Parse `try +/ body ECB catch e +/ body ECB`
- Parse `uselib -modulename-` for module imports
- Parse `raise expr`
- Parse `return expr`
- Parse top-level `Program` node (list of all statements)
- Write `tests/test_parser.py` with 40+ cases

**Deliverable:** Full parser that handles every AxonBlade construct

---

### Phase 3 — Evaluation (Weeks 5–7)

#### Week 5 — Environment + Core Evaluator

**Goal:** Execute basic AxonBlade programs — variables, math, control flow, colors.

**Tasks:**
- Write `Environment` class with `define`, `get`, `set`, parent chaining
- Write `Evaluator` class with `eval(node, env)` dispatch method
- Evaluate all literal nodes → Python values
- Evaluate `ColorLiteral` → ANSI escape string
- Evaluate `FStringLiteral` → concatenated string with interpolated parts
- Evaluate `BinaryOp` with type checks and `AxonTypeError` on invalid combos
- Evaluate `UnaryOp` (`-`, `-n`)
- Evaluate `AssignStmt` — `define` for declarations, `set` for re-assignments
- Evaluate `Identifier` → `env.get(name)`
- Evaluate `IfStmt`, `WhileStmt`, `ForStmt`
- Evaluate `ListLiteral`, `DictLiteral`, `IndexAccess` (~val~), `SliceAccess` (~start:end~)

**Deliverable:** Basic programs with variables, math, colors, and control flow run correctly

---

#### Week 6 — Functions, Closures, bladeGRPs, Built-ins

**Goal:** Make AxonBlade a complete language with callable functions and objects.

**Tasks:**
- Implement `AxonFunction` class storing params, body, closure env
- Evaluate `FnDef` → create `AxonFunction`, define in current env
- Evaluate `CallExpr` → create child env from closure env, bind args, check types, eval body
- Implement `ReturnException` for return statement unwinding
- Implement closures — inner functions capture `env` at definition time, not call time
- Implement `AxonBladeGRP`, `AxonInstance`, `BoundMethod`
- Evaluate `BladeGRPDef` → build method dict, define bladeGRP in env
- Evaluate `CallExpr` on a bladeGRP → create instance, call `init` if defined
- Evaluate `DotAccess` on instances → check fields then methods
- Evaluate `PipelineExpr` → rewrite `a |> f(b)` as `f(a, b)` at eval time
- Register all built-in functions in the global env from `stdlib/builtins.py`
- Evaluate `FStringLiteral` fully with all expression types working

**Deliverable:** Functions, closures, bladeGRPs, type checking, built-ins all working

---

#### Week 7 — Errors, Modules, REPL, CLI

**Goal:** Make AxonBlade fully runnable as a real terminal language.

**Tasks:**
- Evaluate `TryCatch` — wrap body eval in Python try/except, bind error dict to catch var
- Evaluate `RaiseStmt` — throw `AxonRuntimeError` with the given message
- Write all error classes in `core/errors.py`
- Format error messages with line/col and source excerpt
- Implement module loader — run `.axb` file in fresh env, return namespace object
- Write `stdlib/math.axb` and `stdlib/string.axb`
- Register `__builtin_*` hooks called by stdlib .axb files
- Write `repl.py` — readline loop, pretty-print return values, catch and display errors without crashing, show `>>` prompt styled with color literals
- Write `main.py` — argparse CLI with `axb run file.axb`, `axb repl`, `axb version`
- Integration test: run `examples/fibonacci.axb` end to end

**Deliverable:** Full working language. Any `.axb` file runs from terminal.

---

### Phase 4 — Grid (Week 8)

#### Week 8 — Grid Object + Terminal Renderer

**Goal:** Implement the grid primitive — AxonBlade's signature feature.

**Tasks:**
- Write `grid/grid_object.py` — `AxonGrid` Python class with full tile state
- Implement all grid methods: `set`, `get`, `fill`, `set_char`, `get_char`, `clear`, `render`, `on_key`, `on_click`, `loop`, `stop`, `width`, `height`
- Write `grid/renderer_term.py` — ANSI background color rendering, in-place re-render using cursor-up escape
- Register `grid(cols, rows)` as a built-in that returns an `AxonGrid` wrapped as an AxonBlade value
- Handle dot-method dispatch on `AxonGrid` in the evaluator
- Write `examples/snake.axb` — playable Snake in ~40 lines using grid + on_key + loop
- Write `examples/life.axb` — Conway's Game of Life using grid.loop()
- Write `tests/test_grid.py`

**Deliverable:** `grid()` fully usable in AxonBlade, Snake and Life running in terminal

---

### Phase 5 — Website (Weeks 9–10)

#### Week 9 — ~~Pyodide Bridge + Canvas Renderer~~ (Scrapped)

**Status: Cancelled.** The Pyodide bridge between Python and JS was not possible. The playground has been removed from the site.

---

#### Week 10 — Website: Docs + Examples + Deploy

**Goal:** Ship a complete AxonBlade website with documentation and example showcase — statically hosted on GitHub Pages.

**Tasks:**

*Site structure:*
- Multi-page static site: Home, Docs, Examples
- Shared navbar, dark AxonBlade-themed design (dark bg, cyan/green accents)
- Responsive layout, footer with version + GitHub link

*Home page:*
- Hero section with tagline and animated color demo
- Feature highlights, install snippet, language at a glance

*Documentation:*
- Getting Started — install, first program, REPL, CLI
- Syntax Reference — variables, strings, functions, control flow, classes, imports
- Operators — full table including `-n`/`-a`/`-o`, `>>`, `+/`, `|>`, `**`
- Type System, Color Literals, Grid System, Standard Library, Error Handling, Module System
- Syntax-highlighted code blocks on every page

*Deploy:*
- Zero build step — plain HTML/CSS/JS
- Deploy to GitHub Pages at `AI-Alon.github.io/axonblade`

**Deliverable:** Live website at `AI-Alon.github.io/axonblade`

---

## 15. Testing Strategy

### 15.1 Unit Tests

| File | What it tests | Min cases |
|------|---------------|-----------|
| `test_lexer.py` | Every token type, edge cases (empty file, only comments, deeply nested indentation) | 30 |
| `test_parser.py` | Every AST node type, operator precedence, nested structures | 40 |
| `test_evaluator.py` | All expressions, statements, closures, bladeGRPs, error handling, modules | 50 |
| `test_grid.py` | Grid construction, all methods, render output, loop callback firing | 20 |

### 15.2 Integration Tests

Run full `.axb` programs and compare stdout output to expected strings:

- `hello.axb` → `"Hello, AxonBlade!"`
- `fibonacci.axb` → `"0 1 1 2 3 5 8 13 21 34"`
- `closures.axb` → counter incrementing correctly
- `classes.axb` → Animal speaking correctly
- `errors.axb` → correct error message and line number

### 15.3 Test Runner

Use Python's built-in `unittest` or `pytest`. Run all tests with:

```bash
python -m pytest tests/ -v
```

---

## 16. Website

### 16.1 Pages

| Page | File | Description |
|------|------|-------------|
| Home | `website/index.html` | Hero, features, install snippet, language preview |
| Docs | `website/docs/index.html` | Full language documentation |
| Examples | `website/examples.html` | Annotated example programs |

> **Note:** The interactive playground (Phase 9) was scrapped. The Pyodide bridge between Python and JavaScript proved too unreliable. All three pages are complete and deployed.

### 16.2 Tech Stack

| Layer | Technology |
|-------|-----------|
| Site | Plain HTML/CSS/JS — zero build step |
| Hosting | GitHub Pages at `AI-Alon.github.io/axonblade` |

### 16.3 Site Layout

```
┌──────────────────────────────────────────────────┐
│  AxonBlade    Home  Docs  Examples  GitHub        │
├──────────────────────────────────────────────────┤
│                                                   │
│   [page content]                                  │
│                                                   │
├──────────────────────────────────────────────────┤
│  AxonBlade v1.0  ·  MIT  ·  © 2026 AI-Alon       │
└──────────────────────────────────────────────────┘
```

### 16.4 Documentation Sections

1. Getting Started (install, first program, REPL, CLI)
2. Variables & Strings
3. Operators (full table, ECB, `>>`, `+/`, `|>`, `-n`/`-a`/`-o`)
4. Pipeline operator
5. Control Flow
6. Lists (tilde indexing, slice syntax, methods)
7. Dictionaries (tilde access, methods)
8. Functions (closures, first-class)
9. Classes (bladeGRP, `blade` self)
10. Type Annotations
11. Color Literals
12. Error Handling
13. Modules (uselib)
14. Built-in Functions
15. Grid System
16. Standard Library (math, string)

---

## 17. Example Programs

### 17.1 Hello World (`hello.axb`)

```axb
write(-*cyan*- + "Hello, AxonBlade!" + -*reset*-)
```

### 17.2 Fibonacci (`fibonacci.axb`)

```axb
bladeFN fib(n#int) +/
    if n <= 1 +/
        return n
    ECB
    return fib(n - 1) + fib(n - 2)
ECB

>> i = 0
while i < 10 +/
    write(fib(i))
    i = i + 1
ECB
```

### 17.3 Counter with closure (`closures.axb`)

```axb
bladeFN make_counter(start#int) +/
    >> count = start
    bladeFN increment() +/
        count = count + 1
        return count
    ECB
    return increment
ECB

>> c = make_counter(0)
write(c())
write(c())
write(c())
```

### 17.4 Snake game (`snake.axb`)

```axb
>> g = grid(20, 15)
>> snake = [{x: 10, y: 7}]
>> dir = {x: 1, y: 0}
>> food = {x: 5, y: 5}
>> running = true

bladeFN place_food() +/
    g.set(food~"x"~, food~"y"~, -*red*-)
    g.set_char(food~"x"~, food~"y"~, "*")
ECB

bladeFN draw() +/
    g.fill(-*black*-)
    place_food()
    for seg in snake +/
        g.set(seg~"x"~, seg~"y"~, -*green*-)
    ECB
ECB

bladeFN update() +/
    >> head = snake~0~
    >> new_head = {x: head~"x"~ + dir~"x"~, y: head~"y"~ + dir~"y"~}
    snake.insert(0, new_head)
    snake.pop()
    draw()
ECB

g.on_key("w", bladeFN() +/ dir = {x: 0, y: -1} ECB)
g.on_key("s", bladeFN() +/ dir = {x: 0, y: 1}  ECB)
g.on_key("a", bladeFN() +/ dir = {x: -1, y: 0} ECB)
g.on_key("d", bladeFN() +/ dir = {x: 1, y: 0}  ECB)
g.on_key("q", bladeFN() +/ g.stop() ECB)

draw()
g.loop(update, 10)
```

### 17.5 Conway's Game of Life (`life.axb`)

```axb
>> W = 40
>> H = 20
>> g = grid(W, H)

bladeFN make_board() +/
    >> board = []
    >> y = 0
    while y < H +/
        >> row = []
        >> x = 0
        while x < W +/
            row.append(0)
            x = x + 1
        ECB
        board.append(row)
        y = y + 1
    ECB
    return board
ECB

>> board = make_board()
board~10~~10~ = 1
board~10~~11~ = 1
board~11~~10~ = 1
board~11~~11~ = 1

bladeFN step() +/
    >> next = make_board()
    >> y = 0
    while y < H +/
        >> x = 0
        while x < W +/
            >> alive = board~y~~x~
            if alive == 1 +/
                g.set(x, y, -*green*-)
            ECB
            else +/
                g.set(x, y, -*black*-)
            ECB
            x = x + 1
        ECB
        y = y + 1
    ECB
    board = next
ECB

g.on_key("q", bladeFN() +/ g.stop() ECB)
g.loop(step, 10)
```

---

## 18. Future Roadmap (Post v1)

These features are explicitly out of scope for v1 but planned for future versions:

| Feature | Version | Notes |
|---------|---------|-------|
| Inheritance (`bladeGRP Dog extends Animal`) | v1.1 | Single inheritance only |
| List comprehensions | v1.1 | `[x * 2 for x in nums]` |
| Pipeline operator full support | v1.1 | `list \|> filter(fn) \|> map(fn)` |
| Bytecode compiler + VM | v2.0 | Significant performance improvement |
| Standard library expansion | v1.2 | `io.axb`, `json.axb`, `http.axb` |
| Package manager | v2.0 | `axb install package_name` |
| VSCode extension | v1.2 | Syntax highlighting + error squiggles |
| Debugger | v2.0 | Step-through execution in playground |
| Tail call optimization | v1.3 | Prevents stack overflow in deep recursion |
| Native HTTP requests | v1.2 | `http.get(url)` in stdlib |

---

*AxonBlade is built from scratch in Python. No parser generator, no lexer library, no frameworks — every line of the interpreter is written by hand.*