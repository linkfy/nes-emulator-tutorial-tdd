"""Lesson 103: implement accumulator-targeted ROL.

In this step, use memory ``rol`` from lesson 102 as a prerequisite and add only
the register variant. Dispatch is deferred to lesson 104.

Complete example implementation in the production location:
``emulator/cpu/instructions.py::rol_a``::

    def rol_a(cpu: CPU):
        value = cpu.a
        old_carry = int(cpu.flags.get_carry_flag())

        result = (value << 1) | old_carry
        result_8 = result & 0xFF

        # Set flags

        cpu.flags.set_carry_flag((value & 0b1000_0000) != 0)
        cpu.flags.set_zero_flag(result_8 == 0)
        cpu.flags.set_negative_flag((result_8 & 0b1000_0000) != 0)

        cpu.a = result_8

Why this step exists:
Accumulator mode has no effective memory address, so a dedicated
primitive preserves the same rotation semantics while writing ``cpu.a``.

Invariants: old Carry is sampled first and enters bit 0; original A bit 7
becomes Carry; A is constrained to eight bits; Z/N describe the new A; no bus
write occurs.

Misconception: ``cpu.a`` is a value, not an address to pass to ``rol``.  Doing
so would mutate memory at address A and leave the register unchanged.

Out of scope: mapping opcode ``0x2A`` is lesson 104, memory modes are 105-108,
ROR starts at 109, and timing/cycle fidelity is later work.
"""

from emulator.cpu.instructions import rol_a
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG, make_cpu


CARRY_FLAG = 1 << 0


def test_rol_a_rotates_accumulator_left_with_old_carry_clear():
    """Objective: old Carry=0 means new A bit 0 becomes 0."""
    cpu = make_cpu()
    cpu.a = 0b0000_0011

    rol_a(cpu)

    assert cpu.a == 0b0000_0110
    assert (cpu.p & CARRY_FLAG) == 0


def test_rol_a_rotates_accumulator_left_with_old_carry_set():
    """Objective: old Carry=1 is inserted into result bit 0."""
    cpu = make_cpu()
    cpu.p |= CARRY_FLAG
    cpu.a = 0b0000_0010

    rol_a(cpu)

    assert cpu.a == 0b0000_0101
    assert (cpu.p & CARRY_FLAG) == 0


def test_rol_a_sets_carry_from_old_accumulator_bit_7():
    """Objective: old A bit 7 becomes the new Carry flag."""
    cpu = make_cpu()
    cpu.a = 0b1000_0001

    rol_a(cpu)

    assert cpu.a == 0b0000_0010
    assert (cpu.p & CARRY_FLAG) != 0


def test_rol_a_sets_zero_flag_when_result_is_zero():
    """Objective: A=0x80 with old Carry=0 becomes 0x00 and sets Zero."""
    cpu = make_cpu()
    cpu.a = 0x80

    rol_a(cpu)

    assert cpu.a == 0x00
    assert (cpu.p & ZERO_FLAG) != 0
    assert (cpu.p & NEGATIVE_FLAG) == 0
    assert (cpu.p & CARRY_FLAG) != 0


def test_rol_a_sets_negative_flag_from_result_bit_7():
    """Objective: A=0x40 with old Carry=0 becomes 0x80 and sets Negative."""
    cpu = make_cpu()
    cpu.a = 0x40

    rol_a(cpu)

    assert cpu.a == 0x80
    assert (cpu.p & NEGATIVE_FLAG) != 0
    assert (cpu.p & ZERO_FLAG) == 0


def test_rol_a_does_not_write_rotated_result_to_memory():
    """Objective: ROL A writes to A only; it must not treat A as a memory address."""
    cpu = make_cpu()
    cpu.a = 0x20
    cpu.bus.write(0x0020, 0x99)

    rol_a(cpu)

    assert cpu.a == 0x40
    assert cpu.bus.read(0x0020) == 0x99
