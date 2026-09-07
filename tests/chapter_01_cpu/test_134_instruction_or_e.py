"""Lesson 134: implement addressing-independent EOR behavior.

Why this step exists:
Centralizing exclusive-OR semantics in a value-oriented primitive lets every
later EOR opcode share identical accumulator and Zero/Negative flag behavior.

In this step, after all ORA work, add exactly this symbol to
``emulator/cpu/instructions.py``:

    def or_e(cpu: CPU, value: int):
        result_8 = (cpu.a ^ value) & 0xFF

        # Flags:
        cpu.flags.set_zero_flag(result_8 == 0)
        cpu.flags.set_negative_flag((result_8 & 0b1000_0000) != 0)

        cpu.a = result_8

The value-oriented signature separates EOR semantics from addressing.  XOR is
masked to eight bits, stored in A, and used to derive Zero and Negative.
Carry, Overflow, memory, X, Y, and PC are invariant because ``or_e`` does not
touch them.

Misconception: despite the helper name ``or_e``, EOR is exclusive
OR (``^``), not inclusive OR, and ``value`` is not an address.  Out of scope:
importing ``or_e`` in ``emulator/cpu/opcodes.py``, every EOR opcode (135-142),
and BIT (143-145).
"""

from emulator.cpu.instructions import or_e
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG, make_cpu


CARRY_FLAG = 1 << 0
OVERFLOW_FLAG = 1 << 6


def test_or_e_stores_exclusive_or_result_in_accumulator():
    """Objective: A becomes A ^ value."""
    cpu = make_cpu()
    cpu.a = 0b1100_1010

    or_e(cpu, 0b1010_1100)

    assert cpu.a == 0b0110_0110


def test_or_e_sets_zero_flag_when_result_is_zero():
    """Objective: when A ^ value is 0, Zero flag is set."""
    cpu = make_cpu()
    cpu.a = 0xAA

    or_e(cpu, 0xAA)

    assert cpu.a == 0x00
    assert (cpu.p & ZERO_FLAG) != 0
    assert (cpu.p & NEGATIVE_FLAG) == 0


def test_or_e_sets_negative_flag_from_result_bit_7():
    """Objective: if result bit 7 is set, Negative flag is set."""
    cpu = make_cpu()
    cpu.a = 0x01

    or_e(cpu, 0x81)

    assert cpu.a == 0x80
    assert (cpu.p & NEGATIVE_FLAG) != 0
    assert (cpu.p & ZERO_FLAG) == 0


def test_or_e_does_not_modify_carry_or_overflow_flags():
    """Objective: EOR only updates Z/N; Carry and Overflow are preserved."""
    cpu = make_cpu()
    cpu.a = 0xF0
    cpu.p |= CARRY_FLAG
    cpu.p |= OVERFLOW_FLAG

    or_e(cpu, 0x0F)

    assert cpu.a == 0xFF
    assert (cpu.p & CARRY_FLAG) != 0
    assert (cpu.p & OVERFLOW_FLAG) != 0
