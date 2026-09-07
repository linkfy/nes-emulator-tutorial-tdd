"""Lesson 116: implement addressing-independent AND behavior.

In this step, add only ``and_a`` to ``emulator/cpu/instructions.py``. Opcode
imports and AND addressing modes follow in lessons 117-124.

Why this step exists:
Defining AND as a value-oriented primitive keeps accumulator and flag semantics
in one place so every addressing-mode handler can reuse them consistently.

Suggested implementation:

    def and_a(cpu: CPU, value: int):
        result_8 = (cpu.a & value) & 0xFF

        # Flags:
        cpu.flags.set_zero_flag(result_8 == 0)
        cpu.flags.set_negative_flag((result_8 & 0b1000_0000) != 0)

        cpu.a = result_8

The value-oriented signature keeps instruction semantics separate from
address decoding.  The result is constrained to eight bits, stored in A,
Zero reflects equality to zero, and Negative reflects result bit 7.  Carry,
Overflow, memory, X, Y, and PC are invariant because this function never
touches them.

Misconception: ``value`` is not an address to read through ``cpu.bus``; opcode
handlers perform such reads. Out of scope: importing ``and_a`` into
``emulator/cpu/opcodes.py`` and every AND opcode (lessons 117-124), plus the
ORA, EOR, and BIT symbols in lessons 125-145.
"""

from emulator.cpu.instructions import and_a
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG, make_cpu


CARRY_FLAG = 1 << 0
OVERFLOW_FLAG = 1 << 6


def test_and_a_stores_bitwise_and_result_in_accumulator():
    """Objective: A becomes A & value."""
    cpu = make_cpu()
    cpu.a = 0b1100_1010

    and_a(cpu, 0b1010_1100)

    assert cpu.a == 0b1000_1000


def test_and_a_sets_zero_flag_when_result_is_zero():
    """Objective: when A & value is 0, Zero flag is set."""
    cpu = make_cpu()
    cpu.a = 0b0000_1111


    and_a(cpu, 0b1111_0000)


    assert cpu.a == 0x00
    assert (cpu.p & ZERO_FLAG) != 0
    assert (cpu.p & NEGATIVE_FLAG) == 0


def test_and_a_sets_negative_flag_from_result_bit_7():
    """Objective: if result bit 7 is set, Negative flag is set."""
    cpu = make_cpu()
    cpu.a = 0b1000_1111

    and_a(cpu, 0b1111_0000)

    assert cpu.a == 0b1000_0000
    assert (cpu.p & NEGATIVE_FLAG) != 0
    assert (cpu.p & ZERO_FLAG) == 0


def test_and_a_does_not_modify_carry_or_overflow_flags():
    """Objective: AND only updates Z/N; Carry and Overflow are preserved."""
    cpu = make_cpu()
    cpu.a = 0xFF
    cpu.p |= CARRY_FLAG
    cpu.p |= OVERFLOW_FLAG

    and_a(cpu, 0x0F)

    assert cpu.a == 0x0F
    assert (cpu.p & CARRY_FLAG) != 0
    assert (cpu.p & OVERFLOW_FLAG) != 0
