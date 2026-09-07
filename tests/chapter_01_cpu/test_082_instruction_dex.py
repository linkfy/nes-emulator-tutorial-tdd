"""
Test 082 - Add DEX instruction behavior.

In this step, add only the instruction function. Opcode 0xCA is the following
Test 083 step.

Production location and symbol:
    emulator/cpu/instructions.py: `dex(cpu: CPU)`

Why this step exists:
DEX is register behavior independent of opcode decoding. Python integers do not
wrap automatically, so subtraction must be normalized to an 8-bit result.

Suggested implementation:

    def dex(cpu: CPU):
        result = cpu.x - 1
        result_8 = result & 0xFF

        # Set flags
        cpu.flags.set_negative_flag((result_8 & 0b1000_0000) != 0)
        cpu.flags.set_zero_flag(result_8 == 0)

        cpu.x = result_8

Important invariants:
    - X wraps from 0x00 to 0xFF through `& 0xFF`
    - Zero and Negative are derived from the final 8-bit value
    - Carry, Overflow, memory, and all other registers are untouched

Common misconception:
DEX is not subtraction through SBC: it neither consumes nor changes Carry and
does not apply SBC's overflow rules.

Out of scope:
    - importing `dex` into opcodes and mapping 0xCA (test 083)
    - later Y-register increments/decrements
    - cycle timing
"""

from emulator.cpu.instructions import dex
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG, make_cpu


CARRY_FLAG = 1 << 0
OVERFLOW_FLAG = 1 << 6


def test_dex_decrements_x_register():
    """Objective: X decreases by one and remains an 8-bit register value."""
    cpu = make_cpu()
    cpu.x = 0x10

    dex(cpu)

    assert cpu.x == 0x0F


def test_dex_wraps_from_00_to_ff_and_sets_negative_flag():
    """Objective: 0x00 - 1 wraps to 0xFF and sets Negative flag."""
    cpu = make_cpu()
    cpu.x = 0x00

    dex(cpu)

    assert cpu.x == 0xFF
    assert (cpu.p & NEGATIVE_FLAG) != 0
    assert (cpu.p & ZERO_FLAG) == 0


def test_dex_sets_zero_flag_when_result_is_zero():
    """Objective: 0x01 - 1 becomes 0x00 and sets Zero flag."""
    cpu = make_cpu()
    cpu.x = 0x01

    dex(cpu)

    assert cpu.x == 0x00
    assert (cpu.p & ZERO_FLAG) != 0
    assert (cpu.p & NEGATIVE_FLAG) == 0


def test_dex_does_not_modify_carry_or_overflow_flags():
    """Objective: DEX updates Z/N only; Carry and Overflow are preserved."""
    cpu = make_cpu()
    cpu.x = 0x10
    cpu.p |= CARRY_FLAG
    cpu.p |= OVERFLOW_FLAG

    dex(cpu)

    assert cpu.x == 0x0F
    assert (cpu.p & CARRY_FLAG) != 0
    assert (cpu.p & OVERFLOW_FLAG) != 0
