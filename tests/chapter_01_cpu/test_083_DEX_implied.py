"""
Test 083 - Wire the DEX implied opcode.

In this step, use `instructions.dex` from Test 082 and add only its opcode
integration.

Production location and symbols:
    emulator/cpu/opcodes.py: imported `dex` and `OPCODE_TABLE[0xCA]`

Why this step exists:
DEX has no explicit operand, so its opcode maps directly to `dex(cpu)` without
an addressing wrapper.

Suggested implementation for this step:

    # emulator/cpu/opcodes.py
    from emulator.cpu.instructions import dex  # alongside existing imports

    OPCODE_TABLE = {
        # ... existing entries ...
        0xCA: dex,
    }

Important invariants:
    - opcode 0xCA resolves to the exact `dex` function
    - no addressing helper consumes bytes, so PC advances by exactly one
    - test 082's function remains responsible for X wrapping and Z/N flags

Common misconception:
The implied operand is X itself; do not fetch a byte and treat it as an address
or decrement memory.

Out of scope:
    - the already completed INX behavior/mapping from tests 080-081
    - tests 084-087's INY/DEY work
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


def test_dex_opcode_exists_and_is_in_opcode_table():
    """Objective: add 0xCA to OPCODE_TABLE and point it to dex."""
    assert hasattr(opcodes, "dex")
    assert callable(opcodes.dex)
    assert list(inspect.signature(opcodes.dex).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xCA] is opcodes.dex


def test_opcode_CA_dex_implied_decrements_x_register():
    """Objective: CA means DEX, so X is decremented and PC advances by 1."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xCA)

    cpu.reset()
    cpu.x = 0x10
    cpu.step()

    assert cpu.x == 0x0F
    assert cpu.pc == 0x8001


def test_opcode_CA_dex_implied_updates_zero_flag():
    """Objective: X=0x01 becomes 0x00 and sets Zero flag."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xCA)

    cpu.reset()
    cpu.x = 0x01
    cpu.step()

    assert cpu.x == 0x00
    assert (cpu.p & ZERO_FLAG) != 0
    assert (cpu.p & NEGATIVE_FLAG) == 0


def test_opcode_CA_dex_implied_updates_negative_flag():
    """Objective: X=0x00 wraps to 0xFF and sets Negative flag."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xCA)

    cpu.reset()
    cpu.x = 0x00
    cpu.step()

    assert cpu.x == 0xFF
    assert (cpu.p & NEGATIVE_FLAG) != 0
    assert (cpu.p & ZERO_FLAG) == 0
