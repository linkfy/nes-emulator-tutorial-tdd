"""Lesson 142: add EOR (indirect),Y opcode ``0x51``.

Why this step exists:
This completes EOR addressing coverage with post-indexed pointer access, using
the indirect,Y helper before passing the fetched value to the EOR primitive.

In this step, lesson 141 completes the other indirect EOR form.  Add exactly
the following to
``emulator/cpu/opcodes.py``:

    def eor_indirect_y(cpu: CPU):
        addr = indirect_y(cpu)
        value = cpu.bus.read(addr)
        or_e(cpu, value)

    OPCODE_TABLE = {
        ...
        0x51: eor_indirect_y,
    }

``emulator/cpu/addressing_modes.py::indirect_y`` first reads the wrapped
little-endian pointer from zero page and then adds Y to that target.  The
handler reads the resulting address and passes its value to ``or_e``.  A and
Z/N may change; Carry, Overflow, X, Y, and memory remain invariant; PC advances
two bytes.

Misconception: Y does not select the zero-page pointer bytes; it indexes the
decoded target.  Out of scope: BIT behavior and opcodes are lessons 143-145.
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


def test_eor_indirect_y_handler_exists_and_is_in_opcode_table():
    """Objective: create eor_indirect_y(cpu) and add 0x51 to OPCODE_TABLE."""
    assert hasattr(opcodes, "eor_indirect_y")
    assert callable(opcodes.eor_indirect_y)
    assert list(inspect.signature(opcodes.eor_indirect_y).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x51] is opcodes.eor_indirect_y


def test_opcode_51_eor_indirect_y_reads_pointed_indexed_memory_value():
    """Objective: 51 20 reads pointer at $20/$21, then adds Y."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x51)
    rom.write(0x0001, 0x20)
    bus.write(0x0020, 0x00)
    bus.write(0x0021, 0x02)
    bus.write(0x0204, 0x0F)

    cpu.reset()
    cpu.y = 0x04
    cpu.a = 0xF0
    cpu.step()

    assert cpu.a == 0xFF
    assert cpu.pc == 0x8002
