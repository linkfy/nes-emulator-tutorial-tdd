"""Lesson 124: add AND (indirect),Y opcode ``0x31``.

Why this step exists:
This completes AND addressing coverage with a zero-page pointer followed by Y
indexing, reusing both the indirect helper and the common AND primitive.

In this step, complete the numbered AND modes by adding the following to
``emulator/cpu/opcodes.py``:

    def and_indirect_y(cpu: CPU):
        addr = indirect_y(cpu)
        value = cpu.bus.read(addr)
        and_a(cpu, value)

    OPCODE_TABLE = {
        ...
        0x31: and_indirect_y,
    }

``emulator/cpu/addressing_modes.py::indirect_y`` fetches a zero-page pointer
location, reads its little-endian word with zero-page wrapping for the high
byte, and only then adds ``cpu.y``.  The target value goes to
``instructions.and_a``.  A and Z/N change; Y, Carry/Overflow, pointer bytes,
and target memory remain invariant; PC advances two bytes.

Misconception: (indirect),Y does not add Y to the zero-page pointer location;
that ordering belongs to (indirect,X).  Out of scope: ORA, EOR, and BIT work,
beginning with lesson 125.
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


def test_and_indirect_y_handler_exists_and_is_in_opcode_table():
    """Objective: create and_indirect_y(cpu) and add 0x31 to OPCODE_TABLE."""
    assert hasattr(opcodes, "and_indirect_y")
    assert callable(opcodes.and_indirect_y)
    assert list(inspect.signature(opcodes.and_indirect_y).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x31] is opcodes.and_indirect_y


def test_opcode_31_and_indirect_y_reads_pointed_indexed_memory_value():
    """Objective: 31 20 reads pointer at $20/$21, then adds Y."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x31)
    rom.write(0x0001, 0x20)
    bus.write(0x0020, 0x00)
    bus.write(0x0021, 0x02)
    bus.write(0x0204, 0x0F)

    cpu.reset()
    cpu.y = 0x04
    cpu.a = 0xF3
    cpu.step()

    assert cpu.a == 0x03
    assert cpu.pc == 0x8002
