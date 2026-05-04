"""
core/serializer.py — AxonBlade bytecode serialization (V2 Phase 3.4).

.axbc binary file format
------------------------
  Bytes 0-3:  magic  b'AXBC'
  Byte  4:    format version (currently 1)
  Bytes 5+:   serialized top-level CodeObject

CodeObject serialization is self-contained: every nested CodeObject
(function / method body) is stored recursively inside the parent's
constants list, so a single serialize/deserialize round-trip rebuilds
the complete object graph.

Value type tags (1 byte)
------------------------
  0x00  None (null)
  0x01  False
  0x02  True
  0x03  int   → signed 8-byte little-endian
  0x04  float → IEEE-754 double (8 bytes, little-endian)
  0x05  str   → uint32 length + UTF-8 bytes
  0x06  CodeObject (recursive)
  0x07  tuple  → uint32 length + serialized elements
  0x08  list   → uint32 length + serialized elements

Instruction arg serialization uses the same value tags.
"""

from __future__ import annotations

import struct
from typing import Any

from core.code_object import CodeObject, Instruction
from core.opcodes import Opcode

MAGIC   = b"AXBC"
VERSION = 1


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def serialize(code: CodeObject) -> bytes:
    """Serialize a CodeObject to bytes with the .axbc header."""
    buf = bytearray()
    _write_code(buf, code)
    header = MAGIC + struct.pack("<B", VERSION) + struct.pack("<I", len(buf))
    return bytes(header) + bytes(buf)


def _write_code(buf: bytearray, code: CodeObject) -> None:
    _write_str(buf, code.name)
    # constants
    _write_uint32(buf, len(code.constants))
    for c in code.constants:
        _write_value(buf, c)
    # names
    _write_strlist(buf, code.names)
    # instructions
    _write_uint32(buf, len(code.instructions))
    for instr in code.instructions:
        _write_instr(buf, instr)
    # param_names / param_types
    _write_strlist(buf, code.param_names)
    _write_uint32(buf, len(code.param_types))
    for pt in code.param_types:
        _write_value(buf, pt)
    # upvalue_names / cell_vars
    _write_strlist(buf, code.upvalue_names)
    _write_strlist(buf, code.cell_vars)


def _write_instr(buf: bytearray, instr: Instruction) -> None:
    buf.append(instr.opcode.value)
    _write_value(buf, instr.arg)


def _write_value(buf: bytearray, val: Any) -> None:  # noqa: C901
    if val is None:
        buf.append(0x00)
    elif val is False:
        buf.append(0x01)
    elif val is True:
        buf.append(0x02)
    elif isinstance(val, bool):  # must come before int
        buf.append(0x02 if val else 0x01)
    elif isinstance(val, int):
        buf.append(0x03)
        buf.extend(struct.pack("<q", val))
    elif isinstance(val, float):
        buf.append(0x04)
        buf.extend(struct.pack("<d", val))
    elif isinstance(val, str):
        buf.append(0x05)
        _write_str(buf, val)
    elif isinstance(val, CodeObject):
        buf.append(0x06)
        _write_code(buf, val)
    elif isinstance(val, tuple):
        buf.append(0x07)
        _write_uint32(buf, len(val))
        for item in val:
            _write_value(buf, item)
    elif isinstance(val, list):
        buf.append(0x08)
        _write_uint32(buf, len(val))
        for item in val:
            _write_value(buf, item)
    else:
        raise TypeError(f"Cannot serialize value of type {type(val).__name__!r}: {val!r}")


def _write_str(buf: bytearray, s: str) -> None:
    enc = s.encode("utf-8")
    _write_uint32(buf, len(enc))
    buf.extend(enc)


def _write_strlist(buf: bytearray, lst: list[str]) -> None:
    _write_uint32(buf, len(lst))
    for s in lst:
        _write_str(buf, s)


def _write_uint32(buf: bytearray, n: int) -> None:
    buf.extend(struct.pack("<I", n))


# ---------------------------------------------------------------------------
# Deserialization
# ---------------------------------------------------------------------------

def deserialize(data: bytes) -> CodeObject:
    """Deserialize bytes produced by serialize() back into a CodeObject."""
    if len(data) < 9:
        raise ValueError("File too short to be a valid .axbc file")
    if data[:4] != MAGIC:
        raise ValueError("Not an AXBC file (wrong magic bytes)")
    version = data[4]
    if version != VERSION:
        raise ValueError(f"Unsupported .axbc format version {version}")
    length = struct.unpack("<I", data[5:9])[0]
    payload = data[9:9 + length]
    view = memoryview(payload)
    code, pos = _read_code(view, 0)
    return code


class _Reader:
    """Mutable cursor over a memoryview for reading binary data."""

    def __init__(self, view: memoryview) -> None:
        self.view = view
        self.pos = 0

    def read(self, n: int) -> bytes:
        chunk = bytes(self.view[self.pos:self.pos + n])
        self.pos += n
        return chunk

    def read_uint8(self) -> int:
        b = self.view[self.pos]
        self.pos += 1
        return b

    def read_uint32(self) -> int:
        val = struct.unpack("<I", self.view[self.pos:self.pos + 4])[0]
        self.pos += 4
        return val

    def read_str(self) -> str:
        length = self.read_uint32()
        return self.read(length).decode("utf-8")

    def read_strlist(self) -> list[str]:
        n = self.read_uint32()
        return [self.read_str() for _ in range(n)]

    def read_value(self) -> Any:
        tag = self.read_uint8()
        if tag == 0x00:
            return None
        if tag == 0x01:
            return False
        if tag == 0x02:
            return True
        if tag == 0x03:
            return struct.unpack("<q", self.read(8))[0]
        if tag == 0x04:
            return struct.unpack("<d", self.read(8))[0]
        if tag == 0x05:
            return self.read_str()
        if tag == 0x06:
            return self.read_code()
        if tag == 0x07:
            n = self.read_uint32()
            return tuple(self.read_value() for _ in range(n))
        if tag == 0x08:
            n = self.read_uint32()
            return [self.read_value() for _ in range(n)]
        raise ValueError(f"Unknown value tag: 0x{tag:02x}")

    def read_code(self) -> CodeObject:
        name = self.read_str()
        n_const = self.read_uint32()
        constants = [self.read_value() for _ in range(n_const)]
        names = self.read_strlist()
        n_instr = self.read_uint32()
        instructions = []
        for _ in range(n_instr):
            opcode_val = self.read_uint8()
            opcode = Opcode(opcode_val)
            arg = self.read_value()
            instructions.append(Instruction(opcode, arg))
        param_names = self.read_strlist()
        n_pt = self.read_uint32()
        param_types = [self.read_value() for _ in range(n_pt)]
        upvalue_names = self.read_strlist()
        cell_vars = self.read_strlist()
        code = CodeObject(
            name=name,
            constants=constants,
            names=names,
            instructions=instructions,
            param_names=param_names,
            param_types=param_types,
            upvalue_names=upvalue_names,
            cell_vars=cell_vars,
        )
        return code


def _read_code(view: memoryview, start: int) -> tuple[CodeObject, int]:
    r = _Reader(view[start:])
    code = r.read_code()
    return code, start + r.pos
