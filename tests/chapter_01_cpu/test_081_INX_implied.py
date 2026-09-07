"""
Test 081 - Wire the INX implied opcode.

In this step, add only the INX opcode integration after Test 080 has provided
`instructions.inx`.

Production location and symbols:
    emulator/cpu/opcodes.py: imported `inx` and `OPCODE_TABLE[0xE8]`

Why this step exists:
INX has implied addressing, so dispatch can call the instruction function
directly. No wrapper or addressing-mode helper is needed.

Suggested implementation for this step:

    # emulator/cpu/opcodes.py
    from emulator.cpu.instructions import inx  # alongside existing imports

    OPCODE_TABLE = {
        # ... existing entries ...
        0xE8: inx,
    }

Important invariants:
    - opcode 0xE8 dispatches to the exact `inx(cpu)` function
    - no operand byte is fetched, so CPU.step advances PC by one byte
    - register wrapping and Z/N updates remain owned by test 080's `inx`

Common misconception:
Do not create an `inx_implied` wrapper; implied instructions can be direct table
entries, and a wrapper would add no decoding behavior.

Out of scope:
    - test 082's `dex` instruction behavior and test 083's DEX mapping
    - later INY/DEY and shift instructions
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


def test_inx_opcode_exists_and_is_in_opcode_table():
    """Objective: add 0xE8 to OPCODE_TABLE and point it to inx."""
    assert hasattr(opcodes, "inx")
    assert callable(opcodes.inx)
    assert list(inspect.signature(opcodes.inx).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xE8] is opcodes.inx


def test_opcode_E8_inx_implied_increments_x_register():
    """Objective: E8 means INX, so X is incremented and PC advances by 1."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xE8)

    cpu.reset()
    cpu.x = 0x10
    cpu.step()

    assert cpu.x == 0x11
    assert cpu.pc == 0x8001


def test_opcode_E8_inx_implied_updates_zero_flag():
    """Objective: X=0xFF wraps to 0x00 and sets Zero flag."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xE8)

    cpu.reset()
    cpu.x = 0xFF
    cpu.step()

    assert cpu.x == 0x00
    assert (cpu.p & ZERO_FLAG) != 0
    assert (cpu.p & NEGATIVE_FLAG) == 0


def test_opcode_E8_inx_implied_updates_negative_flag():
    """Objective: X=0x7F becomes 0x80 and sets Negative flag."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xE8)

    cpu.reset()
    cpu.x = 0x7F
    cpu.step()

    assert cpu.x == 0x80
    assert (cpu.p & NEGATIVE_FLAG) != 0
    assert (cpu.p & ZERO_FLAG) == 0
