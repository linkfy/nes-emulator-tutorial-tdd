"""Step 205: add Decimal-bit support.

Why this step exists:
In this step, add ``emulator/cpu/flags_handler.py`` symbols ``DECIMAL_FLAG``,
``FlagsHandler.set_decimal_flag``, and ``FlagsHandler.get_decimal_flag``.  The
helper keeps bit-3 manipulation in the status abstraction needed by subsequent
flag-control operations.  The NES CPU retains D even though ADC/SBC do not use
6502 BCD arithmetic.

Suggested implementation::

    DECIMAL_FLAG = 1 << 3

    class FlagsHandler:
        def set_decimal_flag(self, enabled: bool):
            if enabled:
                self.cpu.p |= DECIMAL_FLAG
            else:
                self.cpu.p &= ~DECIMAL_FLAG

        def get_decimal_flag(self) -> bool:
            return bool(self.cpu.p & DECIMAL_FLAG)

Invariant: setting or clearing D preserves every other P bit, especially the
neighboring Interrupt Disable bit.  The common misconception is clearing with
``p &= DECIMAL_FLAG``, which retains D and destroys unrelated flags.

Out of scope: instruction functions and opcode mappings belong to steps 206 and
207. Decimal-mode ADC/SBC behavior must not be introduced for the NES CPU.
"""

import inspect

from emulator.cpu.flags_handler import FlagsHandler
from tests.helpers import make_cpu


CARRY_FLAG = 1 << 0
ZERO_FLAG = 1 << 1
INTERRUPT_DISABLE_FLAG = 1 << 2
DECIMAL_FLAG = 1 << 3
OVERFLOW_FLAG = 1 << 6
NEGATIVE_FLAG = 1 << 7


def test_flags_handler_has_decimal_flag_helpers():
    """
    Objective:
    Add helpers for the Decimal flag.

    Required API:
        set_decimal_flag(enabled: bool)
        get_decimal_flag() -> bool

    Why:
    SED and CLD should not manipulate cpu.p directly. They should use
    FlagsHandler.
    """
    assert hasattr(FlagsHandler, "set_decimal_flag")
    assert hasattr(FlagsHandler, "get_decimal_flag")

    assert list(inspect.signature(FlagsHandler.set_decimal_flag).parameters) == [
        "self",
        "enabled",
    ]
    assert list(inspect.signature(FlagsHandler.get_decimal_flag).parameters) == ["self"]


def test_flags_handler_sets_and_clears_decimal_flag():
    """
    Objective:
    set_decimal_flag(True) sets bit 3.
    set_decimal_flag(False) clears bit 3.
    """
    cpu = make_cpu()

    cpu.flags.set_decimal_flag(True)
    assert (cpu.p & DECIMAL_FLAG) != 0
    assert cpu.flags.get_decimal_flag() is True

    cpu.flags.set_decimal_flag(False)
    assert (cpu.p & DECIMAL_FLAG) == 0
    assert cpu.flags.get_decimal_flag() is False


def test_clearing_decimal_flag_preserves_other_flags():
    """
    Objective:
    Clearing Decimal must not erase Carry, Zero, Interrupt Disable, Overflow, or
    Negative.

    Failure mode this catches:
        self.cpu.p &= DECIMAL_FLAG

    That keeps only the Decimal bit and clears everything else.
    """
    cpu = make_cpu()
    other_flags = CARRY_FLAG | ZERO_FLAG | INTERRUPT_DISABLE_FLAG | OVERFLOW_FLAG | NEGATIVE_FLAG
    cpu.p = other_flags | DECIMAL_FLAG

    cpu.flags.set_decimal_flag(False)

    assert (cpu.p & DECIMAL_FLAG) == 0
    assert (cpu.p & other_flags) == other_flags


def test_setting_decimal_flag_preserves_other_flags():
    """
    Objective:
    Setting Decimal must add bit 3 without damaging existing status flags.
    """
    cpu = make_cpu()
    other_flags = CARRY_FLAG | ZERO_FLAG | OVERFLOW_FLAG | NEGATIVE_FLAG
    cpu.p = other_flags

    cpu.flags.set_decimal_flag(True)

    assert (cpu.p & DECIMAL_FLAG) != 0
    assert (cpu.p & other_flags) == other_flags


def test_decimal_flag_is_independent_from_interrupt_disable_flag():
    """
    Objective:
    Decimal and Interrupt Disable are neighboring bits, but they are different
    flags.

        I flag = bit 2
        D flag = bit 3

    Setting or clearing one must not toggle the other.
    """
    cpu = make_cpu()

    cpu.flags.set_interrupt_disable_flag(True)
    assert cpu.flags.get_interrupt_disable_flag() is True
    assert cpu.flags.get_decimal_flag() is False

    cpu.flags.set_decimal_flag(True)
    assert cpu.flags.get_interrupt_disable_flag() is True
    assert cpu.flags.get_decimal_flag() is True

    cpu.flags.set_decimal_flag(False)
    assert cpu.flags.get_interrupt_disable_flag() is True
    assert cpu.flags.get_decimal_flag() is False
