"""
Test 095 - Add the LSR memory instruction behavior.

In this step, add only memory-targeted LSR behavior. Accumulator behavior and
opcode wiring follow in Tests 096-101.

File and symbol:
    emulator/cpu/instructions.py: lsr

Why this step exists:
The instruction layer must define LSR's read/modify/write and flag semantics once
before addressing-mode handlers are wired. This transition is memory-only.

Suggested implementation for this step:

    # emulator/cpu/instructions.py
    def lsr(cpu: CPU, addr: int):
        value = cpu.bus.read(addr)
        result = value >> 1
        result_8 = result & 0xFF

        # Set flags
        cpu.flags.set_carry_flag((value & 0x01) != 0)
        cpu.flags.set_negative_flag(False)
        cpu.flags.set_zero_flag(result_8 == 0)

        cpu.bus.write(addr, result_8)

Important invariants:
    - Carry is replaced from the original bit 0, including being cleared when absent
    - Zero is based on the final 8-bit result and Negative is always cleared
    - exactly the supplied memory address is read and written; A is unchanged
    - logical right shift introduces zero at bit 7

Common misconception:
Carry does not come from the result and Negative is not copied from the old bit 7.

Out of scope:
    - accumulator behavior in Test 096 and opcode wiring in Tests 097-101
    - cycle-accurate read/modify/write sequencing
    - unrelated cleanup to `asl_a`
"""

from emulator.cpu.instructions import lsr
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG, make_cpu


CARRY_FLAG = 1 << 0


def test_lsr_memory_shifts_value_right_and_writes_result_back():
    """Objective: memory value 0b0000_0110 becomes 0b0000_0011."""
    cpu = make_cpu()
    cpu.bus.write(0x0020, 0b0000_0110)

    lsr(cpu, 0x0020)

    assert cpu.bus.read(0x0020) == 0b0000_0011


def test_lsr_memory_sets_carry_from_old_bit_0():
    """Objective: old bit 0 is moved into Carry before the right shift."""
    cpu = make_cpu()
    cpu.bus.write(0x0020, 0b0000_0011)

    lsr(cpu, 0x0020)

    assert cpu.bus.read(0x0020) == 0b0000_0001
    assert (cpu.p & CARRY_FLAG) != 0


def test_lsr_memory_clears_carry_when_old_bit_0_was_clear():
    """Objective: Carry is cleared when the original value did not have bit 0 set."""
    cpu = make_cpu()
    cpu.p |= CARRY_FLAG
    cpu.bus.write(0x0020, 0b0000_0010)

    lsr(cpu, 0x0020)

    assert cpu.bus.read(0x0020) == 0b0000_0001
    assert (cpu.p & CARRY_FLAG) == 0


def test_lsr_memory_sets_zero_flag_when_result_is_zero():
    """Objective: 0x01 >> 1 becomes 0x00 and sets Zero flag."""
    cpu = make_cpu()
    cpu.bus.write(0x0020, 0x01)

    lsr(cpu, 0x0020)

    assert cpu.bus.read(0x0020) == 0x00
    assert (cpu.p & ZERO_FLAG) != 0


def test_lsr_memory_always_clears_negative_flag():
    """Objective: LSR fills bit 7 with 0, so Negative must be cleared."""
    cpu = make_cpu()
    cpu.p |= NEGATIVE_FLAG
    cpu.bus.write(0x0020, 0x80)

    lsr(cpu, 0x0020)

    assert cpu.bus.read(0x0020) == 0x40
    assert (cpu.p & NEGATIVE_FLAG) == 0
