"""
Test 084 - Add INY instruction behavior.

In this step, add only `iny`, before its Test 085 opcode mapping and the DEY
work in Tests 086-087.

Production location and symbol:
    emulator/cpu/instructions.py: `iny(cpu: CPU)`

Why this step exists:
INY increments the Y register independently of opcode decoding and must emulate
an 8-bit register despite Python's unbounded integers.

Suggested implementation:

    def iny(cpu: CPU):
        result = cpu.y + 1
        result_8 = result & 0xFF

        # Set flags
        cpu.flags.set_negative_flag((result_8 & 0b1000_0000) != 0)
        cpu.flags.set_zero_flag(result_8 == 0)

        cpu.y = result_8

Important invariants:
    - Y wraps from 0xFF to 0x00
    - Zero and Negative are computed from the masked result
    - Carry, Overflow, memory, and other registers remain unchanged

Common misconception:
The increment does not set Carry when Y wraps; INY only updates Z and N.

Out of scope:
    - opcode 0xC8 dispatch (test 085)
    - DEY behavior and dispatch (tests 086-087)
    - later ASL work and cycle timing
"""

from emulator.cpu.instructions import iny
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG, make_cpu


CARRY_FLAG = 1 << 0
OVERFLOW_FLAG = 1 << 6


def test_iny_increments_y_register():
    """Objective: Y increases by one and remains an 8-bit register value."""
    cpu = make_cpu()
    cpu.y = 0x10

    iny(cpu)

    assert cpu.y == 0x11


def test_iny_wraps_from_ff_to_00_and_sets_zero_flag():
    """Objective: 0xFF + 1 wraps to 0x00 and sets Zero flag."""
    cpu = make_cpu()
    cpu.y = 0xFF

    iny(cpu)

    assert cpu.y == 0x00
    assert (cpu.p & ZERO_FLAG) != 0
    assert (cpu.p & NEGATIVE_FLAG) == 0


def test_iny_sets_negative_flag_when_result_has_bit_7_set():
    """Objective: 0x7F + 1 becomes 0x80, so Negative flag is set."""
    cpu = make_cpu()
    cpu.y = 0x7F

    iny(cpu)

    assert cpu.y == 0x80
    assert (cpu.p & NEGATIVE_FLAG) != 0
    assert (cpu.p & ZERO_FLAG) == 0


def test_iny_does_not_modify_carry_or_overflow_flags():
    """Objective: INY updates Z/N only; Carry and Overflow are preserved."""
    cpu = make_cpu()
    cpu.y = 0x01
    cpu.p |= CARRY_FLAG
    cpu.p |= OVERFLOW_FLAG

    iny(cpu)

    assert cpu.y == 0x02
    assert (cpu.p & CARRY_FLAG) != 0
    assert (cpu.p & OVERFLOW_FLAG) != 0
