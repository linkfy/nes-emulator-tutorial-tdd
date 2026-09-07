"""Lesson 102: implement memory-targeted ROL.

In this step, add only the ROL memory primitive. Accumulator behavior follows
in lesson 103, and opcode exposure belongs to lessons 104-108.

Complete example implementation in the production location:
``emulator/cpu/instructions.py::rol``::

    def rol(cpu: CPU, addr: int):
        value = cpu.bus.read(addr)
        old_carry = int(cpu.flags.get_carry_flag())

        result = (value << 1) | old_carry
        result_8 = result & 0xFF

        # Set flags

        cpu.flags.set_carry_flag((value & 0b1000_0000) != 0)
        cpu.flags.set_zero_flag(result_8 == 0)
        cpu.flags.set_negative_flag((result_8 & 0b1000_0000) != 0)

        cpu.bus.write(addr, result_8)

Why this step exists:
One addressing-independent read/modify/write primitive lets every
memory opcode reuse identical rotation and flag semantics.

Invariants: capture Carry before changing flags; old Carry enters bit 0, old
bit 7 becomes Carry, the stored result is masked to eight bits, and Zero and
Negative derive from that stored result.  Exactly one target address is read
and written; A is unchanged.

Misconception: ROL is not ASL.  It inserts old Carry rather than always
inserting zero, and Carry must come from the original value, not ``result_8``.

Out of scope: accumulator ROL is lesson 103, opcode/addressing adapters are
104-108, and ROR starts at lesson 109; cycle-level bus behavior came later.
"""

from emulator.cpu.instructions import rol
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG, make_cpu


CARRY_FLAG = 1 << 0


def test_rol_memory_rotates_left_with_old_carry_clear():
    """Objective: old Carry=0 means new bit 0 becomes 0."""
    cpu = make_cpu()
    cpu.bus.write(0x0020, 0b0000_0011)

    rol(cpu, 0x0020)

    assert cpu.bus.read(0x0020) == 0b0000_0110
    assert (cpu.p & CARRY_FLAG) == 0


def test_rol_memory_rotates_left_with_old_carry_set():
    """Objective: old Carry=1 is inserted into result bit 0."""
    cpu = make_cpu()
    cpu.p |= CARRY_FLAG
    cpu.bus.write(0x0020, 0b0000_0010)

    rol(cpu, 0x0020)

    assert cpu.bus.read(0x0020) == 0b0000_0101
    assert (cpu.p & CARRY_FLAG) == 0


def test_rol_memory_sets_carry_from_old_bit_7():
    """Objective: old memory bit 7 becomes the new Carry flag."""
    cpu = make_cpu()
    cpu.bus.write(0x0020, 0b1000_0001)

    rol(cpu, 0x0020)

    assert cpu.bus.read(0x0020) == 0b0000_0010
    assert (cpu.p & CARRY_FLAG) != 0


def test_rol_memory_sets_zero_flag_when_result_is_zero():
    """Objective: 0x80 with old Carry=0 becomes 0x00 and sets Zero."""
    cpu = make_cpu()
    cpu.bus.write(0x0020, 0x80)

    rol(cpu, 0x0020)

    assert cpu.bus.read(0x0020) == 0x00
    assert (cpu.p & ZERO_FLAG) != 0
    assert (cpu.p & NEGATIVE_FLAG) == 0
    assert (cpu.p & CARRY_FLAG) != 0


def test_rol_memory_sets_negative_flag_from_result_bit_7():
    """Objective: 0x40 with old Carry=0 becomes 0x80 and sets Negative."""
    cpu = make_cpu()
    cpu.bus.write(0x0020, 0x40)

    rol(cpu, 0x0020)

    assert cpu.bus.read(0x0020) == 0x80
    assert (cpu.p & NEGATIVE_FLAG) != 0
    assert (cpu.p & ZERO_FLAG) == 0
