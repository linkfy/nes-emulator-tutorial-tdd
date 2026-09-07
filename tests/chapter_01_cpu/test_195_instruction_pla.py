"""Step 195: implement PLA behavior.

In this step, change only ``emulator/cpu/instructions.py`` by adding
``pla(cpu)``. Prerequisites: ``STACK_BASE`` and the zero/negative flag setters
already exist.

Why this step exists:
A pull first advances S to the occupied stack slot, loads that byte
into A, and derives Z and N from the newly loaded accumulator.

Suggested implementation::

    cpu.s = (cpu.s + 1) & 0xFF
    cpu.a = cpu.bus.read(0x0100 | cpu.s)
    cpu.flags.set_zero_flag(cpu.a == 0)
    cpu.flags.set_negative_flag((cpu.a & 0x80) != 0)

Place those statements in ``def pla(cpu: CPU)``. ``STACK_BASE`` and the
equivalent binary bit-7 mask ``0b1000_0000`` may be used.

Invariants: increment and wrap S before reading; read stack page $0100; replace
A with the pulled byte; update only Z and N, using bit 7 for N; preserve all
other status bits.

Misconception: PLA is not merely PHA in reverse. Unlike PHA, it updates Z and
N from A, but it does not replace the whole status register.

Out of scope: opcode $68 registration belongs to step 196. PHP and PLP begin
at steps 197 and 199; do not add their APIs or behavior here.
"""

from emulator.cpu.instructions import pla
from tests.helpers import make_cpu


CARRY_FLAG = 1 << 0
ZERO_FLAG = 1 << 1
OVERFLOW_FLAG = 1 << 6
NEGATIVE_FLAG = 1 << 7
STACK_BASE = 0x0100


def test_pla_pulls_value_from_stack_into_accumulator():
    """Objective: PLA reads from $0100 | incremented S and stores that value in A."""
    cpu = make_cpu()
    cpu.s = 0xFC
    cpu.bus.write(STACK_BASE | 0xFD, 0x42)

    pla(cpu)

    assert cpu.a == 0x42


def test_pla_increments_stack_pointer_before_reading():
    """
    Objective:
    PLA must increment S before reading.

    With S = $FC, the pulled byte comes from $01FD, not $01FC.
    """
    cpu = make_cpu()
    cpu.s = 0xFC
    cpu.bus.write(STACK_BASE | 0xFC, 0x11)
    cpu.bus.write(STACK_BASE | 0xFD, 0x22)

    pla(cpu)

    assert cpu.a == 0x22
    assert cpu.s == 0xFD


def test_pla_sets_zero_flag_when_pulled_value_is_zero():
    """Objective: PLA updates Zero from the pulled accumulator value."""
    cpu = make_cpu()
    cpu.s = 0xFC
    cpu.bus.write(STACK_BASE | 0xFD, 0x00)
    cpu.flags.set_zero_flag(False)

    pla(cpu)

    assert cpu.a == 0x00
    assert cpu.flags.get_zero_flag() is True


def test_pla_clears_zero_flag_when_pulled_value_is_not_zero():
    """Objective: PLA clears Zero when the pulled value is non-zero."""
    cpu = make_cpu()
    cpu.s = 0xFC
    cpu.bus.write(STACK_BASE | 0xFD, 0x01)
    cpu.flags.set_zero_flag(True)

    pla(cpu)

    assert cpu.a == 0x01
    assert cpu.flags.get_zero_flag() is False


def test_pla_sets_negative_flag_when_bit_7_is_set():
    """
    Objective:
    PLA updates Negative from bit 7 of the pulled value.

    $80 is binary 1000_0000, so Negative must be set.
    """
    cpu = make_cpu()
    cpu.s = 0xFC
    cpu.bus.write(STACK_BASE | 0xFD, 0x80)
    cpu.flags.set_negative_flag(False)

    pla(cpu)

    assert cpu.a == 0x80
    assert cpu.flags.get_negative_flag() is True


def test_pla_does_not_set_negative_flag_for_bit_6_only():
    """
    Objective:
    Catch the common mask bug: Negative is bit 7, not bit 6.

    $40 is binary 0100_0000. Bit 6 is set, but Negative must remain clear.
    """
    cpu = make_cpu()
    cpu.s = 0xFC
    cpu.bus.write(STACK_BASE | 0xFD, 0x40)
    cpu.flags.set_negative_flag(True)

    pla(cpu)

    assert cpu.a == 0x40
    assert cpu.flags.get_negative_flag() is False


def test_pla_preserves_flags_other_than_zero_and_negative():
    """
    Objective:
    PLA updates only Zero and Negative.

    Carry and Overflow must keep their previous values.
    """
    cpu = make_cpu()
    cpu.s = 0xFC
    cpu.bus.write(STACK_BASE | 0xFD, 0x01)
    cpu.p = CARRY_FLAG | ZERO_FLAG | OVERFLOW_FLAG | NEGATIVE_FLAG

    pla(cpu)

    assert cpu.flags.get_zero_flag() is False
    assert cpu.flags.get_negative_flag() is False
    assert (cpu.p & CARRY_FLAG) != 0
    assert (cpu.p & OVERFLOW_FLAG) != 0


def test_pla_stack_pointer_wraps_to_8_bits():
    """Objective: S is an 8-bit stack pointer and wraps before reading."""
    cpu = make_cpu()
    cpu.s = 0xFF
    cpu.bus.write(STACK_BASE | 0x00, 0xAB)

    pla(cpu)

    assert cpu.a == 0xAB
    assert cpu.s == 0x00
