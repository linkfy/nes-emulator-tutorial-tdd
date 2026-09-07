"""Lesson 145: add BIT absolute opcode ``0x2C``.

Why this step exists:
Absolute BIT extends the flag-only test to the full address space and verifies
that its two-byte operand is decoded as a little-endian memory address.

In this step, with BIT semantics and its opcode import established in lessons
143-144, add exactly the following to ``emulator/cpu/opcodes.py``:

    def bit_absolute(cpu: CPU):
        addr = absolute(cpu)
        value = cpu.bus.read(addr)
        bit(cpu, value)

    OPCODE_TABLE = {
        ...
        0x2C: bit_absolute,
    }

``emulator/cpu/addressing_modes.py::absolute`` uses ``CPU.fetch_word`` to
decode the little-endian address.  The handler performs one bus read and BIT
only consumes that value.  Z/N/V may change; A, Carry, X, Y, and memory remain
invariant; opcode plus word advances PC three bytes.

Misconception: ``2C 02 20`` does not test literal ``$2002``; it reads that
address, with any bus-owned side effects remaining bus behavior.  Out of scope:
CMP and its compare opcodes begin in lesson 146.
"""
import inspect

from emulator.bus.cpu_bus import CpuBus
from emulator.cpu import opcodes
from emulator.cpu.cpu import CPU
from emulator.memory.fake_rom import FakeROM
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG


OVERFLOW_FLAG = 1 << 6


def make_cpu_with_rom():
    rom = FakeROM()
    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)
    bus = CpuBus(program_rom=rom)
    return CPU(bus), bus, rom


def test_bit_absolute_handler_exists_and_is_in_opcode_table():
    """Objective: create bit_absolute(cpu) and add 0x2C to OPCODE_TABLE."""
    assert hasattr(opcodes, "bit_absolute")
    assert callable(opcodes.bit_absolute)
    assert list(inspect.signature(opcodes.bit_absolute).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x2C] is opcodes.bit_absolute


def test_opcode_2C_bit_absolute_sets_zero_from_a_and_memory_value():
    """Objective: 2C 00 02 means BIT value at RAM[$0200]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x2C)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0200, 0b1111_0000)

    cpu.reset()
    cpu.a = 0b0000_1111
    cpu.step()

    assert (cpu.p & ZERO_FLAG) != 0
    assert cpu.a == 0b0000_1111
    assert bus.read(0x0200) == 0b1111_0000
    assert cpu.pc == 0x8003


def test_opcode_2C_bit_absolute_copies_memory_bits_7_and_6_to_n_and_v():
    """Objective: memory bits 7 and 6 are copied into Negative and Overflow."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x2C)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0200, 0b1100_0000)

    cpu.reset()
    cpu.a = 0x00
    cpu.step()

    assert (cpu.p & NEGATIVE_FLAG) != 0
    assert (cpu.p & OVERFLOW_FLAG) != 0
