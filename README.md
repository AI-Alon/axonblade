# AxonBlade ⚡

**A scripting language that makes the terminal come alive.**

AxonBlade is a fully interpreted scripting language built in Python, with first-class color literals, a native grid primitive for terminal rendering, closures, classes, modules, and a clean — opinionated — syntax that's unlike anything you've used before.

Write terminal games. Build visualizations. Script with color.

---

## Why AxonBlade?

Most scripting languages treat the terminal as an afterthought. AxonBlade was built for it.

- 🎨 **Color is a value** — `-*cyan*-` is not a string, it's a first-class color literal
- 🟩 **Grid is built in** — `grid(cols, rows)` gives you a tile canvas in the terminal, no library needed
- ⚡ **Clean syntax** — `bladeFN`, `+/...ECB`, `>>` — unconventional, consistent, and readable
- 🔗 **Pipeline operator** — chain transformations with `|>`
- 🧱 **Full OOP** — classes via `bladeGRP`, with `blade` as self
- 🛡️ **Type annotations** — optional `#type` parameter hints with runtime checking
- 📦 **Module system** — `uselib -math-`, `uselib -string-`, or your own `.axb` files
- 🎮 **Interactive examples** — playable Snake and Conway's Game of Life included out of the box

---

## Install

```bash
git clone https://github.com/AI-Alon/axonblade.git
cd axonblade
pip install -e .
```

> Requires Python 3.11+

---

## Quick Start

```bash
ablade run examples/hello.axb
ablade repl
ablade version
```

---

## The Language

### Variables & strings

```axb
>> name = "AxonBlade"
>> version = 1
>> ready = true

write("Hello from &{name} v&{version}!")
```

### Functions & closures

```axb
bladeFN make_adder(n) +/
    return bladeFN(x) +/
        return x + n
    ECB
ECB

>> add10 = make_adder(10)
write(add10(5))    # 15
write(add10(32))   # 42
```

### Classes

```axb
bladeGRP Animal +/
    bladeFN init(blade, name#str, sound#str) +/
        blade.name = name
        blade.sound = sound
    ECB
    bladeFN speak(blade) +/
        write(-*cyan*- + "&{blade.name} says: &{blade.sound}" + -*reset*-)
    ECB
ECB

>> dog = Animal("Rex", "woof!")
dog.speak()
```

### Pipeline operator

```axb
bladeFN double(n) +/ return n * 2 ECB
bladeFN inc(n)    +/ return n + 1 ECB
bladeFN square(n) +/ return n * n ECB

>> result = 3 |> double |> inc |> square
write(result)   # 49
```

### Color literals

```axb
write(-*red*-     + " red     " + -*reset*-)
write(-*yellow*-  + " yellow  " + -*reset*-)
write(-*green*-   + " green   " + -*reset*-)
write(-*cyan*-    + " cyan    " + -*reset*-)
write(-*blue*-    + " blue    " + -*reset*-)
write(-*magenta*- + " magenta " + -*reset*-)
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

### Error handling

```axb
try +/
    >> result = 10 / 0
ECB
catch err +/
    write(-*red*- + "Caught: &{err~\"message\"~}" + -*reset*-)
ECB
```

### Modules

```axb
uselib -math-
uselib -string-

write(math.sqrt(144))            # 12.0
write(string.upper("axonblade")) # AXONBLADE
```

### Logical operators

| Operator | Meaning |
|----------|---------|
| `-a` | and |
| `-o` | or |
| `-n` | not |

---

## Included Examples

| File | Description |
|------|-------------|
| `examples/hello.axb` | Colors, strings, math — the classic intro |
| `examples/fibonacci.axb` | Recursive + iterative fib, squared sequence |
| `examples/closures.axb` | Counter factory, adder generator, map via pipeline |
| `examples/classes.axb` | Animal health system, Point geometry, error handling |
| `examples/snake.axb` | Fully playable Snake — grid, game loop, keyboard input |
| `examples/life.axb` | Conway's Game of Life — edit mode + live simulation |

Run any of them:

```bash
ablade run examples/snake.axb
```

---

## Project Structure

```
axonblade/
├── core/
│   ├── lexer.py           # tokenizer
│   ├── parser.py          # Pratt parser → AST
│   ├── ast_nodes.py       # AST node definitions
│   ├── evaluator.py       # tree-walk interpreter
│   ├── environment.py     # scoped variable store
│   ├── errors.py          # error hierarchy
│   └── module_loader.py   # uselib module system
├── grid/
│   ├── grid_object.py     # AxonGrid state & API
│   └── renderer_term.py   # ANSI terminal renderer
├── stdlib/
│   ├── builtins.py        # built-in functions
│   ├── math.axb           # math standard library
│   └── string.axb         # string standard library
├── examples/              # runnable .axb programs
├── website/               # project website source
├── main.py                # CLI entry point
└── repl.py                # interactive REPL
```

---

## License

MIT — see [LICENSE](LICENSE).
