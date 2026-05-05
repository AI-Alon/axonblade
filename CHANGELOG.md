# Changelog

## v2.0.0 — 2026-05-04

### Bytecode Compiler & VM

- New `core/compiler.py` — single-pass AST → bytecode compiler producing `CodeObject` values
- New `core/vm.py` — stack-based virtual machine; each call creates an isolated `Frame`
- New `core/serializer.py` — binary `.axbc` format (msgpack-style) for pre-compiled files
- `ablade compile <file.axb>` — new CLI command that writes `<file>.axbc` alongside the source
- `ablade run` now accepts both `.axb` (compile-and-run) and `.axbc` (run precompiled) files
- Closures are captured via `Cell` objects and `LOAD_DEREF` / `STORE_DEREF` opcodes
- Tree-walking evaluator (`core/evaluator.py`) removed; all execution goes through the VM

### Standalone Binary

- `axonblade.spec` — PyInstaller spec; bundles stdlib `.axb` files via `datas`
- GitHub Actions workflow (`.github/workflows/release.yml`) builds and publishes binaries on `v2.*` tags
- Released binaries: `ablade-linux-x64`, `ablade-macos-arm64`, `ablade-windows-x64.exe`
- No Python installation required to run AxonBlade programs

### Online Playground

- `playground/backend/main.py` — FastAPI + SSE backend; streams execution output line-by-line
- `docs/playground.html` — in-browser IDE with CodeMirror 6 syntax highlighting and ANSI color output
- URL-hash sharing: click **Share** to encode the current snippet into the URL
- 7 built-in examples; `Ctrl+Enter` shortcut to run

### Standard Library

- `stdlib/io.axb` — `io.read`, `io.write`, `io.append`, `io.exists`, `io.delete`
- `stdlib/http.axb` — `http.get`, `http.post` with response object (`.ok`, `.status`, `.body`)
- `stdlib/json.axb` — `json.parse`, `json.stringify`
- `stdlib/regex.axb` — `regex.match`, `regex.find_all`, `regex.replace`, `regex.split`
- `stdlib/datetime.axb` — `datetime.now`, `datetime.timestamp`, date formatting
- `stdlib/random.axb` — `random.int`, `random.float`, `random.choice`, `random.shuffle`
- `stdlib/math.axb` — `math.sqrt`, `math.floor`, `math.ceil`, `math.abs`, `math.pow`, constants
- `stdlib/string.axb` — `string.split`, `string.join`, `string.trim`, `string.pad`

### Tooling

- `ablade fmt` — canonical source formatter (parse → AST → re-emit)
- `ablade lint` — static analyser; reports undefined variables, arity errors, unused declarations
- `ablade test` — discovers `*_test.axb` files, runs them through the VM, reports pass/fail

### VSCode Extension

- `.vsix` package providing syntax highlighting, bracket matching, and auto-indentation for `.axb` files

### Breaking Changes

- The tree-walking evaluator is gone; all programs now run through the compiler + VM pipeline
- Install method changed: download a binary from GitHub Releases instead of `pip install`
- `pip install -e .` still works for source builds

---

## v1.0.0 — 2025

Initial release.

- Tree-walking interpreter (evaluator)
- Variables (`>>`), strings with `&{}` interpolation, color literals (`-*cyan*-`)
- Functions (`bladeFN`), classes (`bladeGRP`), closures
- Pipeline operator (`|>`)
- Type annotations (`#str`, `#int`, `#float`, `#bool`, `#fn`)
- Grid system (`grid(cols, rows)`) for terminal rendering
- REPL (`ablade repl`)
- Playable Snake and Conway's Game of Life examples
