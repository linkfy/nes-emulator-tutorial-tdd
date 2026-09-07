"""Lesson 075: wire INC Absolute,X (`0xFE`).

In this step, add `emulator/cpu/opcodes.py:inc_absolute_x` and
`OPCODE_TABLE[0xFE]` after the other INC forms from lessons 071-074.

Why this step exists:
Reuse `addressing_modes.absolute_x` so base-address decoding and X
indexing remain outside the INC read-modify-write primitive.

Suggested implementation in `emulator/cpu/opcodes.py`:

    def inc_absolute_x(cpu: CPU):
        addr = absolute_x(cpu)
        inc(cpu, addr)

Add this exact entry to the existing `OPCODE_TABLE`:

    0xFE: inc_absolute_x,

Invariants: two little-endian operand bytes are consumed; X is added to the
16-bit base address; PC advances by two after opcode fetch, making a three-byte
instruction; the resolved memory byte wraps modulo 256; only Z/N follow it.

Misconception: absolute-X indexing does not use zero-page wraparound. It may
cross a page, so `$02FF,X` with X=1 resolves to `$0300`.

Out of scope: DEC starts in lesson 076. Cycle-count and page-cross timing work
are not part of this step.
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


def test_inc_absolute_x_handler_exists_and_is_in_opcode_table():
    """Objective: create inc_absolute_x(cpu) and add 0xFE to OPCODE_TABLE."""
    assert hasattr(opcodes, "inc_absolute_x")
    assert callable(opcodes.inc_absolute_x)
    assert list(inspect.signature(opcodes.inc_absolute_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xFE] is opcodes.inc_absolute_x


def test_opcode_FE_inc_absolute_x_increments_indexed_memory():
    """Objective: FE 00 02 with X=0x04 increments RAM[$0204]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xFE)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0204, 0x41)

    cpu.reset()
    cpu.x = 0x04
    cpu.step()

    assert bus.read(0x0204) == 0x42
    assert cpu.pc == 0x8003
