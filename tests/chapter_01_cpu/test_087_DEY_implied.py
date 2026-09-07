"""
Test 087 - Wire the DEY implied opcode.

In this step, use `instructions.dey` from Test 086 and add only its opcode
integration.

Production location and symbols:
    emulator/cpu/opcodes.py: imported `dey` and `OPCODE_TABLE[0x88]`

Why this step exists:
DEY's Y-register operand is implicit, allowing direct table dispatch with no
addressing-mode wrapper.

Suggested implementation for this step:

    # emulator/cpu/opcodes.py
    from emulator.cpu.instructions import dey  # alongside existing imports

    OPCODE_TABLE = {
        # ... existing entries ...
        0x88: dey,
    }

Important invariants:
    - opcode 0x88 dispatches to the exact `dey(cpu)` function
    - no operand is consumed and PC advances by one byte
    - Y wrapping and Z/N updates remain owned by test 086's `dey`

Common misconception:
Do not build a memory-decrement wrapper around `dec`; DEY modifies the register
and performs no bus read or write.

Out of scope:
    - prior INY behavior/mapping from tests 084-085
    - ASL behavior and opcodes beginning at test 088
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


def test_dey_opcode_exists_and_is_in_opcode_table():
    """Objective: add 0x88 to OPCODE_TABLE and point it to dey."""
    assert hasattr(opcodes, "dey")
    assert callable(opcodes.dey)
    assert list(inspect.signature(opcodes.dey).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x88] is opcodes.dey


def test_opcode_88_dey_implied_decrements_y_register():
    """Objective: 88 means DEY, so Y is decremented and PC advances by 1."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x88)

    cpu.reset()
    cpu.y = 0x10
    cpu.step()

    assert cpu.y == 0x0F
    assert cpu.pc == 0x8001


def test_opcode_88_dey_implied_updates_zero_flag():
    """Objective: Y=0x01 becomes 0x00 and sets Zero flag."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x88)

    cpu.reset()
    cpu.y = 0x01
    cpu.step()

    assert cpu.y == 0x00
    assert (cpu.p & ZERO_FLAG) != 0
    assert (cpu.p & NEGATIVE_FLAG) == 0


def test_opcode_88_dey_implied_updates_negative_flag():
    """Objective: Y=0x00 wraps to 0xFF and sets Negative flag."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x88)

    cpu.reset()
    cpu.y = 0x00
    cpu.step()

    assert cpu.y == 0xFF
    assert (cpu.p & NEGATIVE_FLAG) != 0
    assert (cpu.p & ZERO_FLAG) == 0
