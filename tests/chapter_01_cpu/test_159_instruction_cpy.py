"""Lesson 159: implement addressing-independent CPY behavior.

Why this step exists:
CPY needs a value-oriented comparison primitive so every addressing form uses
the same no-borrow, equality, and wrapped-subtraction flag rules.

In this step, after CPX, add exactly this symbol to
``emulator/cpu/instructions.py``:

    def cpy(cpu: CPU, value: int):
        result_8 = (cpu.y - value) & 0xFF

        # Flags:
        cpu.flags.set_carry_flag(cpu.y >= value)
        cpu.flags.set_zero_flag(cpu.y == value)
        cpu.flags.set_negative_flag((result_8 & 0b1000_0000) !=0)

The subtraction wraps solely to derive Negative; Carry represents no unsigned
borrow and Zero represents equality.  Y, the operand, memory, A, X, PC, and
Overflow are invariant because CPY stores no subtraction result.

Misconception: CPY neither consumes the existing Carry flag nor writes back to
Y.  Out of scope: importing ``cpy`` into ``emulator/cpu/opcodes.py`` and its
immediate, zero-page, and absolute handlers (lessons 160-162).
"""

from emulator.cpu.instructions import cpy
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG, make_cpu


CARRY_FLAG = 1 << 0
OVERFLOW_FLAG = 1 << 6


def test_cpy_sets_carry_when_y_is_greater_than_value():
    """Objective: Carry means Y >= value for CPY."""
    cpu = make_cpu()
    cpu.y = 0x10

    cpy(cpu, 0x01)

    assert (cpu.p & CARRY_FLAG) != 0
    assert (cpu.p & ZERO_FLAG) == 0
    assert (cpu.p & NEGATIVE_FLAG) == 0


def test_cpy_sets_carry_and_zero_when_y_equals_value():
    """Objective: Y == value sets both Carry and Zero."""
    cpu = make_cpu()
    cpu.y = 0x10

    cpy(cpu, 0x10)

    assert (cpu.p & CARRY_FLAG) != 0
    assert (cpu.p & ZERO_FLAG) != 0
    assert (cpu.p & NEGATIVE_FLAG) == 0


def test_cpy_clears_carry_and_sets_negative_when_y_is_less_than_value():
    """Objective: Y < value clears Carry; wrapped subtraction can set Negative."""
    cpu = make_cpu()
    cpu.y = 0x01

    cpy(cpu, 0x02)

    assert (cpu.p & CARRY_FLAG) == 0
    assert (cpu.p & ZERO_FLAG) == 0
    assert (cpu.p & NEGATIVE_FLAG) != 0


def test_cpy_does_not_modify_y_or_overflow_flag():
    """Objective: CPY only updates C/Z/N; Y and Overflow are preserved."""
    cpu = make_cpu()
    cpu.y = 0x10
    cpu.p |= OVERFLOW_FLAG

    cpy(cpu, 0x01)

    assert cpu.y == 0x10
    assert (cpu.p & OVERFLOW_FLAG) != 0
