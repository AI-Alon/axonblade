# AxonBlade ⚡

**A scripting language that makes the terminal come alive.**

AxonBlade is a compiled scripting language with a bytecode VM, first-class color literals, a native grid primitive for terminal rendering, closures, classes, modules, and a clean — opinionated — syntax that's unlike anything you've used before.

Write terminal games. Build visualizations. Script with color.

---

## Download

No Python required — grab the binary for your platform, add it to PATH, and run.

| Platform | Download |
|----------|----------|
| **Linux x64** | [ablade-linux-x64](https://github.com/AI-Alon/axonblade/releases/latest/download/ablade-linux-x64) |
| **macOS** (M1/M2/M3 + Intel via Rosetta 2) | [ablade-macos-arm64](https://github.com/AI-Alon/axonblade/releases/latest/download/ablade-macos-arm64) |
| **Windows x64** | [ablade-windows-x64.exe](https://github.com/AI-Alon/axonblade/releases/latest/download/ablade-windows-x64.exe) |

### Add to PATH

**Linux / macOS**
```bash
chmod +x ablade-linux-x64          # or ablade-macos-arm64 / ablade-macos-x64
mv ablade-linux-x64 /usr/local/bin/ablade
```

**Windows** — move `ablade-windows-x64.exe` to a folder that's in your `PATH`, then rename it to `ablade.exe`.

### Verify

```bash
ablade version
```

---

## Quick Start

```bash
ablade run examples/hello.axb      # run a source file
ablade compile examples/hello.axb  # compile to hello.axbc
ablade run examples/hello.axbc     # run the compiled binary
ablade repl                        # interactive REPL
ablade fmt examples/hello.axb      # format source file
ablade lint examples/hello.axb     # static analysis
ablade test tests/                 # run *_test.axb files
```

---

## Why AxonBlade?

Most scripting languages treat the terminal as an afterthought. AxonBlade was built for it.

- 🎨 **Color is a value** — `-*cyan*-` is not a string, it's a first-class color literal
- 🟩 **Grid is built in** — `grid(cols, rows)` gives you a tile canvas, no library needed
- ⚡ **Bytecode compiled** — source compiles to `.axbc` bytecode, executed by a stack-based VM
- 🔗 **Pipeline operator** — chain transformations with `|>`
- 🧱 **Full OOP** — classes via `bladeGRP`, with `blade` as self
- 🛡️ **Type annotations** — optional `#type` parameter hints with runtime checking
- 📦 **Module system** — `uselib -math-`, `uselib -string-`, or your own `.axb` files
- 🎮 **Interactive examples** — playable Snake and Conway's Game of Life included

---

## The Language

### Variables & strings

```axb
>> name = "AxonBlade"
>> version = 2
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
│   ├── compiler.py        # AST → bytecode compiler
│   ├── vm.py              # stack-based bytecode VM
│   ├── serializer.py      # .axbc binary format
│   ├── runtime.py         # shared runtime types (AxonFunction, Cell, …)
│   ├── code_object.py     # Instruction + CodeObject
│   ├── opcodes.py         # opcode definitions
│   ├── environment.py     # scoped variable store
│   ├── errors.py          # error hierarchy
│   ├── formatter.py       # ablade fmt
│   └── module_loader.py   # uselib module system
├── grid/
│   ├── grid_object.py     # AxonGrid state & API
│   └── renderer_term.py   # ANSI terminal renderer
├── stdlib/
│   ├── builtins.py        # built-in functions
│   ├── math.axb           # math standard library
│   ├── string.axb         # string standard library
│   ├── io.axb             # file I/O
│   ├── json.axb           # JSON parse/stringify
│   ├── http.axb           # HTTP client
│   ├── regex.axb          # regular expressions
│   ├── datetime.axb       # date/time utilities
│   └── random.axb         # random number generation
├── tools/
│   ├── linter.py          # ablade lint
│   └── test_runner.py     # ablade test
├── examples/              # runnable .axb programs
├── tests/fixtures/        # *_test.axb test suite (88 tests)
├── vscode-extension/      # .axb syntax highlighting for VS Code
├── axonblade.spec         # PyInstaller build spec
├── main.py                # CLI entry point
└── repl.py                # interactive REPL
```

---

## Build from Source

Requires Python 3.11+.

```bash
git clone https://github.com/AI-Alon/axonblade.git
cd axonblade
pip install -e ".[dev]"
```

To build a standalone binary locally:

```bash
pyinstaller axonblade.spec
# output: dist/ablade
```

Run the test suite:

```bash
ablade test tests/
```

---

## License

MIT — see [LICENSE](LICENSE).
