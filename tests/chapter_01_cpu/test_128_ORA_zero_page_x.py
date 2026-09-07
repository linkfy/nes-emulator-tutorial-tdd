"""Lesson 128: add ORA zero-page,X opcode ``0x15``.

Why this step exists:
This enables compact indexed ORA access and verifies that adding X obeys
zero-page wraparound before the selected byte is combined with A.

In this step, following lesson 127, add only this handler and table entry to
``emulator/cpu/opcodes.py``:

    def ora_zero_page_x(cpu: CPU):
        addr = zero_page_x(cpu)
        value = cpu.bus.read(addr)
        or_a(cpu, value)

    OPCODE_TABLE = {
        ...
        0x15: ora_zero_page_x,
    }

``emulator/cpu/addressing_modes.py::zero_page_x`` computes
``(base + cpu.x) & 0xFF`` before the bus read.  The resolved value feeds
``instructions.or_a``; A and Z/N change, X, Carry/Overflow, and memory do not,
and PC advances two bytes.  Thus base ``0xFE`` plus X ``0x03`` reads
``$0001``.

Misconception: zero-page indexing wraps to ``$0001``, not ``$0101``; X does
not alter the loaded value.  Out of scope: absolute and indirect ORA modes
(lessons 129-133).
"""
import inspect

from emulator.bus.cpu_bus import CpuBus
from emulator.cpu import opcodes
from emulator.cpu.cpu import CPU
from emulator.memory.fake_rom import FakeROM


def make_cpu_with_rom():
    rom = FakeROM()
    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)
    bus = CpuBus(program_rom=rom)
    return CPU(bus), bus, rom


def test_ora_zero_page_x_handler_exists_and_is_in_opcode_table():
    """Objective: create ora_zero_page_x(cpu) and add 0x15 to OPCODE_TABLE."""
    assert hasattr(opcodes, "ora_zero_page_x")
    assert callable(opcodes.ora_zero_page_x)
    assert list(inspect.signature(opcodes.ora_zero_page_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x15] is opcodes.ora_zero_page_x


def test_opcode_15_ora_zero_page_x_reads_indexed_memory_value():
    """Objective: 15 20 with X=0x04 reads RAM[$0024]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x15)
    rom.write(0x0001, 0x20)
    bus.write(0x0024, 0x0F)

    cpu.reset()
    cpu.x = 0x04
    cpu.a = 0xF0
    cpu.step()

    assert cpu.a == 0xFF
    assert cpu.pc == 0x8002


def test_opcode_15_ora_zero_page_x_wraps_zero_page_address():
    """Objective: base=0xFE and X=0x03 reads RAM[$0001]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x15)
    rom.write(0x0001, 0xFE)
    bus.write(0x0001, 0x0F)

    cpu.reset()
    cpu.x = 0x03
    cpu.a = 0xF0
    cpu.step()

    assert cpu.a == 0xFF
    assert cpu.pc == 0x8002
