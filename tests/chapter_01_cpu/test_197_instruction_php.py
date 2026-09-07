"""Step 197: implement PHP behavior.

In this step, change only ``emulator/cpu/instructions.py`` by adding
``php(cpu)``. Prerequisite: ``FlagsHandler.set_break_flag`` already exists.

Why this step exists:
PHP pushes P with the emulator's Break marker set, then
clears that transient marker from live CPU state. As with every push, it writes
to $0100 | S before decrementing the 8-bit S.

Suggested implementation::

    def php(cpu: CPU):
        cpu.flags.set_break_flag(True)
        cpu.flags.set_one_flag(True)
        cpu.bus.write(STACK_BASE | cpu.s, cpu.p)
        cpu.flags.set_break_flag(False)
        cpu.flags.set_one_flag(False)
        cpu.s = (cpu.s - 1) & 0xFF

Invariants: preserve every pre-existing status bit; set Break and ONE in the
stacked copy; clear both from live P afterward; write before decrementing and
wrap S; do not derive Z or N from the status byte.

Misconception: Break is not left enabled in ``cpu.p`` after PHP merely because
it is set in the byte written to the stack.

Out of scope: opcode $08 registration belongs to step 198. Any later changes to
the pushed status-byte rules belong to their own numbered steps.
"""

from emulator.cpu.instructions import php
from tests.helpers import make_cpu


CARRY_FLAG = 1 << 0
ZERO_FLAG = 1 << 1
INTERRUPT_DISABLE_FLAG = 1 << 2
BREAK_FLAG = 1 << 4
ONE_FLAG = 1 << 5
OVERFLOW_FLAG = 1 << 6
NEGATIVE_FLAG = 1 << 7
STACK_BASE = 0x0100


def test_php_pushes_processor_status_to_current_stack_address():
    """Objective: PHP writes status to $0100 | S before changing S."""
    cpu = make_cpu()
    cpu.s = 0xFD
    cpu.p = CARRY_FLAG | ZERO_FLAG

    php(cpu)

    pushed_status = cpu.bus.read(STACK_BASE | 0xFD)
    assert (pushed_status & CARRY_FLAG) != 0
    assert (pushed_status & ZERO_FLAG) != 0


def test_php_pushes_status_with_break_flag_set():
    """
    Objective:
    PHP pushes a copy of P with the Break flag set.

    The Break flag here describes the saved status byte, not a normal long-lived
    CPU flag in this emulator model.
    """
    cpu = make_cpu()
    cpu.s = 0xFD
    cpu.p = 0x00

    php(cpu)

    pushed_status = cpu.bus.read(STACK_BASE | 0xFD)
    assert (pushed_status & BREAK_FLAG) != 0
    assert (pushed_status & ONE_FLAG) != 0


def test_php_clears_break_flag_from_cpu_state_after_push():
    """
    Objective:
    PHP should not leave Break set in cpu.p after the push finishes.
    """
    cpu = make_cpu()
    cpu.s = 0xFD
    cpu.p = 0x00

    php(cpu)

    pushed_status = cpu.bus.read(STACK_BASE | 0xFD)
    assert (pushed_status & BREAK_FLAG) != 0
    assert (pushed_status & ONE_FLAG) != 0
    assert cpu.flags.get_break_flag() is False
    assert cpu.flags.get_one_flag() is False


def test_php_decrements_stack_pointer_after_push():
    """Objective: PHP pushes one byte, so S decreases by 1."""
    cpu = make_cpu()
    cpu.s = 0xFD
    cpu.p = 0x00

    php(cpu)

    assert cpu.s == 0xFC


def test_php_stack_pointer_wraps_to_8_bits():
    """Objective: S is an 8-bit stack pointer and wraps after decrementing."""
    cpu = make_cpu()
    cpu.s = 0x00
    cpu.p = CARRY_FLAG

    php(cpu)

    pushed_status = cpu.bus.read(STACK_BASE | 0x00)
    assert (pushed_status & CARRY_FLAG) != 0
    assert (pushed_status & BREAK_FLAG) != 0
    assert (pushed_status & ONE_FLAG) != 0
    assert cpu.s == 0xFF


def test_php_preserves_non_break_cpu_flags_after_push():
    """
    Objective:
    PHP is a stack operation. It should not damage existing status flags.

    Break is special here: it is temporarily set for the pushed copy, then
    cleared from CPU state again.
    """
    cpu = make_cpu()
    cpu.s = 0xFD
    cpu.p = CARRY_FLAG | ZERO_FLAG | INTERRUPT_DISABLE_FLAG | OVERFLOW_FLAG | NEGATIVE_FLAG
    expected_cpu_p = cpu.p

    php(cpu)

    assert cpu.p == expected_cpu_p


def test_php_does_not_update_zero_or_negative_flags_from_status_value():
    """
    Objective:
    PHP does not compute flags. It only pushes a status byte.

    Even if the pushed byte has bit 7 set, PHP must not reinterpret that as a
    new Negative result.
    """
    cpu = make_cpu()
    cpu.s = 0xFD
    cpu.p = CARRY_FLAG
    cpu.flags.set_zero_flag(False)
    cpu.flags.set_negative_flag(False)

    php(cpu)

    assert cpu.flags.get_zero_flag() is False
    assert cpu.flags.get_negative_flag() is False
