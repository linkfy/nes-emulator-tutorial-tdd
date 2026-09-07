"""Lesson 146: implement addressing-independent CMP behavior.

Why this step exists:
CMP needs one value-oriented definition of no-borrow Carry, equality Zero, and
wrapped-subtraction Negative semantics before adding any addressing modes.

In this step, before the addressing-specific compare lessons, add exactly this
symbol to ``emulator/cpu/instructions.py``:

    def cmp(cpu: CPU, value: int):
        result_8 = (cpu.a - value) & 0xFF

        # Flags:
        cpu.flags.set_carry_flag(cpu.a >= value)
        cpu.flags.set_zero_flag(cpu.a == value)
        cpu.flags.set_negative_flag((result_8 & 0b1000_0000) !=0)

CMP performs an unsigned comparison while using the wrapped subtraction only
for N.  C means no borrow (A >= value), Z means equality, and N is result bit
7.  A, Overflow, memory, X, Y, and PC are invariant.

Misconception: Carry is set, not cleared, when A is at least the operand, and
the subtraction result is never stored.  Out of scope: importing ``cmp`` and
CMP opcodes are lessons 147 onward; CPX/CPY are lessons 155-162.
"""

from emulator.cpu.instructions import cmp
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG, make_cpu


CARRY_FLAG = 1 << 0
OVERFLOW_FLAG = 1 << 6


def test_cmp_sets_carry_when_a_is_greater_than_value():
    """Objective: Carry means A >= value for CMP."""
    cpu = make_cpu()
    cpu.a = 0x10

    cmp(cpu, 0x01)

    assert (cpu.p & CARRY_FLAG) != 0
    assert (cpu.p & ZERO_FLAG) == 0
    assert (cpu.p & NEGATIVE_FLAG) == 0


def test_cmp_sets_carry_and_zero_when_a_equals_value():
    """Objective: A == value sets both Carry and Zero."""
    cpu = make_cpu()
    cpu.a = 0x10

    cmp(cpu, 0x10)

    assert (cpu.p & CARRY_FLAG) != 0
    assert (cpu.p & ZERO_FLAG) != 0
    assert (cpu.p & NEGATIVE_FLAG) == 0


def test_cmp_clears_carry_and_sets_negative_when_a_is_less_than_value():
    """Objective: A < value clears Carry; wrapped subtraction can set Negative."""
    cpu = make_cpu()
    cpu.a = 0x01

    cmp(cpu, 0x02)

    assert (cpu.p & CARRY_FLAG) == 0
    assert (cpu.p & ZERO_FLAG) == 0
    assert (cpu.p & NEGATIVE_FLAG) != 0


def test_cmp_does_not_modify_accumulator_or_overflow_flag():
    """Objective: CMP only updates C/Z/N; A and Overflow are preserved."""
    cpu = make_cpu()
    cpu.a = 0x10
    cpu.p |= OVERFLOW_FLAG

    cmp(cpu, 0x01)

    assert cpu.a == 0x10
    assert (cpu.p & OVERFLOW_FLAG) != 0
