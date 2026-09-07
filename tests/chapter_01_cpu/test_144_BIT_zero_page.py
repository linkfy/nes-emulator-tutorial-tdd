"""Lesson 144: add BIT zero-page opcode ``0x24``.

Why this step exists:
The first BIT opcode must fetch an operand from memory rather than modify A,
then delegate its distinct Z/N/V rules to the instruction primitive.

In this step, lesson 143 already adds ``bit``.  As BIT's first opcode lesson,
add its import and exactly the following handler/table entry in
``emulator/cpu/opcodes.py``:

    from emulator.cpu.instructions import (..., bit)

    def bit_zero_page(cpu: CPU):
        addr = zero_page(cpu)
        value = cpu.bus.read(addr)
        bit(cpu, value)

    OPCODE_TABLE = {
        ...
        0x24: bit_zero_page,
    }

``addressing_modes.zero_page`` consumes the operand as an address; the bus
read supplies the value whose bits BIT tests.  Z/N/V may change, while A,
Carry, X, Y, and memory are invariant; opcode plus operand advances PC two
bytes.

Misconception: the operand byte is not tested directly and BIT does not write
the addressed byte.  Out of scope: BIT absolute is lesson 145.
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


def test_bit_zero_page_handler_exists_and_is_in_opcode_table():
    """Objective: create bit_zero_page(cpu) and add 0x24 to OPCODE_TABLE."""
    assert hasattr(opcodes, "bit_zero_page")
    assert callable(opcodes.bit_zero_page)
    assert list(inspect.signature(opcodes.bit_zero_page).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x24] is opcodes.bit_zero_page


def test_opcode_24_bit_zero_page_sets_zero_from_a_and_memory_value():
    """Objective: 24 10 means BIT value at RAM[$0010]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x24)
    rom.write(0x0001, 0x10)
    bus.write(0x0010, 0b1111_0000)

    cpu.reset()
    cpu.a = 0b0000_1111
    cpu.step()

    assert (cpu.p & ZERO_FLAG) != 0
    assert cpu.a == 0b0000_1111
    assert bus.read(0x0010) == 0b1111_0000
    assert cpu.pc == 0x8002


def test_opcode_24_bit_zero_page_copies_memory_bits_7_and_6_to_n_and_v():
    """Objective: memory bits 7 and 6 are copied into Negative and Overflow."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x24)
    rom.write(0x0001, 0x10)
    bus.write(0x0010, 0b1100_0000)

    cpu.reset()
    cpu.a = 0x00
    cpu.step()

    assert (cpu.p & NEGATIVE_FLAG) != 0
    assert (cpu.p & OVERFLOW_FLAG) != 0
