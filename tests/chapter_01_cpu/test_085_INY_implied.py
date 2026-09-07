"""
Test 085 - Wire the INY implied opcode.

In this step, use `instructions.iny` from Test 084 and add only dispatch.

Production location and symbols:
    emulator/cpu/opcodes.py: imported `iny` and `OPCODE_TABLE[0xC8]`

Why this step exists:
Because Y is implied by INY, the opcode table can dispatch directly to the
instruction function without decoding an operand.

Suggested implementation for this step:

    # emulator/cpu/opcodes.py
    from emulator.cpu.instructions import iny  # alongside existing imports

    OPCODE_TABLE = {
        # ... existing entries ...
        0xC8: iny,
    }

Important invariants:
    - opcode 0xC8 maps to the exact `iny(cpu)` function
    - the one-byte instruction advances PC by one
    - wrapping and Z/N behavior remain in test 084's instruction function

Common misconception:
Do not use `immediate(cpu)` merely because the table needs a callable; INY has
no operand byte and an immediate decode would corrupt PC.

Out of scope:
    - DEY behavior and opcode mapping (tests 086-087)
    - later ASL instruction forms
    - cycle timing
"""
import inspect

from emulator.bus.cpu_bus import CpuBus
from emulator.cpu import opcodes
from emulator.cpu.cpu import CPU
from emulator.memory.fake_rom import FakeROM
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG


def make_cpu_with_rom():
    rom = FakeROM()
    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)
    bus = CpuBus(program_rom=rom)
    return CPU(bus), bus, rom


def test_iny_opcode_exists_and_is_in_opcode_table():
    """Objective: add 0xC8 to OPCODE_TABLE and point it to iny."""
    assert hasattr(opcodes, "iny")
    assert callable(opcodes.iny)
    assert list(inspect.signature(opcodes.iny).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xC8] is opcodes.iny


def test_opcode_C8_iny_implied_increments_y_register():
    """Objective: C8 means INY, so Y is incremented and PC advances by 1."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xC8)

    cpu.reset()
    cpu.y = 0x10
    cpu.step()

    assert cpu.y == 0x11
    assert cpu.pc == 0x8001


def test_opcode_C8_iny_implied_updates_zero_flag():
    """Objective: Y=0xFF wraps to 0x00 and sets Zero flag."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xC8)

    cpu.reset()
    cpu.y = 0xFF
    cpu.step()

    assert cpu.y == 0x00
    assert (cpu.p & ZERO_FLAG) != 0
    assert (cpu.p & NEGATIVE_FLAG) == 0


def test_opcode_C8_iny_implied_updates_negative_flag():
    """Objective: Y=0x7F becomes 0x80 and sets Negative flag."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xC8)

    cpu.reset()
    cpu.y = 0x7F
    cpu.step()

    assert cpu.y == 0x80
    assert (cpu.p & NEGATIVE_FLAG) != 0
    assert (cpu.p & ZERO_FLAG) == 0
