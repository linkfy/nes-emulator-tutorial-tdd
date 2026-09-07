"""Lesson 077: wire DEC Zero Page,X (`0xD6`).

In this step, with `dec` imported by lesson 076, add
`emulator/cpu/opcodes.py:dec_zero_page_x` and `OPCODE_TABLE[0xD6]` only.

Why this step exists:
Delegate indexed page-zero address calculation to the existing
addressing helper and memory mutation to the existing DEC primitive.

Suggested implementation in `emulator/cpu/opcodes.py`:

    def dec_zero_page_x(cpu: CPU):
        addr = zero_page_x(cpu)
        dec(cpu, addr)

Add this exact entry to the existing `OPCODE_TABLE`:

    0xD6: dec_zero_page_x,

Invariants: one operand byte is consumed; base plus X wraps at `$FF` within page
zero; PC advances to the next two-byte instruction; DEC writes an 8-bit result
and updates only Z/N.

Misconception: `$FF,X` with X=1 does not target `$0100`; zero-page indexed
addressing resolves `$0000` before DEC runs.

Out of scope: `dec_absolute`/`0xCE` and `dec_absolute_x`/`0xDE` are lessons
078-079.
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


def test_dec_zero_page_x_handler_exists_and_is_in_opcode_table():
    """Objective: create dec_zero_page_x(cpu) and add 0xD6 to OPCODE_TABLE."""
    assert hasattr(opcodes, "dec_zero_page_x")
    assert callable(opcodes.dec_zero_page_x)
    assert list(inspect.signature(opcodes.dec_zero_page_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xD6] is opcodes.dec_zero_page_x


def test_opcode_D6_dec_zero_page_x_decrements_indexed_memory():
    """Objective: D6 10 with X=0x03 decrements RAM[$0013]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xD6)
    rom.write(0x0001, 0x10)
    bus.write(0x0013, 0x42)

    cpu.reset()
    cpu.x = 0x03
    cpu.step()

    assert bus.read(0x0013) == 0x41
    assert cpu.pc == 0x8002


def test_opcode_D6_dec_zero_page_x_wraps_inside_page_zero():
    """Objective: Zero Page,X wraps before DEC modifies memory."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xD6)
    rom.write(0x0001, 0xFF)
    bus.write(0x0000, 0x42)

    cpu.reset()
    cpu.x = 0x01
    cpu.step()

    assert bus.read(0x0000) == 0x41
    assert cpu.pc == 0x8002
