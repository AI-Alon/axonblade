from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from core.opcodes import Opcode


@dataclass
class Instruction:
    opcode: Opcode
    arg: Any = None  # int index, str name, or None depending on opcode


@dataclass
class CodeObject:
    name: str
    constants: list[Any] = field(default_factory=list)
    names: list[str] = field(default_factory=list)
    instructions: list[Instruction] = field(default_factory=list)
    param_names: list[str] = field(default_factory=list)
    param_types: list[str | None] = field(default_factory=list)
    upvalue_names: list[str] = field(default_factory=list)
    cell_vars: list[str] = field(default_factory=list)  # locals captured by inner fns

    def add_constant(self, value: Any) -> int:
        """Intern a constant and return its index."""
        try:
            return self.constants.index(value)
        except ValueError:
            self.constants.append(value)
            return len(self.constants) - 1

    def add_name(self, name: str) -> int:
        """Intern a name and return its index."""
        if name not in self.names:
            self.names.append(name)
        return self.names.index(name)

    def emit(self, opcode: Opcode, arg: Any = None) -> int:
        """Append an instruction and return its offset."""
        self.instructions.append(Instruction(opcode, arg))
        return len(self.instructions) - 1

    def patch(self, offset: int, arg: Any) -> None:
        """Patch the arg of the instruction at offset (used for forward jumps)."""
        self.instructions[offset].arg = arg

    def __repr__(self) -> str:
        lines = [f"<CodeObject {self.name!r}>"]
        for i, instr in enumerate(self.instructions):
            lines.append(f"  {i:4d}  {instr.opcode.name:<20} {instr.arg!r}")
        return "\n".join(lines)
