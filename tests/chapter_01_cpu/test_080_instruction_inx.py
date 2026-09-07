"""Lesson 080: add the INX instruction primitive.

In this step, add only `emulator/cpu/instructions.py:inx`. Opcode `0xE8` is
lesson 081, while `dex` and opcode `0xCA` are lessons 082-083.

Why this step exists:
INX is implied register behavior, so it needs no addressing helper or
bus access. The primitive performs 8-bit arithmetic and derives flags directly
from the new X value.

Suggested implementation in `emulator/cpu/instructions.py`, after
`dec`:

    def inx(cpu: CPU):
        result = cpu.x + 1
        result_8 = result & 0xFF

        # Set flags
        cpu.flags.set_negative_flag((result_8 & 0b1000_0000) != 0)
        cpu.flags.set_zero_flag(result_8 == 0)

        cpu.x = result_8

Invariants: X remains eight-bit (`$FF + 1 == $00`); Zero and Negative reflect
the masked result; A, Y, memory, Carry, and Overflow remain unchanged; this
primitive itself does not fetch operands or advance PC.

Misconception: INX is not memory INC with X as an address. It mutates the X
register directly and takes only `cpu`.

Out of scope: importing and mapping `inx`, adding `dex`, and mapping `0xCA`
belong to lessons 081-083.
"""

from emulator.cpu.instructions import inx
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG, make_cpu


CARRY_FLAG = 1 << 0
OVERFLOW_FLAG = 1 << 6


def test_inx_increments_x_register():
    """Objective: X increases by one and remains an 8-bit register value."""
    cpu = make_cpu()
    cpu.x = 0x10

    inx(cpu)

    assert cpu.x == 0x11


def test_inx_wraps_from_ff_to_00_and_sets_zero_flag():
    """Objective: 0xFF + 1 wraps to 0x00 and sets Zero flag."""
    cpu = make_cpu()
    cpu.x = 0xFF

    inx(cpu)

    assert cpu.x == 0x00
    assert (cpu.p & ZERO_FLAG) != 0
    assert (cpu.p & NEGATIVE_FLAG) == 0


def test_inx_sets_negative_flag_when_result_has_bit_7_set():
    """Objective: 0x7F + 1 becomes 0x80, so Negative flag is set."""
    cpu = make_cpu()
    cpu.x = 0x7F

    inx(cpu)

    assert cpu.x == 0x80
    assert (cpu.p & NEGATIVE_FLAG) != 0
    assert (cpu.p & ZERO_FLAG) == 0


def test_inx_does_not_modify_carry_or_overflow_flags():
    """Objective: INX updates Z/N only; Carry and Overflow are preserved."""
    cpu = make_cpu()
    cpu.x = 0x01
    cpu.p |= CARRY_FLAG
    cpu.p |= OVERFLOW_FLAG

    inx(cpu)

    assert cpu.x == 0x02
    assert (cpu.p & CARRY_FLAG) != 0
    assert (cpu.p & OVERFLOW_FLAG) != 0
