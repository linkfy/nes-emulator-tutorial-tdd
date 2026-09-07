"""Lesson 113: add ROR zero-page,X opcode ``0x76``.

In this step, with ``ror`` imported by lesson 112, add only the indexed
zero-page handler and table entry in ``emulator/cpu/opcodes.py``.

Why this step exists:
Indexed zero-page ROR must combine X with an eight-bit base address, including
zero-page wraparound, before applying the already-established rotation rules.

Suggested implementation:

    def ror_zero_page_x(cpu: CPU):
        addr = zero_page_x(cpu)
        ror(cpu, addr)

    OPCODE_TABLE = {
        ...
        0x76: ror_zero_page_x,
    }

``emulator/cpu/addressing_modes.py::zero_page_x`` fetches the base byte and
computes ``(base + cpu.x) & 0xFF``.  ``instructions.ror`` owns the memory
read/write and C/Z/N changes.  The invariant is zero-page wrapping: base
``0xFE`` plus X ``0x03`` targets ``0x0001``, never ``0x0101``; PC advances
two bytes and A is unchanged.

Misconception: ordinary integer addition is not sufficient for zero-page
indexing.  Out of scope: absolute and absolute,X ROR (lessons 114-115), and
any new rotate implementation or addressing helper.
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


def test_ror_zero_page_x_handler_exists_and_is_in_opcode_table():
    """Objective: create ror_zero_page_x(cpu) and add 0x76 to OPCODE_TABLE."""
    assert hasattr(opcodes, "ror_zero_page_x")
    assert callable(opcodes.ror_zero_page_x)
    assert list(inspect.signature(opcodes.ror_zero_page_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x76] is opcodes.ror_zero_page_x


def test_opcode_76_ror_zero_page_x_rotates_indexed_memory_value():
    """Objective: 76 20 with X=0x04 rotates RAM[$0024]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x76)
    rom.write(0x0001, 0x20)
    bus.write(0x0024, 0b0000_0110)

    cpu.reset()
    cpu.x = 0x04
    cpu.step()

    assert bus.read(0x0024) == 0b0000_0011
    assert cpu.pc == 0x8002


def test_opcode_76_ror_zero_page_x_wraps_zero_page_address():
    """Objective: zero-page indexed addresses wrap to 8 bits."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x76)
    rom.write(0x0001, 0xFE)
    bus.write(0x0001, 0x04)

    cpu.reset()
    cpu.x = 0x03
    cpu.step()

    assert bus.read(0x0001) == 0x02
    assert cpu.pc == 0x8002
