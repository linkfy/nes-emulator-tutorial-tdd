"""Step 199: implement PLP behavior.

In this step, change only ``emulator/cpu/instructions.py`` by adding
``plp(cpu)``. Prerequisites: ``STACK_BASE`` and RTI's status-mask convention
already exist.

Why this step exists:
PLP advances S to the saved status byte and replaces P with that
byte after removing this emulator model's non-persistent bits 4 and 5.

Suggested implementation::

    cpu.s = (cpu.s + 1) & 0xFF
    flags = cpu.bus.read(0x0100 | cpu.s)
    cpu.p = flags & 0b1100_1111

Place those statements in ``def plp(cpu: CPU)``; the equivalent
``STACK_BASE + cpu.s`` address also selects stack page $0100.

Invariants: increment and wrap S before reading; replace rather than merge P;
clear bits 4 and 5; restore all other saved flag bits exactly; do not compute Z
or N from the numeric byte as PLA does.

Misconception: PLP does not selectively OR flags into the old P. Doing so
leaves stale flags that the stacked status explicitly cleared.

Out of scope: opcode $28 registration belongs to step 200. Later flag APIs must
not be added to this implementation.
"""

from emulator.cpu.instructions import plp
from tests.helpers import make_cpu


CARRY_FLAG = 1 << 0
ZERO_FLAG = 1 << 1
INTERRUPT_DISABLE_FLAG = 1 << 2
BREAK_FLAG = 1 << 4
ONE_FLAG = 1 << 5
OVERFLOW_FLAG = 1 << 6
NEGATIVE_FLAG = 1 << 7
STACK_BASE = 0x0100


def test_plp_pulls_status_from_stack_into_processor_status():
    """Objective: PLP restores status flags from $0100 | incremented S."""
    cpu = make_cpu()
    cpu.s = 0xFC
    saved_status = CARRY_FLAG | ZERO_FLAG | INTERRUPT_DISABLE_FLAG | OVERFLOW_FLAG | NEGATIVE_FLAG
    cpu.bus.write(STACK_BASE | 0xFD, saved_status)

    plp(cpu)

    assert cpu.p == saved_status


def test_plp_increments_stack_pointer_before_reading():
    """
    Objective:
    PLP must increment S before reading.

    With S = $FC, the pulled status comes from $01FD, not $01FC.
    """
    cpu = make_cpu()
    cpu.s = 0xFC
    cpu.bus.write(STACK_BASE | 0xFC, CARRY_FLAG)
    cpu.bus.write(STACK_BASE | 0xFD, NEGATIVE_FLAG)

    plp(cpu)

    assert cpu.p == NEGATIVE_FLAG
    assert cpu.s == 0xFD


def test_plp_restores_zero_and_negative_from_saved_status_bits():
    """
    Objective:
    PLP restores Z and N from the saved status byte.

    Unlike PLA, it does not compute Z/N from a pulled data value. It copies the
    saved flag bits.
    """
    cpu = make_cpu()
    cpu.s = 0xFC
    cpu.flags.set_zero_flag(False)
    cpu.flags.set_negative_flag(False)
    cpu.bus.write(STACK_BASE | 0xFD, ZERO_FLAG | NEGATIVE_FLAG)

    plp(cpu)

    assert cpu.flags.get_zero_flag() is True
    assert cpu.flags.get_negative_flag() is True


def test_plp_clears_break_and_unused_status_bits_from_pulled_status():
    """
    Objective:
    In this emulator model, bits 4 and 5 are not kept in cpu.p after PLP.

    PHP may push Break in the saved stack byte, but PLP should not keep Break as
    persistent CPU state.
    """
    cpu = make_cpu()
    cpu.s = 0xFC
    saved_status_with_break_and_unused = 0b0011_0000 | CARRY_FLAG | NEGATIVE_FLAG
    cpu.bus.write(STACK_BASE | 0xFD, saved_status_with_break_and_unused)

    plp(cpu)

    assert (cpu.p & BREAK_FLAG) == 0
    assert (cpu.p & ONE_FLAG) == 0
    assert cpu.p == (CARRY_FLAG | NEGATIVE_FLAG)


def test_plp_replaces_previous_processor_status():
    """
    Objective:
    PLP restores P from the stack. It does not merge old flags with new flags.

    Failure mode this catches:
    Using cpu.p |= flags would leave stale flags set.
    """
    cpu = make_cpu()
    cpu.s = 0xFC
    cpu.p = CARRY_FLAG | ZERO_FLAG | OVERFLOW_FLAG | NEGATIVE_FLAG
    cpu.bus.write(STACK_BASE | 0xFD, INTERRUPT_DISABLE_FLAG)

    plp(cpu)

    assert cpu.p == INTERRUPT_DISABLE_FLAG


def test_plp_stack_pointer_wraps_to_8_bits():
    """Objective: S is an 8-bit stack pointer and wraps before reading."""
    cpu = make_cpu()
    cpu.s = 0xFF
    cpu.bus.write(STACK_BASE | 0x00, CARRY_FLAG | NEGATIVE_FLAG)

    plp(cpu)

    assert cpu.p == (CARRY_FLAG | NEGATIVE_FLAG)
    assert cpu.s == 0x00
