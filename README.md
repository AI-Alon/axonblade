# AxonBlade

A custom interpreted scripting language implemented in Python, with a native ANSI grid primitive for building terminal games and simulations.

## Features

- **Unique syntax** — `bladeFN`, `+/`, `ECB`, `>>`, `&{}`, `#type`
- **Color literals** — `-*red*-`, `-*cyan*-` are first-class values resolving to ANSI codes
- **Built-in grid** — `grid(cols, rows)` renders colored tiles directly in the terminal
- **Full language** — closures, classes (`bladeGRP`), modules, error handling, type annotations
- **Interactive examples** — playable Snake and Conway's Game of Life included

## Install

```bash
pip install -e .
```

## Usage

```bash
ablade run examples/hello.axb
ablade run examples/snake.axb
ablade run examples/life.axb
ablade repl
ablade version
```

## Syntax at a glance

```axb
# Variables
>> name = "AxonBlade"
>> version = 1

# Functions
bladeFN greet(who#str) +/
    write(-*cyan*- + "Hello, &{who}!" + -*reset*-)
ECB

greet(name)

# Classes
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

# Grid
>> g = grid(20, 10)
g.fill(-*black*-)
g.set(10, 5, -*red*-)
g.on_key("q", bladeFN() +/ g.stop() ECB)
g.loop(bladeFN() +/ null ECB, 10)
```

## Comments

```axb
# single-line comment

#/
  multi-line
  comment
/#
```

## Logical operators

| Operator | Meaning |
|----------|---------|
| `-a` | and |
| `-o` | or |
| `-n` | not |

## Running tests

```bash
python -m pytest tests/ -v
```
