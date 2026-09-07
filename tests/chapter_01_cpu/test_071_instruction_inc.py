"""Lesson 071: add the INC instruction primitive.

In this step, add only `emulator/cpu/instructions.py:inc`. The opcode import,
handlers, and table entries belong to lessons 072-075.

Why this step exists:
INC is a memory read-modify-write operation. Keeping the arithmetic
in one instruction primitive lets each later addressing-mode handler resolve an
address and delegate identical mutation and flag behavior.

Suggested implementation in `emulator/cpu/instructions.py`, inserted
after `sbc`:

    def inc(cpu: CPU, address: int):
        value = cpu.bus.read(address)
        result = value + 1
        result_8 = result & 0xFF

        # Set flags
        cpu.flags.set_negative_flag((result_8 & 0b1000_0000) != 0)
        cpu.flags.set_zero_flag(result_8 == 0)

        # Set value on address
        cpu.bus.write(address, result_8)

Invariants: `address` is an effective address, not an operand value; the byte is
read and written through `cpu.bus`; masking provides 8-bit wraparound; Zero and
Negative reflect the masked result; Carry, Overflow, and A/X/Y remain unchanged.

Misconception: do not increment A or pass `cpu.bus.read(address)` to `inc`.
INC owns the memory read and writes the result back to the same address.

Out of scope: opcode wiring is not part of step 071; zero-page through
absolute-X integration follows in lessons 072-075.
"""
import inspect

from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG, make_cpu
from emulator.cpu import instructions


def test_inc_instruction_exists():
    """
    Objective:
    Create in instructions.py:
        def inc(cpu, address):
            ...

    Implementation shape:
        value = cpu.bus.read(address)
        result = value + 1
        result_8 = result & 0xFF

        cpu.bus.write(address, result_8)
        cpu.flags.set_zero_flag(result_8 == 0)
        cpu.flags.set_negative_flag((result_8 & 0x80) != 0)

    Important:
    INC receives an address, not a value.
    INC modifies memory, not A/X/Y directly.
    """
    assert hasattr(instructions, "inc")
    assert callable(instructions.inc)
    assert list(inspect.signature(instructions.inc).parameters) == ["cpu", "address"]


def test_inc_reads_memory_adds_one_and_writes_back():
    """
    Objective:
    inc(cpu, address) must increment the value stored at that address.

    Example:
    RAM[$0010] is 0x41.
    After INC, RAM[$0010] becomes 0x42.
    """
    cpu = make_cpu()
    cpu.bus.write(0x0010, 0x41)

    instructions.inc(cpu, 0x0010)

    assert cpu.bus.read(0x0010) == 0x42


def test_inc_wraps_from_ff_to_zero_and_sets_zero_flag():
    """
    Objective:
    INC works with 8-bit values.

    Example:
    0xFF + 1 becomes 0x00.
    Zero flag is set.
    """
    cpu = make_cpu()
    cpu.bus.write(0x0010, 0xFF)

    instructions.inc(cpu, 0x0010)

    assert cpu.bus.read(0x0010) == 0x00
    assert (cpu.p & ZERO_FLAG) != 0
    assert (cpu.p & NEGATIVE_FLAG) == 0


def test_inc_sets_negative_flag_when_result_has_bit_7_active():
    """
    Objective:
    INC updates the Negative flag from bit 7 of the result.

    Example:
    0x7F + 1 becomes 0x80.
    0x80 has bit 7 active, so Negative flag is set.
    """
    cpu = make_cpu()
    cpu.bus.write(0x0010, 0x7F)

    instructions.inc(cpu, 0x0010)

    assert cpu.bus.read(0x0010) == 0x80
    assert (cpu.p & NEGATIVE_FLAG) != 0
    assert (cpu.p & ZERO_FLAG) == 0


def test_inc_does_not_change_carry_or_overflow_flags():
    """
    Objective:
    INC only updates Zero and Negative flags.

    It must not modify Carry or Overflow.
    """
    cpu = make_cpu()
    cpu.bus.write(0x0010, 0x01)
    cpu.flags.set_carry_flag(True)
    cpu.flags.set_overflow_flag(True)

    instructions.inc(cpu, 0x0010)

    assert cpu.bus.read(0x0010) == 0x02
    assert cpu.flags.get_carry_flag() is True
    assert cpu.flags.get_overflow_flag() is True
