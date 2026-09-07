"""Lesson 114: add ROR absolute opcode ``0x6E``.

In this step, use the instruction and addressing imports from prior lessons and
add only the absolute handler and table entry in ``emulator/cpu/opcodes.py``.

Why this step exists:
ROR needs a full-address memory form so programs can rotate bytes outside the
zero page while reusing the same read-modify-write instruction primitive.

Suggested implementation:

    def ror_absolute(cpu: CPU):
        addr = absolute(cpu)
        ror(cpu, addr)

    OPCODE_TABLE = {
        ...
        0x6E: ror_absolute,
    }

``emulator/cpu/addressing_modes.py::absolute`` calls ``CPU.fetch_word`` and
therefore decodes the low byte before the high byte.  ``6E 00 02`` rotates
the byte at ``$0200`` through Carry via ``instructions.ror``.  Memory is
read/modified/written once conceptually, A is unchanged, C/Z/N follow the
rotate result, and the opcode plus two-byte operand advances PC by three.

Misconception: ``00 02`` is not address ``$0002`` and is not itself the data
to rotate.  Out of scope: adding X (lesson 115), changing ``absolute``, or
reimplementing ``ror`` in the handler.
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


def test_ror_absolute_handler_exists_and_is_in_opcode_table():
    """Objective: create ror_absolute(cpu) and add 0x6E to OPCODE_TABLE."""
    assert hasattr(opcodes, "ror_absolute")
    assert callable(opcodes.ror_absolute)
    assert list(inspect.signature(opcodes.ror_absolute).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x6E] is opcodes.ror_absolute


def test_opcode_6E_ror_absolute_rotates_memory_value():
    """Objective: 6E 00 02 means ROR $0200, so RAM[$0200] is rotated."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x6E)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0200, 0b0000_0110)

    cpu.reset()
    cpu.step()

    assert bus.read(0x0200) == 0b0000_0011
    assert cpu.pc == 0x8003
