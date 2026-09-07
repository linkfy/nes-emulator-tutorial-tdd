"""Step 203: implement the TSX operation.

Why this step exists:
In this step, add ``emulator/cpu/instructions.py::tsx``. TSX complements
step 201 by copying the stack-pointer byte into X and deriving the two result
flags from the copied value.

Suggested implementation::

    def tsx(cpu: CPU):
        cpu.x = cpu.s
        cpu.flags.set_zero_flag(cpu.x == 0)
        cpu.flags.set_negative_flag((cpu.x & 0b1000_0000) != 0)

Invariants: S, A, Y, PC, memory, and status bits other than Zero and Negative
are unchanged.  Zero is set exactly for $00; Negative follows bit 7, not bit 6.
The common misconception is to treat TSX like TXS and preserve every flag, or
to calculate flags from X before copying S.

Out of scope: importing TSX and mapping implied opcode $BA in
``emulator/cpu/opcodes.py`` belongs to step 204; no other stack API is added.
"""

from emulator.cpu.instructions import tsx
from tests.helpers import make_cpu


CARRY_FLAG = 1 << 0
ZERO_FLAG = 1 << 1
OVERFLOW_FLAG = 1 << 6
NEGATIVE_FLAG = 1 << 7


def test_tsx_copies_stack_pointer_to_x():
    """Objective: TSX sets X to the current value of S."""
    cpu = make_cpu()
    cpu.s = 0x42
    cpu.x = 0x00

    tsx(cpu)

    assert cpu.x == 0x42


def test_tsx_does_not_modify_stack_pointer():
    """Objective: TSX reads S but leaves S unchanged."""
    cpu = make_cpu()
    cpu.s = 0xFD
    cpu.x = 0x00

    tsx(cpu)

    assert cpu.s == 0xFD


def test_tsx_sets_zero_flag_when_stack_pointer_is_zero():
    """Objective: TSX updates Zero from the copied S value."""
    cpu = make_cpu()
    cpu.s = 0x00
    cpu.x = 0x99
    cpu.flags.set_zero_flag(False)

    tsx(cpu)

    assert cpu.x == 0x00
    assert cpu.flags.get_zero_flag() is True


def test_tsx_clears_zero_flag_when_stack_pointer_is_not_zero():
    """Objective: TSX clears Zero when copied S is non-zero."""
    cpu = make_cpu()
    cpu.s = 0x01
    cpu.flags.set_zero_flag(True)

    tsx(cpu)

    assert cpu.x == 0x01
    assert cpu.flags.get_zero_flag() is False


def test_tsx_sets_negative_flag_when_bit_7_of_stack_pointer_is_set():
    """Objective: TSX updates Negative from bit 7 of copied S."""
    cpu = make_cpu()
    cpu.s = 0x80
    cpu.flags.set_negative_flag(False)

    tsx(cpu)

    assert cpu.x == 0x80
    assert cpu.flags.get_negative_flag() is True


def test_tsx_does_not_set_negative_flag_for_bit_6_only():
    """
    Objective:
    Catch the common mask bug: Negative is bit 7, not bit 6.

    $40 is binary 0100_0000, so Negative must be clear.
    """
    cpu = make_cpu()
    cpu.s = 0x40
    cpu.flags.set_negative_flag(True)

    tsx(cpu)

    assert cpu.x == 0x40
    assert cpu.flags.get_negative_flag() is False


def test_tsx_preserves_flags_other_than_zero_and_negative():
    """Objective: TSX updates only Zero and Negative flags."""
    cpu = make_cpu()
    cpu.s = 0x01
    cpu.p = CARRY_FLAG | ZERO_FLAG | OVERFLOW_FLAG | NEGATIVE_FLAG

    tsx(cpu)

    assert cpu.flags.get_zero_flag() is False
    assert cpu.flags.get_negative_flag() is False
    assert (cpu.p & CARRY_FLAG) != 0
    assert (cpu.p & OVERFLOW_FLAG) != 0
