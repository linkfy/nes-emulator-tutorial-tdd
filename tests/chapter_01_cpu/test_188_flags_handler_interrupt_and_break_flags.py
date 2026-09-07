"""Step 188: add I, B, and unused-bit flag helpers.

In this step, define Break as bit 4 and the pushed-status unused bit as bit 5.
Add to ``emulator/cpu/flags_handler.py``:

    INTERRUPT_FLAG = 1 << 2
    B_FLAG = 1 << 4
    ONE_FLAG = 1 << 5

    def set_interrupt_disable_flag(self, enabled: bool):
        if enabled:
            self.cpu.p |= INTERRUPT_FLAG
        else:
            self.cpu.p &= ~INTERRUPT_FLAG

    def set_break_flag(self, enabled: bool):
        if enabled:
            self.cpu.p |= B_FLAG
        else:
            self.cpu.p &= ~B_FLAG

    def set_one_flag(self, enabled: bool):
        if enabled:
            self.cpu.p |= ONE_FLAG
        else:
            self.cpu.p &= ~ONE_FLAG

    def get_interrupt_disable_flag(self) -> bool:
        return bool(self.cpu.p & INTERRUPT_FLAG)

    def get_break_flag(self) -> bool:
        return bool(self.cpu.p & B_FLAG)

    def get_one_flag(self) -> bool:
        return bool(self.cpu.p & ONE_FLAG)

Why this step exists:
We are preparing to implement BRK.

BRK is a software interrupt instruction. To implement it clearly, the CPU needs
helpers for two status flags:

    I flag -> Interrupt Disable, bit 2
    B flag -> Break, bit 4
    ONE flag -> unused/status bit 5 used in pushed status bytes

BRK will need them because:
    - it sets the Interrupt Disable flag after entering the interrupt handler
    - it pushes a status byte with the Break flag set

Design goal:
Keep bit manipulation inside FlagsHandler instead of spreading raw cpu.p bit
operations through instruction code.

Important terminology:
    Interrupt Disable flag:
        When set, maskable IRQ interrupts are disabled.

    Break flag:
        Used to mark that the pushed status byte came from BRK.

Common mistake:
Do not confuse the BRK opcode with the Break flag.

    BRK opcode: 0x00, the instruction byte in memory
    B flag:     bit 4 inside the status byte pushed to the stack
    ONE flag:   bit 5, usually set in pushed status bytes

Rationale: named setters centralize independent read-modify-write operations on
P and getters expose booleans.  Invariants: each setter changes only its bit;
I, B, ONE, and all existing flags remain independent.  Misconception: B and
the always-one pushed-status bit are not the same bit, and opcode $00 is neither.

Out of scope: this step does not implement BRK or decide when bits are set;
those are steps 189-190. RTI/PHP/PLP, NMI behavior, and CPU stack helpers remain
later work.
"""

import inspect

from emulator.cpu.flags_handler import FlagsHandler
from tests.helpers import make_cpu


INTERRUPT_DISABLE_FLAG = 1 << 2
BREAK_FLAG = 1 << 4
ONE_FLAG = 1 << 5


def test_flags_handler_has_interrupt_disable_helpers():
    """
    Objective:
    Add helpers for the Interrupt Disable flag.

    Required API:
        set_interrupt_disable_flag(enabled: bool)
        get_interrupt_disable_flag() -> bool

    Why:
    BRK must set the Interrupt Disable flag after it begins interrupt handling.
    """
    assert hasattr(FlagsHandler, "set_interrupt_disable_flag")
    assert hasattr(FlagsHandler, "get_interrupt_disable_flag")

    assert list(inspect.signature(FlagsHandler.set_interrupt_disable_flag).parameters) == [
        "self",
        "enabled",
    ]
    assert list(inspect.signature(FlagsHandler.get_interrupt_disable_flag).parameters) == [
        "self"
    ]


def test_flags_handler_has_break_flag_helpers():
    """
    Objective:
    Add helpers for the Break flag.

    Required API:
        set_break_flag(enabled: bool)
        get_break_flag() -> bool

    Why:
    BRK pushes a status byte with the Break flag set.
    """
    assert hasattr(FlagsHandler, "set_break_flag")
    assert hasattr(FlagsHandler, "get_break_flag")

    assert list(inspect.signature(FlagsHandler.set_break_flag).parameters) == [
        "self",
        "enabled",
    ]
    assert list(inspect.signature(FlagsHandler.get_break_flag).parameters) == ["self"]


def test_flags_handler_has_one_flag_helpers():
    """
    Objective:
    Add helpers for the ONE/unused status bit.

    Required API:
        set_one_flag(enabled: bool)
        get_one_flag() -> bool

    Why:
    BRK/PHP/NMI pushed status bytes should have bit 5 set even though this bit has
    no normal CPU behavior effect.
    """
    assert hasattr(FlagsHandler, "set_one_flag")
    assert hasattr(FlagsHandler, "get_one_flag")

    assert list(inspect.signature(FlagsHandler.set_one_flag).parameters) == [
        "self",
        "enabled",
    ]
    assert list(inspect.signature(FlagsHandler.get_one_flag).parameters) == ["self"]


def test_flags_handler_sets_and_clears_interrupt_disable_flag():
    """
    Objective:
    set_interrupt_disable_flag(True) sets bit 2.
    set_interrupt_disable_flag(False) clears bit 2.

    Mental model:
    The flag helper does not decide when interrupts should be disabled.
    Instructions decide the condition. The helper only changes the bit.
    """
    cpu = make_cpu()

    cpu.flags.set_interrupt_disable_flag(True)
    assert (cpu.p & INTERRUPT_DISABLE_FLAG) != 0
    assert cpu.flags.get_interrupt_disable_flag() is True

    cpu.flags.set_interrupt_disable_flag(False)
    assert (cpu.p & INTERRUPT_DISABLE_FLAG) == 0
    assert cpu.flags.get_interrupt_disable_flag() is False


def test_flags_handler_sets_and_clears_break_flag():
    """
    Objective:
    set_break_flag(True) sets bit 4.
    set_break_flag(False) clears bit 4.

    Why this matters for BRK:
    The pushed status byte must indicate that the interrupt came from BRK.
    """
    cpu = make_cpu()

    cpu.flags.set_break_flag(True)
    assert (cpu.p & BREAK_FLAG) != 0
    assert cpu.flags.get_break_flag() is True

    cpu.flags.set_break_flag(False)
    assert (cpu.p & BREAK_FLAG) == 0
    assert cpu.flags.get_break_flag() is False


def test_flags_handler_sets_and_clears_one_flag():
    """
    Objective:
    set_one_flag(True) sets bit 5.
    set_one_flag(False) clears bit 5.

    Why this matters:
    Bit 5 is forced into pushed status bytes, but it is distinct from the Break
    flag at bit 4.
    """
    cpu = make_cpu()

    cpu.flags.set_one_flag(True)
    assert (cpu.p & ONE_FLAG) != 0
    assert cpu.flags.get_one_flag() is True

    cpu.flags.set_one_flag(False)
    assert (cpu.p & ONE_FLAG) == 0
    assert cpu.flags.get_one_flag() is False


def test_interrupt_disable_and_break_helpers_preserve_other_flags():
    """
    Objective:
    Changing I or B must not accidentally damage other status flags.

    Failure mode this catches:
    A setter that assigns cpu.p directly, like cpu.p = INTERRUPT_DISABLE_FLAG,
    would erase existing flags such as Carry, Zero, Overflow, or Negative.
    """
    cpu = make_cpu()
    other_flags = 0b1100_0011
    cpu.p = other_flags

    cpu.flags.set_interrupt_disable_flag(True)
    cpu.flags.set_break_flag(True)

    assert (cpu.p & other_flags) == other_flags
    assert (cpu.p & INTERRUPT_DISABLE_FLAG) != 0
    assert (cpu.p & BREAK_FLAG) != 0

    cpu.flags.set_interrupt_disable_flag(False)
    cpu.flags.set_break_flag(False)

    assert (cpu.p & other_flags) == other_flags
    assert (cpu.p & INTERRUPT_DISABLE_FLAG) == 0
    assert (cpu.p & BREAK_FLAG) == 0


def test_interrupt_disable_and_break_flags_are_independent():
    """
    Objective:
    The I flag and B flag are different bits and must not toggle each other.

    Why:
    BRK needs both concepts, but they mean different things:
        I flag: disables maskable IRQ interrupts
        B flag: marks BRK in the pushed status byte
    """
    cpu = make_cpu()

    cpu.flags.set_interrupt_disable_flag(True)
    assert cpu.flags.get_interrupt_disable_flag() is True
    assert cpu.flags.get_break_flag() is False

    cpu.flags.set_break_flag(True)
    assert cpu.flags.get_interrupt_disable_flag() is True
    assert cpu.flags.get_break_flag() is True

    cpu.flags.set_interrupt_disable_flag(False)
    assert cpu.flags.get_interrupt_disable_flag() is False
    assert cpu.flags.get_break_flag() is True
