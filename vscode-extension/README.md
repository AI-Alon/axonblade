# AxonBlade for Visual Studio Code

Syntax highlighting, bracket matching, and comment toggling for [AxonBlade](https://ai-alon.github.io/axonblade/) `.axb` files.

## Features

- **Syntax highlighting** for all AxonBlade constructs:
  - Keywords: `bladeFN`, `bladeGRP`, `ECB`, `return`, `if`, `elif`, `else`, `while`, `for`, `in`, `try`, `catch`, `raise`, `uselib`
  - Logic operators: `-a` (and), `-o` (or), `-n` (not)
  - Color literals: `-*red*-`, `-*cyan*-`, `-*reset*-` highlighted in a distinct color
  - String interpolation: `&{expr}` inside strings highlighted separately
  - Variable declaration: `>>` highlighted as a keyword operator
  - Block delimiters: `+/` and `ECB`
  - Type annotations: `#str`, `#int`, `#float`, `#bool`, `#list`, `#fn`
  - Built-in functions: `write`, `len`, `type`, `range`, `input`, `grid`, `str`, `int`, `float`, `bool`
  - Numbers, booleans (`true`/`false`), `null`, `blade` (self)
- **Bracket matching** for `()`, `[]`, `{}`
- **Comment toggling** — `#` for line comments, `#/ ... /#` for block comments
- **Auto-close pairs** for `()`, `[]`, `{}`, `""`
- **Auto-indent** — indents after `+/`, dedents at `ECB`

## Install

### From VSIX (recommended)

1. Download `axonblade-2.0.0.vsix` from [GitHub Releases](https://github.com/AI-Alon/axonblade/releases).
2. Open VS Code → Extensions panel → `···` menu → **Install from VSIX…**
3. Select the downloaded file.

### From source (development)

```bash
cd vscode-extension
npm install -g @vscode/vsce
vsce package
code --install-extension axonblade-2.0.0.vsix
```

Or press **F5** inside the `vscode-extension/` folder to launch an Extension Development Host.

## Usage

Open any `.axb` file — the extension activates automatically.

## Language Quick Reference

```axb
# line comment
#/ block comment /#

bladeFN greet(name#str) +/
    >> msg = "Hello, &{name}!"
    write(-*cyan*- + msg + -*reset*-)
ECB

greet("world")
```

## License

MIT — see [LICENSE](../LICENSE) in the repository root.
