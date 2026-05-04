"""
core/module_loader.py — AxonBlade module system (V2 — compiler + VM).

Resolution order:
  1. stdlib/{name}.axb
  2. ./{name}.axb relative to the importing file
  3. AxonImportError if not found

Returns an Environment (namespace object) populated with the module's
exported names so that dot-access works: `math.sqrt(x)`.

Circular-import detection is handled via _loading_set.
"""

from __future__ import annotations

import sys
from pathlib import Path

from core.errors import AxonImportError

_loading_set: set[str] = set()

# When running as a PyInstaller frozen binary, stdlib .axb files are unpacked
# into sys._MEIPASS/stdlib/. Otherwise use the normal source tree location.
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    _STDLIB_DIR = Path(sys._MEIPASS) / "stdlib"
else:
    _STDLIB_DIR = Path(__file__).parent.parent / "stdlib"


def load_module(name: str, caller_file: str | None = None,
                vm: object = None) -> object:
    """
    Compile and execute the module named *name*, returning an Environment
    namespace for dot-access by the caller.

    Args:
        name:        Module name ("math") or relative path ("./mymodule").
        caller_file: Absolute path of the importing .axb file.
        vm:          The caller's VM instance (used to wire recursive imports).
    """
    if name in _loading_set:
        raise AxonImportError(f"Circular import detected: '{name}'")

    file_path = _resolve_path(name, caller_file)
    if file_path is None:
        raise AxonImportError(f"Module not found: '{name}'")

    _loading_set.add(name)
    try:
        from core.compiler import compile_source
        from core.vm import VM
        from core.environment import Environment
        from stdlib.builtins import build_global_dict

        source = Path(file_path).read_text(encoding="utf-8")
        code = compile_source(source)

        module_globals = build_global_dict()
        module_vm = VM(module_globals)
        module_vm._module_loader = lambda n: load_module(n, str(file_path), module_vm)
        module_vm.run(code)

        # Wrap globals dict in an Environment for dot-access compatibility
        ns = Environment()
        for k, v in module_globals.items():
            ns.define(k, v)
        return ns

    finally:
        _loading_set.discard(name)


def _resolve_path(name: str, caller_file: str | None) -> str | None:
    if name.startswith("./") or name.startswith("../"):
        base = Path(caller_file).parent if caller_file else Path.cwd()
        if name.startswith("./"):
            candidate = base / (name[2:] + ".axb")
        else:
            candidate = base / (name + ".axb")
        return str(candidate) if candidate.exists() else None

    stdlib_path = _STDLIB_DIR / f"{name}.axb"
    if stdlib_path.exists():
        return str(stdlib_path)

    cwd_path = Path.cwd() / f"{name}.axb"
    if cwd_path.exists():
        return str(cwd_path)

    return None
