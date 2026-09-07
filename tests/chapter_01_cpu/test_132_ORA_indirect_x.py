"""Lesson 132: add ORA (indirect,X) opcode ``0x01``.

Why this step exists:
Pre-indexed indirect ORA supports zero-page pointer tables and confirms that
pointer lookup is completed before the resulting memory value is ORed with A.

In this step, lesson 131 has completed the direct ORA modes.  Add exactly the
following to ``emulator/cpu/opcodes.py``:

    def ora_indirect_x(cpu: CPU):
        addr = indirect_x(cpu)
        value = cpu.bus.read(addr)
        or_a(cpu, value)

    OPCODE_TABLE = {
        ...
        0x01: ora_indirect_x,
    }

``emulator/cpu/addressing_modes.py::indirect_x`` fetches the operand, adds X
with zero-page wrapping, and reads a little-endian pointer whose high-byte
lookup also wraps in zero page.  The handler reads the pointed-to value and
delegates ORA flags/result to ``instructions.or_a``.  A and Z/N may change;
Carry/Overflow, memory, X, and Y remain invariant; PC advances two bytes.

Misconception: X is added before pointer dereferencing, not to the final
16-bit address.  Out of scope: ORA (indirect),Y (lesson 133) and EOR/BIT
(134-145).
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


def test_ora_indirect_x_handler_exists_and_is_in_opcode_table():
    """Objective: create ora_indirect_x(cpu) and add 0x01 to OPCODE_TABLE."""
    assert hasattr(opcodes, "ora_indirect_x")
    assert callable(opcodes.ora_indirect_x)
    assert list(inspect.signature(opcodes.ora_indirect_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x01] is opcodes.ora_indirect_x


def test_opcode_01_ora_indirect_x_reads_pointed_memory_value():
    """Objective: 01 20 with X=0x04 reads pointer at zero-page $24/$25."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x01)
    rom.write(0x0001, 0x20)
    bus.write(0x0024, 0x00)
    bus.write(0x0025, 0x02)
    bus.write(0x0200, 0x0F)

    cpu.reset()
    cpu.x = 0x04
    cpu.a = 0xF0
    cpu.step()

    assert cpu.a == 0xFF
    assert cpu.pc == 0x8002
