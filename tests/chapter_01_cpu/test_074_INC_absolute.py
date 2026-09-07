"""Lesson 074: wire INC Absolute (`0xEE`).

In this step, with `inc` already imported, add
`emulator/cpu/opcodes.py:inc_absolute` and `OPCODE_TABLE[0xEE]` only.

Why this step exists:
`addressing_modes.absolute` centralizes little-endian decoding of the
two-byte address while the existing INC primitive performs the read-modify-write.

Suggested implementation in `emulator/cpu/opcodes.py`:

    def inc_absolute(cpu: CPU):
        addr = absolute(cpu)
        inc(cpu, addr)

Add this exact entry to the existing `OPCODE_TABLE`:

    0xEE: inc_absolute,

Invariants: the low operand byte precedes the high byte; `absolute(cpu)` consumes
both and advances PC twice; `EE 00 02` targets `$0200`; total instruction length
is three bytes; INC updates memory and Z/N, not registers, Carry, or Overflow.

Misconception: do not reverse the operand bytes or pass the fetched byte value to
`inc`; the helper returns the effective 16-bit address.

Out of scope: `inc_absolute_x` and `OPCODE_TABLE[0xFE]` are lesson 075.
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


def test_inc_absolute_handler_exists_and_is_in_opcode_table():
    """Objective: create inc_absolute(cpu) and add 0xEE to OPCODE_TABLE."""
    assert hasattr(opcodes, "inc_absolute")
    assert callable(opcodes.inc_absolute)
    assert list(inspect.signature(opcodes.inc_absolute).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xEE] is opcodes.inc_absolute


def test_opcode_EE_inc_absolute_increments_memory():
    """Objective: EE 00 02 means INC $0200, so RAM[$0200] is incremented."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xEE)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0200, 0x41)

    cpu.reset()
    cpu.step()

    assert bus.read(0x0200) == 0x42
    assert cpu.pc == 0x8003
