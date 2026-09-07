"""Lesson 119: add AND zero-page,X opcode ``0x35``.

In this step, after lesson 118, add only the indexed zero-page handler and table
entry in ``emulator/cpu/opcodes.py``.

Why this step exists:
This adds indexed access to zero-page AND and verifies that address calculation
wraps within the zero page before the memory value reaches the AND primitive.

Suggested implementation:

    def and_zero_page_x(cpu: CPU):
        addr = zero_page_x(cpu)
        value = cpu.bus.read(addr)
        and_a(cpu, value)

    OPCODE_TABLE = {
        ...
        0x35: and_zero_page_x,
    }

``emulator/cpu/addressing_modes.py::zero_page_x`` computes
``(base + cpu.x) & 0xFF``.  The resolved byte is read once conceptually and
passed to ``instructions.and_a``: A and Z/N change, Carry/Overflow and memory
do not, and PC advances two bytes.  Base ``0xFE`` plus X ``0x03`` must read
``$0001``, not ``$0101``.

Misconception: indexing does not alter the data and must wrap before the bus
read.  Out of scope: absolute through indirect,Y AND (lessons 120-124), and
changes to the already-existing addressing helper or instruction semantics.
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


def test_and_zero_page_x_handler_exists_and_is_in_opcode_table():
    """Objective: create and_zero_page_x(cpu) and add 0x35 to OPCODE_TABLE."""
    assert hasattr(opcodes, "and_zero_page_x")
    assert callable(opcodes.and_zero_page_x)
    assert list(inspect.signature(opcodes.and_zero_page_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x35] is opcodes.and_zero_page_x


def test_opcode_35_and_zero_page_x_reads_indexed_memory_value():
    """Objective: 35 20 with X=0x04 reads RAM[$0024]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x35)
    rom.write(0x0001, 0x20)
    bus.write(0x0024, 0x0F)

    cpu.reset()
    cpu.x = 0x04
    cpu.a = 0xF3
    cpu.step()

    assert cpu.a == 0x03
    assert cpu.pc == 0x8002


def test_opcode_35_and_zero_page_x_wraps_zero_page_address():
    """Objective: base=0xFE and X=0x03 reads RAM[$0001]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x35)
    rom.write(0x0001, 0xFE)
    bus.write(0x0001, 0x0F)

    cpu.reset()
    cpu.x = 0x03
    cpu.a = 0xF3
    cpu.step()

    assert cpu.a == 0x03
    assert cpu.pc == 0x8002
