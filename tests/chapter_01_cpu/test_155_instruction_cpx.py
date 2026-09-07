"""Lesson 155: implement addressing-independent CPX behavior.

Why this step exists:
CPX needs one value-oriented definition of its no-borrow, equality, and
wrapped-subtraction flags before its addressing-specific opcodes are added.

In this step, after all CMP lessons, add exactly this symbol to
``emulator/cpu/instructions.py``:

    def cpx(cpu: CPU, value: int):
        result_8 = (cpu.x - value) & 0xFF

        # Flags:
        cpu.flags.set_carry_flag(cpu.x >= value)
        cpu.flags.set_zero_flag(cpu.x == value)
        cpu.flags.set_negative_flag((result_8 & 0b1000_0000) !=0)

The wrapped subtraction exists only to derive Negative.  Carry means no
unsigned borrow (X >= value), and Zero tests equality.  X, the operand,
memory, A, Y, PC, and Overflow are invariant because no result is stored and
those locations are untouched.

Misconception: CPX is not SBC and neither consumes Carry nor writes the
subtraction back to X.  Out of scope: importing ``cpx`` into
``emulator/cpu/opcodes.py`` and its immediate, zero-page, and absolute
handlers (lessons 156-158), plus CPY (159-162).
"""

from emulator.cpu.instructions import cpx
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG, make_cpu


CARRY_FLAG = 1 << 0
OVERFLOW_FLAG = 1 << 6


def test_cpx_sets_carry_when_x_is_greater_than_value():
    """Objective: Carry means X >= value for CPX."""
    cpu = make_cpu()
    cpu.x = 0x10

    cpx(cpu, 0x01)

    assert (cpu.p & CARRY_FLAG) != 0
    assert (cpu.p & ZERO_FLAG) == 0
    assert (cpu.p & NEGATIVE_FLAG) == 0


def test_cpx_sets_carry_and_zero_when_x_equals_value():
    """Objective: X == value sets both Carry and Zero."""
    cpu = make_cpu()
    cpu.x = 0x10

    cpx(cpu, 0x10)

    assert (cpu.p & CARRY_FLAG) != 0
    assert (cpu.p & ZERO_FLAG) != 0
    assert (cpu.p & NEGATIVE_FLAG) == 0


def test_cpx_clears_carry_and_sets_negative_when_x_is_less_than_value():
    """Objective: X < value clears Carry; wrapped subtraction can set Negative."""
    cpu = make_cpu()
    cpu.x = 0x01

    cpx(cpu, 0x02)

    assert (cpu.p & CARRY_FLAG) == 0
    assert (cpu.p & ZERO_FLAG) == 0
    assert (cpu.p & NEGATIVE_FLAG) != 0


def test_cpx_does_not_modify_x_or_overflow_flag():
    """Objective: CPX only updates C/Z/N; X and Overflow are preserved."""
    cpu = make_cpu()
    cpu.x = 0x10
    cpu.p |= OVERFLOW_FLAG

    cpx(cpu, 0x01)

    assert cpu.x == 0x10
    assert (cpu.p & OVERFLOW_FLAG) != 0
