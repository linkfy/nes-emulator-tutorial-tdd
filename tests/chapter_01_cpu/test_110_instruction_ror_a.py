"""Lesson 110: implement accumulator-targeted ROR.

In this step, use memory ``ror`` from lesson 109 as a prerequisite and add only
``ror_a``. Opcode ``0x6A`` is deferred to lesson 111.

Complete example implementation in the production location:
``emulator/cpu/instructions.py::ror_a``::

    def ror_a(cpu: CPU):
        value = cpu.a
        old_carry = int(cpu.flags.get_carry_flag())

        result = (value >> 1) | (old_carry << 7)
        result_8 = result & 0xFF

        # Set flags

        cpu.flags.set_carry_flag((value & 0x1) != 0)
        cpu.flags.set_zero_flag(result_8 == 0)
        cpu.flags.set_negative_flag((result_8 & 0b1000_0000) != 0)

        cpu.a = result_8

Why this step exists:
Accumulator mode has no effective address, so it needs a register
primitive with the same rotate-through-Carry semantics as memory ROR.

Invariants: old Carry is captured first and enters bit 7; original A bit 0
becomes Carry; A remains eight-bit; Z/N describe new A; memory is untouched.

Misconception: A is a register value, not an address for ``ror``.  Passing it
to the memory primitive would rotate RAM[A] instead of the accumulator.

Out of scope: ``0x6A`` dispatch is lesson 111, memory opcode modes are
112-115, and timing/cycle fidelity is later work.
"""

from emulator.cpu.instructions import ror_a
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG, make_cpu


CARRY_FLAG = 1 << 0


def test_ror_a_rotates_accumulator_right_with_old_carry_clear():
    """Objective: old Carry=0 means new A bit 7 becomes 0."""
    cpu = make_cpu()
    cpu.a = 0b0000_0110

    ror_a(cpu)

    assert cpu.a == 0b0000_0011
    assert (cpu.p & CARRY_FLAG) == 0


def test_ror_a_rotates_accumulator_right_with_old_carry_set():
    """Objective: old Carry=1 is inserted into result bit 7."""
    cpu = make_cpu()
    cpu.p |= CARRY_FLAG
    cpu.a = 0b0000_0010

    ror_a(cpu)

    assert cpu.a == 0b1000_0001
    assert (cpu.p & CARRY_FLAG) == 0


def test_ror_a_sets_carry_from_old_accumulator_bit_0():
    """Objective: old A bit 0 becomes the new Carry flag."""
    cpu = make_cpu()
    cpu.a = 0b0000_0011

    ror_a(cpu)

    assert cpu.a == 0b0000_0001
    assert (cpu.p & CARRY_FLAG) != 0


def test_ror_a_sets_zero_flag_when_result_is_zero():
    """Objective: A=0x01 with old Carry=0 becomes 0x00 and sets Zero."""
    cpu = make_cpu()
    cpu.a = 0x01

    ror_a(cpu)

    assert cpu.a == 0x00
    assert (cpu.p & ZERO_FLAG) != 0
    assert (cpu.p & NEGATIVE_FLAG) == 0
    assert (cpu.p & CARRY_FLAG) != 0


def test_ror_a_sets_negative_flag_from_result_bit_7():
    """Objective: old Carry=1 becomes result bit 7, so Negative is set."""
    cpu = make_cpu()
    cpu.p |= CARRY_FLAG
    cpu.a = 0x00

    ror_a(cpu)

    assert cpu.a == 0x80
    assert (cpu.p & NEGATIVE_FLAG) != 0
    assert (cpu.p & ZERO_FLAG) == 0


def test_ror_a_does_not_write_rotated_result_to_memory():
    """Objective: ROR A writes to A only; it must not treat A as a memory address."""
    cpu = make_cpu()
    cpu.a = 0x20
    cpu.bus.write(0x0020, 0x99)

    ror_a(cpu)

    assert cpu.a == 0x10
    assert cpu.bus.read(0x0020) == 0x99
