# AxonBlade

> An expressive scripting language with built-in color literals, a native grid primitive, and clean syntax.

Write terminal games, visualizations, and scripts with a language designed to be readable, colorful, and fun.

---

## Features

- **Unique syntax** — `bladeFN`, `+/...ECB`, `>>`, `&{}` string interpolation
- **Color literals** — `-*red*-`, `-*cyan*-` resolve to ANSI escape codes
- **Native grid** — `grid(cols, rows)` renders colored tiles directly in the terminal
- **Full language** — closures, classes, modules, error handling, type annotations
- **Pipeline operator** — `value |> fn` chains transformations cleanly
- **Standard library** — `math` and `string` modules included
- **Interactive REPL** — live evaluation with `ablade repl`

---

## Install

```bash
git clone https://github.com/AI-Alon/axonblade.git
cd axonblade
pip install -e .
```

Requires Python 3.11+.

---

## Usage

```bash
ablade run <file.axb>   # run a script
ablade repl             # start the interactive REPL
ablade version          # print version
```

---

## Examples

Run any of the included examples:

```bash
ablade run examples/hello.axb       # colors, strings, math
ablade run examples/fibonacci.axb   # recursion, closures, pipeline
ablade run examples/closures.axb    # counter factory, adder, map
ablade run examples/classes.axb     # bladeGRP, error handling
ablade run examples/snake.axb       # playable Snake game
ablade run examples/life.axb        # Conway's Game of Life
```

---

## Language Overview

### Variables

```axb
>> name = "AxonBlade"
>> version = 1
>> active = true
```

### String interpolation

```axb
write("Hello, &{name}! Version &{version}")
```

### Functions

```axb
bladeFN greet(who#str) +/
    write(-*cyan*- + "Hello, &{who}!" + -*reset*-)
ECB

greet("world")
```

### Classes

```axb
bladeGRP Point +/
    bladeFN init(blade, x#int, y#int) +/
        blade.x = x
        blade.y = y
    ECB
    bladeFN to_str(blade) +/
        return "(&{blade.x}, &{blade.y})"
    ECB
ECB

>> p = Point(3, 4)
write(p.to_str())
```

### Closures

```axb
bladeFN make_counter() +/
    >> count = 0
    return bladeFN() +/
        count = count + 1
        return count
    ECB
ECB

>> counter = make_counter()
write(counter())   # 1
write(counter())   # 2
```

### Control flow

```axb
if x > 0 +/
    write("positive")
ECB
elif x < 0 +/
    write("negative")
ECB
else +/
    write("zero")
ECB

while x < 10 +/
    x = x + 1
ECB

for item in list +/
    write(item)
ECB
```

### Error handling

```axb
try +/
    >> result = 10 / 0
ECB
catch err +/
    write("Caught: &{err~\"message\"~}")
ECB
```

### Pipeline operator

```axb
bladeFN double(n) +/ return n * 2 ECB
bladeFN inc(n)    +/ return n + 1 ECB

>> result = 3 |> double |> inc
write(result)   # 7
```

### Color literals

```axb
write(-*red*-     + "  red    " + -*reset*-)
write(-*green*-   + "  green  " + -*reset*-)
write(-*cyan*-    + "  cyan   " + -*reset*-)
write(-*yellow*-  + "  yellow " + -*reset*-)
write(-*blue*-    + "  blue   " + -*reset*-)
write(-*magenta*- + "  magenta" + -*reset*-)
write(-*white*-   + "  white  " + -*reset*-)
```

### Grid system

```axb
>> g = grid(24, 16)
g.fill(-*black*-)
g.set(12, 8, -*cyan*-)
g.set_char(12, 8, "@")
g.on_key("q", bladeFN() +/ g.stop() ECB)
g.loop(bladeFN() +/ null ECB, 10)
```

### Modules

```axb
uselib -math-
uselib -string-

write(math.sqrt(16))          # 4.0
write(string.upper("hello"))  # HELLO
```

### Logical operators

| Operator | Meaning |
|----------|---------|
| `-a`     | and     |
| `-o`     | or      |
| `-n`     | not     |

### Type annotations

```axb
bladeFN add(a#int, b#int) +/
    return a + b
ECB
```

---

## Project Structure

```
axonblade/
├── core/
│   ├── lexer.py          # tokenizer
│   ├── parser.py         # Pratt parser → AST
│   ├── ast_nodes.py      # AST node definitions
│   ├── evaluator.py      # tree-walk interpreter
│   ├── environment.py    # scoped variable store
│   ├── errors.py         # error hierarchy
│   └── module_loader.py  # uselib module system
├── grid/
│   ├── grid_object.py    # AxonGrid state
│   └── renderer_term.py  # ANSI terminal renderer
├── stdlib/
│   ├── builtins.py       # built-in functions
│   ├── math.axb          # math standard library
│   └── string.axb        # string standard library
├── examples/             # runnable .axb programs
├── website/              # project website
├── main.py               # CLI entry point
└── repl.py               # interactive REPL
```

---

## License

MIT — see [LICENSE](LICENSE).
