"""
Test 012 — Extract shared Zero and Negative flag updates.

File to update:
    emulator/cpu/cpu.py

Locations:
    CPU._update_zero_and_negative_flags
    CPU.step, existing $A9 and $AD branches

Why this step exists:
Immediate and absolute LDA currently repeat identical flag mutations. One helper
makes the invariant executable once and accepts the result value explicitly so later
instructions can reuse it without depending on accumulator A.

Complete example implementation:

    ZERO_FLAG = 1 << 1
    NEGATIVE_FLAG = 1 << 7


    class CPU:
        def _update_zero_and_negative_flags(self, value: int) -> None:
            if value == 0:
                self.p |= ZERO_FLAG
            else:
                self.p &= ~ZERO_FLAG

            if value & NEGATIVE_FLAG:
                self.p |= NEGATIVE_FLAG
            else:
                self.p &= ~NEGATIVE_FLAG

        def step(self) -> None:
            opcode = self.fetch_byte()

            if opcode == 0xA9:
                self.a = self.fetch_byte()
            elif opcode == 0xAD:
                address = self.fetch_word()
                self.a = self.bus.read(address)
            else:
                raise NotImplementedError(
                    f"Opcode ${opcode:02X} is not implemented"
                )

            self._update_zero_and_negative_flags(self.a)

Important invariants:
    - flags are derived from the received value, not implicitly from cpu.a
    - only Z and N change
    - existing LDA behavior remains unchanged after the refactor

Common misconception:
A refactor is not permission to change behavior. Tests 010–011 remain the behavioral
contract; this step only centralizes their mechanism.

Out of scope:
    - moving addressing logic out of CPU.step
    - moving LDA behavior into instructions.py
"""
import pytest

from tests.helpers import make_cpu

ZERO_FLAG = 1 << 1
NEGATIVE_FLAG = 1 << 7


def test_method_update_zero_and_negative_flags_exists():
    """Optative:
    Declare constants on top of CPU:

    ZERO_FLAG = 1 << 1
    NEGATIVE_FLAG = 1 << 7

    This will help you to have clearest methods

    Objetive:
    Declare in cpu _update_zero_and_negative_flags(self, value: int)
    """
    cpu = make_cpu()

    assert hasattr(cpu, "_update_zero_and_negative_flags")
    assert callable(cpu._update_zero_and_negative_flags)
    
# ---------------------------------------
# Extra tests for check correct behaviour
@pytest.mark.parametrize(
    ("value", "zero_is_set", "negative_is_set"),
    [
        (0x00, True, False),
        (0x01, False, False),
        (0x7F, False, False),
        (0x80, False, True),
        (0xFF, False, True),
    ],
)
def test_update_zero_and_negative_flags_uses_received_value(
    value,
    zero_is_set,
    negative_is_set,
):
    """
    Objective:
    The helper must update Z and N using the received value.

    This protects the refactor: the method should not depend directly on
    cpu.a, because later it can be reused by other registers/instructions.
    """
    cpu = make_cpu()

    cpu.a = 0x00 if value != 0x00 else 0x80
    cpu._update_zero_and_negative_flags(value)

    assert bool(cpu.p & ZERO_FLAG) is zero_is_set
    assert bool(cpu.p & NEGATIVE_FLAG) is negative_is_set


def test_update_zero_and_negative_flags_preserves_other_flags():
    """
    Objective:
    The helper should only modify Zero and Negative flags.

    Other processor status flags must keep their previous value.
    """
    cpu = make_cpu()
    other_flags = 0b0010_1101
    cpu.p = other_flags | ZERO_FLAG | NEGATIVE_FLAG

    cpu._update_zero_and_negative_flags(0x01)

    assert (cpu.p & ZERO_FLAG) == 0
    assert (cpu.p & NEGATIVE_FLAG) == 0
    assert (cpu.p & other_flags) == other_flags
