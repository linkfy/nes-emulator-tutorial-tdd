"""Lesson 125: implement addressing-independent ORA behavior.

Why this step exists:
A single value-oriented ORA primitive centralizes inclusive-OR result and flag
rules before opcode handlers introduce the individual addressing forms.

In this step, after lessons 116-124 complete AND, add only this symbol to
``emulator/cpu/instructions.py``:

    def or_a(cpu: CPU, value: int):
        result_8 = (cpu.a | value) & 0xFF

        # Flags:
        cpu.flags.set_zero_flag(result_8 == 0)
        cpu.flags.set_negative_flag((result_8 & 0b1000_0000) != 0)

        cpu.a = result_8

The value-oriented API keeps ORA semantics independent of addressing.  The
eight-bit result is stored in A; Zero reflects equality to zero and Negative
reflects result bit 7.  Carry, Overflow, memory, X, Y, and PC are invariant
because ``or_a`` does not touch them.

Misconception: ORA means inclusive bitwise OR, not XOR, and ``value`` is not a
bus address.  Out of scope: importing ``or_a`` into
``emulator/cpu/opcodes.py`` and all ORA handlers (lessons 126-133), plus the
EOR and BIT symbols introduced in lessons 134 and 143.
"""

from emulator.cpu.instructions import or_a
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG, make_cpu


CARRY_FLAG = 1 << 0
OVERFLOW_FLAG = 1 << 6


def test_or_a_stores_bitwise_or_result_in_accumulator():
    """Objective: A becomes A | value."""
    cpu = make_cpu()
    cpu.a = 0b1100_0000

    or_a(cpu, 0b0000_1010)

    assert cpu.a == 0b1100_1010


def test_or_a_sets_zero_flag_when_result_is_zero():
    """Objective: when A | value is 0, Zero flag is set."""
    cpu = make_cpu()
    cpu.a = 0x00

    or_a(cpu, 0x00)

    assert cpu.a == 0x00
    assert (cpu.p & ZERO_FLAG) != 0
    assert (cpu.p & NEGATIVE_FLAG) == 0


def test_or_a_sets_negative_flag_from_result_bit_7():
    """Objective: if result bit 7 is set, Negative flag is set."""
    cpu = make_cpu()
    cpu.a = 0x01

    or_a(cpu, 0x80)

    assert cpu.a == 0x81
    assert (cpu.p & NEGATIVE_FLAG) != 0
    assert (cpu.p & ZERO_FLAG) == 0


def test_or_a_does_not_modify_carry_or_overflow_flags():
    """Objective: ORA only updates Z/N; Carry and Overflow are preserved."""
    cpu = make_cpu()
    cpu.a = 0x00
    cpu.p |= CARRY_FLAG
    cpu.p |= OVERFLOW_FLAG

    or_a(cpu, 0x0F)

    assert cpu.a == 0x0F
    assert (cpu.p & CARRY_FLAG) != 0
    assert (cpu.p & OVERFLOW_FLAG) != 0
