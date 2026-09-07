"""Lesson 109: implement memory-targeted ROR.

In this step, after lessons 102-108 complete ROL, add only the ROR memory
primitive. ROR opcode wiring belongs to lessons 111-115.

Complete example implementation in the production location:
``emulator/cpu/instructions.py::ror``::

    def ror(cpu: CPU, addr: int):
        value = cpu.bus.read(addr)
        old_carry = int(cpu.flags.get_carry_flag())

        result = (value >> 1) | (old_carry << 7)
        result_8 = result & 0xFF

        # Set flags

        cpu.flags.set_carry_flag((value & 0x1) != 0)
        cpu.flags.set_zero_flag(result_8 == 0)
        cpu.flags.set_negative_flag((result_8 & 0b1000_0000) != 0)

        cpu.bus.write(addr, result_8)

Why this step exists:
A single addressing-independent memory primitive supplies every
later ROR addressing mode with identical read/modify/write semantics.

Invariants: sample Carry before flags change; old Carry enters bit 7, original
bit 0 becomes Carry, result is eight-bit, and Z/N derive from the stored
result.  Exactly the addressed memory byte changes; A does not.

Misconception: ROR is not LSR.  LSR inserts zero at bit 7, whereas ROR inserts
old Carry; Carry cannot be derived from the shifted result.

Out of scope: accumulator ROR is lesson 110, opcode/addressing wiring is
111-115, and cycle-level bus sequencing is later work.
"""

from emulator.cpu.instructions import ror
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG, make_cpu


CARRY_FLAG = 1 << 0


def test_ror_memory_rotates_right_with_old_carry_clear():
    """Objective: old Carry=0 means new bit 7 becomes 0."""
    cpu = make_cpu()
    cpu.bus.write(0x0020, 0b0000_0110)

    ror(cpu, 0x0020)

    assert cpu.bus.read(0x0020) == 0b0000_0011
    assert (cpu.p & CARRY_FLAG) == 0


def test_ror_memory_rotates_right_with_old_carry_set():
    """Objective: old Carry=1 is inserted into result bit 7."""
    cpu = make_cpu()
    cpu.p |= CARRY_FLAG
    cpu.bus.write(0x0020, 0b0000_0010)

    ror(cpu, 0x0020)

    assert cpu.bus.read(0x0020) == 0b1000_0001
    assert (cpu.p & CARRY_FLAG) == 0


def test_ror_memory_sets_carry_from_old_bit_0():
    """Objective: old memory bit 0 becomes the new Carry flag."""
    cpu = make_cpu()
    cpu.bus.write(0x0020, 0b0000_0011)

    ror(cpu, 0x0020)

    assert cpu.bus.read(0x0020) == 0b0000_0001
    assert (cpu.p & CARRY_FLAG) != 0


def test_ror_memory_sets_zero_flag_when_result_is_zero():
    """Objective: 0x01 with old Carry=0 becomes 0x00 and sets Zero."""
    cpu = make_cpu()
    cpu.bus.write(0x0020, 0x01)

    ror(cpu, 0x0020)

    assert cpu.bus.read(0x0020) == 0x00
    assert (cpu.p & ZERO_FLAG) != 0
    assert (cpu.p & NEGATIVE_FLAG) == 0
    assert (cpu.p & CARRY_FLAG) != 0


def test_ror_memory_sets_negative_flag_from_result_bit_7():
    """Objective: old Carry=1 becomes result bit 7, so Negative is set."""
    cpu = make_cpu()
    cpu.p |= CARRY_FLAG
    cpu.bus.write(0x0020, 0x00)

    ror(cpu, 0x0020)

    assert cpu.bus.read(0x0020) == 0x80
    assert (cpu.p & NEGATIVE_FLAG) != 0
    assert (cpu.p & ZERO_FLAG) == 0
