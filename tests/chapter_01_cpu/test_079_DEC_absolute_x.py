"""Lesson 079: wire DEC Absolute,X (`0xDE`).

In this step, add `emulator/cpu/opcodes.py:dec_absolute_x` and
`OPCODE_TABLE[0xDE]` after the DEC work from lessons 076-078.

Why this step exists:
Compose the established absolute-X address resolver with the DEC
primitive instead of duplicating indexing, bus access, or flag logic.

Suggested implementation in `emulator/cpu/opcodes.py`:

    def dec_absolute_x(cpu: CPU):
        addr = absolute_x(cpu)
        dec(cpu, addr)

Add this exact entry to the existing `OPCODE_TABLE`:

    0xDE: dec_absolute_x,

Invariants: the two-byte base address is little-endian; X participates only in
effective-address resolution and is unchanged; page crossing is allowed; PC
advances by two operand bytes; DEC stores an 8-bit result and changes only Z/N.

Misconception: this instruction decrements memory at `base + X`, not the X
register. Register decrement is the later DEX instruction.

Out of scope: INX/DEX primitives and their implied opcodes are lessons 080-083;
cycle accounting is not part of this step.
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


def test_dec_absolute_x_handler_exists_and_is_in_opcode_table():
    """Objective: create dec_absolute_x(cpu) and add 0xDE to OPCODE_TABLE."""
    assert hasattr(opcodes, "dec_absolute_x")
    assert callable(opcodes.dec_absolute_x)
    assert list(inspect.signature(opcodes.dec_absolute_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xDE] is opcodes.dec_absolute_x


def test_opcode_DE_dec_absolute_x_decrements_indexed_memory():
    """Objective: DE 00 02 with X=0x04 decrements RAM[$0204]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xDE)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0204, 0x42)

    cpu.reset()
    cpu.x = 0x04
    cpu.step()

    assert bus.read(0x0204) == 0x41
    assert cpu.pc == 0x8003
