"""Step 193: implement PHA behavior.

In this step, change only ``emulator/cpu/instructions.py`` by adding
``pha(cpu)``. The stack page begins at ``STACK_BASE = 0x0100``.

Why this step exists:
PHA copies A to the 6502 hardware stack. A push writes to the
current $0100 | S slot first and then decrements the 8-bit stack pointer.

Suggested implementation::

    cpu.bus.write(0x0100 | cpu.s, cpu.a)
    cpu.s = (cpu.s - 1) & 0xFF

Place those statements in ``def pha(cpu: CPU)``; using the module-level
``STACK_BASE = 0x0100`` in place of the literal is equivalent.

Invariants: push exactly A; write before decrementing; wrap S to eight bits;
leave A and all status flags unchanged.

Misconception: pre-decrementing S does not implement a 6502 push; it writes to
the next free slot rather than the current stack slot.

Out of scope: importing/registering opcode $48 belongs to step 194. PLA, PHP,
PLP, TXS, and TSX belong to later steps 195-204 and must not be added here.
"""

from emulator.cpu.instructions import pha
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG, make_cpu


CARRY_FLAG = 1 << 0
INTERRUPT_DISABLE_FLAG = 1 << 2
OVERFLOW_FLAG = 1 << 6
STACK_BASE = 0x0100


def test_pha_pushes_accumulator_to_current_stack_address():
    """Objective: PHA writes A to $0100 | S before changing S."""
    cpu = make_cpu()
    cpu.a = 0x42
    cpu.s = 0xFD

    pha(cpu)

    assert cpu.bus.read(STACK_BASE | 0xFD) == 0x42


def test_pha_decrements_stack_pointer_after_push():
    """Objective: after one push, S decreases by 1."""
    cpu = make_cpu()
    cpu.a = 0x42
    cpu.s = 0xFD

    pha(cpu)

    assert cpu.s == 0xFC


def test_pha_does_not_modify_accumulator():
    """Objective: PHA copies A to the stack but leaves A unchanged."""
    cpu = make_cpu()
    cpu.a = 0x99
    cpu.s = 0xFD

    pha(cpu)

    assert cpu.a == 0x99


def test_pha_stack_pointer_wraps_to_8_bits():
    """Objective: S is an 8-bit stack pointer and wraps after decrementing."""
    cpu = make_cpu()
    cpu.a = 0xAB
    cpu.s = 0x00

    pha(cpu)

    assert cpu.bus.read(STACK_BASE | 0x00) == 0xAB
    assert cpu.s == 0xFF


def test_pha_can_push_zero_value_without_setting_zero_flag():
    """
    Objective:
    PHA is a stack transfer, not an arithmetic/load instruction.

    Even if A is $00, PHA must not update the Zero flag.
    """
    cpu = make_cpu()
    cpu.a = 0x00
    cpu.s = 0xFD
    cpu.flags.set_zero_flag(False)

    pha(cpu)

    assert cpu.bus.read(STACK_BASE | 0xFD) == 0x00
    assert cpu.flags.get_zero_flag() is False


def test_pha_can_push_negative_value_without_setting_negative_flag():
    """
    Objective:
    PHA must not update Negative based on bit 7 of A.

    It only saves A to stack.
    """
    cpu = make_cpu()
    cpu.a = 0x80
    cpu.s = 0xFD
    cpu.flags.set_negative_flag(False)

    pha(cpu)

    assert cpu.bus.read(STACK_BASE | 0xFD) == 0x80
    assert cpu.flags.get_negative_flag() is False


def test_pha_preserves_status_flags():
    """Objective: PHA does not modify any processor status flags."""
    cpu = make_cpu()
    cpu.a = 0x42
    cpu.s = 0xFD
    cpu.p = CARRY_FLAG | ZERO_FLAG | INTERRUPT_DISABLE_FLAG | OVERFLOW_FLAG | NEGATIVE_FLAG

    pha(cpu)

    assert cpu.p == (CARRY_FLAG | ZERO_FLAG | INTERRUPT_DISABLE_FLAG | OVERFLOW_FLAG | NEGATIVE_FLAG)
