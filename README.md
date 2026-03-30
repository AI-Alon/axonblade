# AxonBlade

An expressive scripting language with built-in color literals, a native grid primitive, and clean syntax — write terminal art, games, and scripts with ease.

## Install

```bash
git clone https://github.com/AI-Alon/axonblade.git
cd axonblade
pip install -e .
```

## Usage

```bash
ablade run <file.axb>   # run a script
ablade repl             # interactive REPL
ablade version          # print version
```

## Examples

```bash
ablade run examples/hello.axb
ablade run examples/fibonacci.axb
ablade run examples/closures.axb
ablade run examples/classes.axb
ablade run examples/snake.axb
ablade run examples/life.axb
```

## Syntax

### Variables

```axb
>> name = "AxonBlade"
>> version = 1
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

### Color literals

```axb
write(-*red*-    + "red text"    + -*reset*-)
write(-*cyan*-   + "cyan text"   + -*reset*-)
write(-*green*-  + "green text"  + -*reset*-)
write(-*yellow*- + "yellow text" + -*reset*-)
```

### Grid

```axb
>> g = grid(20, 10)
g.fill(-*black*-)
g.set(10, 5, -*red*-)
g.on_key("q", bladeFN() +/ g.stop() ECB)
g.loop(bladeFN() +/ null ECB, 10)
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

### Pipeline

```axb
>> result = 3 |> double |> inc |> square
```

### Logical operators

| Operator | Meaning |
|----------|---------|
| `-a` | and |
| `-o` | or |
| `-n` | not |

## License

MIT
