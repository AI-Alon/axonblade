"""
core/module_loader.py — AxonBlade module system (Week 7, Phase 7.3).

Implements module loading per ProjectPlan.md §12:
  1. Check stdlib/{name}.axb
  2. Check ./{name}.axb relative to the current file
  3. Raise AxonImportError if not found
  4. Track currently-loading modules to detect circular imports

Returns an Environment (namespace object) for dot-access.
"""

from __future__ import annotations

import os
from pathlib import Path

from core.errors import AxonImportError


# Set of module names currently being loaded — circular import detection
_loading_set: set[str] = set()

# Path to the stdlib directory (sibling of core/)
_STDLIB_DIR = Path(__file__).parent.parent / "stdlib"


def load_module(name: str, caller_file: str | None = None,
                evaluator=None, global_env_builder=None) -> object:
    """
    Load an AxonBlade module by name and return its Environment namespace.

    Args:
        name: Module name (e.g. "math") or relative path (e.g. "./mymodule").
        caller_file: Absolute path of the importing .axb file (for relative paths).
        evaluator: The Evaluator instance to use for running the module.
        global_env_builder: Callable that returns a fresh global Environment.

    Returns:
        An Environment object whose store holds the module's exported names.
    """
    if evaluator is None or global_env_builder is None:
        raise AxonImportError("Module loader not fully configured")

    # Circular import guard
    if name in _loading_set:
        raise AxonImportError(f"Circular import detected: '{name}'")

    # Resolve the file path
    file_path = _resolve_path(name, caller_file)
    if file_path is None:
        raise AxonImportError(f"Module not found: '{name}'")

    _loading_set.add(name)
    try:
        source = Path(file_path).read_text(encoding="utf-8")
        from core.parser import parse_source
        prog = parse_source(source)
        module_env = global_env_builder()
        # Set up module loader recursively
        evaluator._module_loader = lambda n, _line: load_module(
            n, str(file_path), evaluator, global_env_builder
        )
        evaluator.eval(prog, module_env)
        return module_env
    finally:
        _loading_set.discard(name)


def _resolve_path(name: str, caller_file: str | None) -> str | None:
    """Find the .axb file for *name*, returning its path or None."""
    # Relative path import: "./mymodule" or "../lib"
    if name.startswith("./") or name.startswith("../"):
        if caller_file:
            base = Path(caller_file).parent
        else:
            base = Path.cwd()
        candidate = base / (name.lstrip("./").lstrip("../") + ".axb")
        if not name.startswith("./"):
            candidate = base / (name + ".axb")
        else:
            candidate = base / (name[2:] + ".axb")
        return str(candidate) if candidate.exists() else None

    # stdlib lookup
    stdlib_path = _STDLIB_DIR / f"{name}.axb"
    if stdlib_path.exists():
        return str(stdlib_path)

    # Current working directory
    cwd_path = Path.cwd() / f"{name}.axb"
    if cwd_path.exists():
        return str(cwd_path)

    return None
