"""Lesson 162: add CPY absolute opcode ``0xCC``.

Why this step exists:
Absolute CPY compares Y with a byte anywhere in CPU memory and verifies the
two-byte operand is decoded as a little-endian address.

In this step, after lessons 159-161 provide ``cpy`` and its immediate and
zero-page handlers, add exactly the following to ``emulator/cpu/opcodes.py``:

    def cpy_absolute(cpu: CPU):
        addr = absolute(cpu)
        value = cpu.bus.read(addr)
        cpy(cpu, value)

    OPCODE_TABLE = {
        ...
        0xCC: cpy_absolute,
    }

``emulator/cpu/addressing_modes.py::absolute`` consumes a little-
endian address through ``CPU.fetch_word``; ``CC 00 02`` therefore compares Y
with the byte read from ``$0200`` via ``instructions.cpy``.

Invariants: Y and memory are unchanged; only C/Z/N change, and opcode plus the
two-byte operand advances PC by three bytes.  Misconception: ``00 02`` is not
the literal value ``0x0002`` to compare and is not a big-endian address.

Out of scope: relative addressing and branches begin at lesson 163.
"""
import inspect

from emulator.bus.cpu_bus import CpuBus
from emulator.cpu import opcodes
from emulator.cpu.cpu import CPU
from emulator.memory.fake_rom import FakeROM


CARRY_FLAG = 1 << 0


def make_cpu_with_rom():
    rom = FakeROM()
    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)
    bus = CpuBus(program_rom=rom)
    return CPU(bus), bus, rom


def test_cpy_absolute_handler_exists_and_is_in_opcode_table():
    """Objective: create cpy_absolute(cpu) and add 0xCC to OPCODE_TABLE."""
    assert hasattr(opcodes, "cpy_absolute")
    assert callable(opcodes.cpy_absolute)
    assert list(inspect.signature(opcodes.cpy_absolute).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xCC] is opcodes.cpy_absolute


def test_opcode_CC_cpy_absolute_reads_memory_value():
    """Objective: CC 00 02 means compare Y with RAM[$0200]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xCC)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0200, 0x10)

    cpu.reset()
    cpu.y = 0x20
    cpu.step()

    assert (cpu.p & CARRY_FLAG) != 0
    assert cpu.pc == 0x8003
