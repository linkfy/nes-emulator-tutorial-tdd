"""Lesson 115: complete ROR with absolute,X opcode ``0x7E``.

In this step, after lesson 114, add only the Absolute,X handler and table entry
in ``emulator/cpu/opcodes.py``.

Why this step exists:
This completes ROR addressing coverage by resolving a full little-endian base
address plus X before rotating the selected memory byte.

Suggested implementation:

    def ror_absolute_x(cpu: CPU):
        addr = absolute_x(cpu)
        ror(cpu, addr)

    OPCODE_TABLE = {
        ...
        0x7E: ror_absolute_x,
    }

``emulator/cpu/addressing_modes.py::absolute_x`` fetches the little-endian
16-bit base and then adds ``cpu.x``.  ``7E 00 02`` with X ``0x04`` therefore
read/modifies/writes ``$0204`` through ``instructions.ror``.  A stays fixed,
C/Z/N retain ROR semantics, and PC advances three bytes.  Unlike zero-page,X,
absolute,X does not wrap at ``$00FF``.

Misconception: X indexes the decoded address, not either operand byte or the
loaded value.  Out of scope: cycle/page-cross timing and all AND work, which
starts at lesson 116; no additional ROR modes were added after this lesson.
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


def test_ror_absolute_x_handler_exists_and_is_in_opcode_table():
    """Objective: create ror_absolute_x(cpu) and add 0x7E to OPCODE_TABLE."""
    assert hasattr(opcodes, "ror_absolute_x")
    assert callable(opcodes.ror_absolute_x)
    assert list(inspect.signature(opcodes.ror_absolute_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x7E] is opcodes.ror_absolute_x


def test_opcode_7E_ror_absolute_x_rotates_indexed_memory_value():
    """Objective: 7E 00 02 with X=0x04 rotates RAM[$0204]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x7E)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0204, 0b0000_0110)

    cpu.reset()
    cpu.x = 0x04
    cpu.step()

    assert bus.read(0x0204) == 0b0000_0011
    assert cpu.pc == 0x8003
