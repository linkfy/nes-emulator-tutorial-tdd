"""
Test 086 - Add DEY instruction behavior.

In this step, add only `dey`; Test 087 wires the opcode after the behavior
exists.

Production location and symbol:
    emulator/cpu/instructions.py: `dey(cpu: CPU)`

Why this step exists:
DEY owns the Y-register decrement and status effects independently of decoding.
Masking is required to model underflow in an 8-bit register.

Suggested implementation:

    def dey(cpu: CPU):
        result = cpu.y - 1
        result_8 = result & 0xFF

        # Set flags
        cpu.flags.set_negative_flag((result_8 & 0b1000_0000) != 0)
        cpu.flags.set_zero_flag(result_8 == 0)

        cpu.y = result_8

Important invariants:
    - Y wraps from 0x00 to 0xFF
    - Zero and Negative reflect the masked 8-bit result
    - Carry and Overflow are preserved; memory is not accessed

Common misconception:
DEY is not SBC applied to Y and must not use Carry as a borrow input.

Out of scope:
    - importing `dey` and mapping opcode 0x88 (test 087)
    - prior INY behavior and dispatch
    - later ASL work and cycle timing
"""

from emulator.cpu.instructions import dey
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG, make_cpu


CARRY_FLAG = 1 << 0
OVERFLOW_FLAG = 1 << 6


def test_dey_decrements_y_register():
    """Objective: Y decreases by one and remains an 8-bit register value."""
    cpu = make_cpu()
    cpu.y = 0x10

    dey(cpu)

    assert cpu.y == 0x0F


def test_dey_wraps_from_00_to_ff_and_sets_negative_flag():
    """Objective: 0x00 - 1 wraps to 0xFF and sets Negative flag."""
    cpu = make_cpu()
    cpu.y = 0x00

    dey(cpu)

    assert cpu.y == 0xFF
    assert (cpu.p & NEGATIVE_FLAG) != 0
    assert (cpu.p & ZERO_FLAG) == 0


def test_dey_sets_zero_flag_when_result_is_zero():
    """Objective: 0x01 - 1 becomes 0x00 and sets Zero flag."""
    cpu = make_cpu()
    cpu.y = 0x01

    dey(cpu)

    assert cpu.y == 0x00
    assert (cpu.p & ZERO_FLAG) != 0
    assert (cpu.p & NEGATIVE_FLAG) == 0


def test_dey_does_not_modify_carry_or_overflow_flags():
    """Objective: DEY updates Z/N only; Carry and Overflow are preserved."""
    cpu = make_cpu()
    cpu.y = 0x10
    cpu.p |= CARRY_FLAG
    cpu.p |= OVERFLOW_FLAG

    dey(cpu)

    assert cpu.y == 0x0F
    assert (cpu.p & CARRY_FLAG) != 0
    assert (cpu.p & OVERFLOW_FLAG) != 0
