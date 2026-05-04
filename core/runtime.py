"""
core/runtime.py — AxonBlade VM runtime value types (V2 Phase 3.2+).

Shared between the compiler, VM, builtins, test runner, and REPL.
Replaces the runtime types previously defined in core/evaluator.py.
"""

from __future__ import annotations


class Cell:
    """Heap-allocated box for a closure-captured variable."""

    __slots__ = ("value",)

    def __init__(self, value: object) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"Cell({self.value!r})"


class AxonFunction:
    """A compiled AxonBlade function closure."""

    def __init__(self, code: object, captured_cells: list[Cell]) -> None:
        self.code = code                        # CodeObject
        self.captured_cells = captured_cells    # parallel to code.upvalue_names

    def __repr__(self) -> str:
        return f"<bladeFN {self.code.name}>"


class AxonBladeGRP:
    """A bladeGRP class — a named collection of method AxonFunctions."""

    def __init__(self, name: str, methods: dict) -> None:
        self.name = name
        self.methods = methods  # dict[str, AxonFunction]

    def __repr__(self) -> str:
        return f"<bladeGRP {self.name}>"


class AxonInstance:
    """An instance of an AxonBladeGRP class."""

    def __init__(self, klass: AxonBladeGRP) -> None:
        self.klass = klass
        self.fields: dict = {}

    def get_attr(self, name: str) -> object:
        from core.errors import AxonNameError
        if name in self.fields:
            return self.fields[name]
        if name in self.klass.methods:
            return BoundMethod(self, self.klass.methods[name])
        raise AxonNameError(f"No attribute '{name}' on {self.klass.name} instance")

    def set_field(self, name: str, value: object) -> None:
        self.fields[name] = value

    def __repr__(self) -> str:
        return f"<{self.klass.name} instance>"


class BoundMethod:
    """A method bound to an AxonInstance (created on dot-access)."""

    def __init__(self, instance: AxonInstance, fn: AxonFunction) -> None:
        self.instance = instance
        self.fn = fn

    def __repr__(self) -> str:
        return f"<bound method {self.fn.code.name}>"
