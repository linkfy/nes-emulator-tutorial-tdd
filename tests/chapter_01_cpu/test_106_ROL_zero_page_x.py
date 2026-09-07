"""Lesson 106: wire ROL Zero Page,X (opcode ``0x36``).

In this step, extend lesson 105 with only the indexed zero-page adapter and
dispatch entry.

Complete example implementation in the production locations:

``emulator/cpu/opcodes.py::rol_zero_page_x``::

    def rol_zero_page_x(cpu: CPU):
        addr = zero_page_x(cpu)
        rol(cpu, addr)

``emulator/cpu/opcodes.py::OPCODE_TABLE``::

    0x36: rol_zero_page_x,

Why this step exists:
Reuse the established addressing helper so wrapping policy is not
duplicated in the instruction primitive.

Invariants: one operand byte is consumed; effective address is
``(operand + cpu.x) & 0xFF``; PC ends at start+2; ``rol`` mutates only that
byte with the C/Z/N behavior from lesson 102.  Base ``0xFE`` plus X ``0x03``
therefore targets ``$0001``.

Misconception: zero-page indexing does not spill into ``$0101`` and is not
16-bit absolute indexing; wrapping to eight bits is required.

Out of scope: absolute modes are lessons 107-108, ROR starts at 109, and
cycle-accurate indexed read/modify/write sequencing is later work.
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


def test_rol_zero_page_x_handler_exists_and_is_in_opcode_table():
    """Objective: create rol_zero_page_x(cpu) and add 0x36 to OPCODE_TABLE."""
    assert hasattr(opcodes, "rol_zero_page_x")
    assert callable(opcodes.rol_zero_page_x)
    assert list(inspect.signature(opcodes.rol_zero_page_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x36] is opcodes.rol_zero_page_x


def test_opcode_36_rol_zero_page_x_rotates_indexed_memory_value():
    """Objective: 36 20 with X=0x04 rotates RAM[$0024]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x36)
    rom.write(0x0001, 0x20)
    bus.write(0x0024, 0b0000_0011)

    cpu.reset()
    cpu.x = 0x04
    cpu.step()

    assert bus.read(0x0024) == 0b0000_0110
    assert cpu.pc == 0x8002


def test_opcode_36_rol_zero_page_x_wraps_zero_page_address():
    """Objective: zero-page indexed addresses wrap to 8 bits."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x36)
    rom.write(0x0001, 0xFE)
    bus.write(0x0001, 0x02)

    cpu.reset()
    cpu.x = 0x03
    cpu.step()

    assert bus.read(0x0001) == 0x04
    assert cpu.pc == 0x8002
