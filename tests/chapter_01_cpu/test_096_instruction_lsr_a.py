"""
Test 096 - Add the LSR accumulator instruction behavior.

In this step, add accumulator-targeted LSR behavior after the memory primitive
from Test 095.

File and symbol:
    emulator/cpu/instructions.py: lsr_a

Why this step exists:
Accumulator LSR shares the shift and flags of Test 095 but has a different data
destination, so it must update `cpu.a` without treating that register as an address.

Suggested implementation for this step:

    # emulator/cpu/instructions.py
    def lsr_a(cpu: CPU):
        value = cpu.a
        result = value >> 1
        result_8 = result & 0xFF

        # Set flags
        cpu.flags.set_carry_flag((value & 0x01) != 0)
        cpu.flags.set_negative_flag(False)
        cpu.flags.set_zero_flag(result_8 == 0)

        cpu.a = result_8

Important invariants:
    - old A bit 0 replaces Carry
    - Zero follows the final A value and Negative is always cleared
    - no bus read or write occurs
    - memory at an address numerically equal to the old A remains unchanged

Common misconception:
`cpu.a` is the value and destination, not an address to pass to memory `lsr`.

Out of scope:
    - opcode 0x4A wiring in Test 097
    - memory addressing opcodes in Tests 098-101
    - refactoring shared LSR logic or adding cycle timing
"""

from emulator.cpu.instructions import lsr_a
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG, make_cpu


CARRY_FLAG = 1 << 0


def test_lsr_a_shifts_accumulator_right():
    """Objective: A value 0b0000_0110 becomes 0b0000_0011."""
    cpu = make_cpu()
    cpu.a = 0b0000_0110

    lsr_a(cpu)

    assert cpu.a == 0b0000_0011


def test_lsr_a_sets_carry_from_old_accumulator_bit_0():
    """Objective: old A bit 0 is moved into Carry before the right shift."""
    cpu = make_cpu()
    cpu.a = 0b0000_0011

    lsr_a(cpu)

    assert cpu.a == 0b0000_0001
    assert (cpu.p & CARRY_FLAG) != 0


def test_lsr_a_clears_carry_when_old_accumulator_bit_0_was_clear():
    """Objective: Carry is cleared when original A did not have bit 0 set."""
    cpu = make_cpu()
    cpu.p |= CARRY_FLAG
    cpu.a = 0b0000_0010

    lsr_a(cpu)

    assert cpu.a == 0b0000_0001
    assert (cpu.p & CARRY_FLAG) == 0


def test_lsr_a_sets_zero_flag_when_result_is_zero():
    """Objective: A=0x01 shifts to 0x00 and sets Zero flag."""
    cpu = make_cpu()
    cpu.a = 0x01

    lsr_a(cpu)

    assert cpu.a == 0x00
    assert (cpu.p & ZERO_FLAG) != 0


def test_lsr_a_always_clears_negative_flag():
    """Objective: LSR A fills bit 7 with 0, so Negative must be cleared."""
    cpu = make_cpu()
    cpu.p |= NEGATIVE_FLAG
    cpu.a = 0x80

    lsr_a(cpu)

    assert cpu.a == 0x40
    assert (cpu.p & NEGATIVE_FLAG) == 0


def test_lsr_a_does_not_write_shifted_result_to_memory():
    """Objective: LSR A writes to A only; it must not treat A as a memory address."""
    cpu = make_cpu()
    cpu.a = 0x20
    cpu.bus.write(0x0020, 0x99)

    lsr_a(cpu)

    assert cpu.a == 0x10
    assert cpu.bus.read(0x0020) == 0x99
