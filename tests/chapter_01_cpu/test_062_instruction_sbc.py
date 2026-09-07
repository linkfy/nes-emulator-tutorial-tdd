"""
Test 062 - Add the core SBC instruction.

File to update:
    emulator/cpu/instructions.py

Symbol to add:
    instructions.sbc

Why this step exists:
SBC introduces subtraction as a value-based core instruction before any opcode is
wired. The 6502 Carry flag means "no borrow", so subtraction can use addition of
the operand's eight-bit complement plus Carry.

Complete example implementation:

    # emulator/cpu/instructions.py
    def sbc(cpu: CPU, value: int):
        carry = int(cpu.flags.get_carry_flag())
        a = cpu.a
        value_inverted = (~value) & 0xFF
        result = a + value_inverted + carry
        result_8 = result & 0xFF

        cpu.flags.set_carry_flag(result > 0xFF)
        cpu.flags.set_zero_flag(result_8 == 0)
        cpu.flags.set_negative_flag((result_8 & 0x80) != 0)
        overflow = ((result_8 ^ a) & (result_8 ^ value_inverted)) & 0x80
        cpu.flags.set_overflow_flag(overflow != 0)
        cpu.a = result_8

Important invariants:
    - Carry set subtracts only `value`; Carry clear subtracts one extra
    - A is reduced to the final eight-bit result
    - Carry is set exactly when no borrow occurs
    - Zero and Negative follow the final eight-bit result
    - Overflow follows signed subtraction, not unsigned borrow

Common misconception:
Python's raw `~value` is negative because integers are unbounded. Mask it with
`& 0xFF` before addition; also do not treat Carry as a conventional borrow bit.

Out of scope:
    - every SBC opcode handler and opcode-table entry
    - fetching operands or selecting addressing modes inside `sbc`
    - decimal-mode arithmetic and cycle timing

Reference:
https://www.nesdev.org/wiki/Instruction_reference#SBC
"""
import inspect

from emulator.cpu import instructions
from tests.helpers import make_cpu


def test_sbc_instruction_exists():
    """
    Objective:
    Create in instructions.py:
        def sbc(cpu, value):
            ...

    Implementation shape:
        carry = int(cpu.flags.get_carry_flag())
        a = cpu.a
        value_inverted = (~value) & 0xFF
        result = a + value_inverted + carry
        result_8 = result & 0xFF

        cpu.flags.set_carry_flag(result > 0xFF)
        cpu.flags.set_zero_flag(result_8 == 0)
        cpu.flags.set_negative_flag((result_8 & 0x80) != 0)

        overflow = ((result_8 ^ a) & (result_8 ^ value_inverted) & 0x80) != 0
        cpu.flags.set_overflow_flag(overflow)

        cpu.a = result_8
    """
    assert hasattr(instructions, "sbc")
    assert callable(instructions.sbc)
    assert list(inspect.signature(instructions.sbc).parameters) == ["cpu", "value"]


def test_sbc_subtracts_value_when_carry_is_set():
    """
    Objective:
    If Carry is set, SBC subtracts only the value.

    Mental model:
        SBC = A - value - (1 - Carry)

    Example:
        A = 0x10
        value = 0x01
        Carry = 1
        result = 0x0F
    """
    cpu = make_cpu()
    cpu.a = 0x10
    cpu.flags.set_carry_flag(True)

    instructions.sbc(cpu, 0x01)

    assert cpu.a == 0x0F
    assert cpu.flags.get_carry_flag() is True
    assert cpu.flags.get_zero_flag() is False
    assert cpu.flags.get_negative_flag() is False
    assert cpu.flags.get_overflow_flag() is False


def test_sbc_subtracts_extra_one_when_carry_is_clear():
    """
    Objective:
    If Carry is clear, SBC subtracts value + 1.

    This is the confusing part:
    Carry clear means there is a borrow.

    Example:
        A = 0x10
        value = 0x01
        Carry = 0
        result = 0x0E
    """
    cpu = make_cpu()
    cpu.a = 0x10
    cpu.flags.set_carry_flag(False)

    instructions.sbc(cpu, 0x01)

    assert cpu.a == 0x0E
    assert cpu.flags.get_carry_flag() is True


def test_sbc_clears_carry_flag_when_borrow_happens():
    """
    Objective:
    Carry flag is clear when subtraction needs a borrow.

    Example:
        A = 0x00
        value = 0x01
        Carry = 1

    Math:
        0x00 - 0x01 = -1

    8-bit result:
        0xFF

    Carry:
        clear, because borrow happened.
    """
    cpu = make_cpu()
    cpu.a = 0x00
    cpu.flags.set_carry_flag(True)

    instructions.sbc(cpu, 0x01)

    assert cpu.a == 0xFF
    assert cpu.flags.get_carry_flag() is False
    assert cpu.flags.get_negative_flag() is True
    assert cpu.flags.get_zero_flag() is False


def test_sbc_sets_zero_flag_when_8_bit_result_is_zero():
    """
    Objective:
    Zero flag follows the final 8-bit result.

    Example:
        A = 0x01
        value = 0x01
        Carry = 1
        result = 0x00
    """
    cpu = make_cpu()
    cpu.a = 0x01
    cpu.flags.set_carry_flag(True)

    instructions.sbc(cpu, 0x01)

    assert cpu.a == 0x00
    assert cpu.flags.get_zero_flag() is True
    assert cpu.flags.get_carry_flag() is True


def test_sbc_sets_negative_flag_from_bit_7_of_8_bit_result():
    """
    Objective:
    Negative flag follows bit 7 of the final 8-bit result.

    Example:
        A = 0x00
        value = 0x01
        Carry = 1
        result = 0xFF

    0xFF has bit 7 active, so Negative is set.
    """
    cpu = make_cpu()
    cpu.a = 0x00
    cpu.flags.set_carry_flag(True)

    instructions.sbc(cpu, 0x01)

    assert cpu.a == 0xFF
    assert cpu.flags.get_negative_flag() is True


def test_sbc_sets_overflow_on_signed_positive_minus_negative_overflow():
    """
    Objective:
    Overflow is set when signed subtraction cannot fit in 8 bits.

    Example:
        A = 0x7F   # +127
        value = 0xFF  # -1 signed
        Carry = 1

    Signed math:
        +127 - (-1) = +128

    +128 cannot fit in signed 8-bit, so Overflow is set.

    With inverted-value implementation:
        value_inverted = (~value) & 0xFF
        overflow = ((result_8 ^ A) & (result_8 ^ value_inverted) & 0x80) != 0
    """
    cpu = make_cpu()
    cpu.a = 0x7F
    cpu.flags.set_carry_flag(True)

    instructions.sbc(cpu, 0xFF)

    assert cpu.a == 0x80
    assert cpu.flags.get_overflow_flag() is True
    assert cpu.flags.get_negative_flag() is True
    assert cpu.flags.get_carry_flag() is False


def test_sbc_sets_overflow_on_signed_negative_minus_positive_overflow():
    """
    Objective:
    Overflow is also set when a negative minus a positive becomes positive.

    Example:
        A = 0x80      # -128 signed
        value = 0x01  # +1 signed
        Carry = 1

    Signed math:
        -128 - +1 = -129

    -129 cannot fit in signed 8-bit, so Overflow is set.
    Final 8-bit result is 0x7F.
    """
    cpu = make_cpu()
    cpu.a = 0x80
    cpu.flags.set_carry_flag(True)

    instructions.sbc(cpu, 0x01)

    assert cpu.a == 0x7F
    assert cpu.flags.get_overflow_flag() is True
    assert cpu.flags.get_negative_flag() is False
    assert cpu.flags.get_carry_flag() is True


def test_sbc_clears_overflow_when_signed_result_fits():
    """
    Objective:
    Overflow is clear when the signed result fits.

    Example:
        A = 0x10
        value = 0x01
        Carry = 1
        result = 0x0F
    """
    cpu = make_cpu()
    cpu.a = 0x10
    cpu.flags.set_carry_flag(True)
    cpu.flags.set_overflow_flag(True)

    instructions.sbc(cpu, 0x01)

    assert cpu.a == 0x0F
    assert cpu.flags.get_overflow_flag() is False


def test_sbc_masks_python_inverted_value_to_8_bits():
    """
    Objective:
    The implementation must not use raw Python ~value directly.

    Python behavior:
        ~0x01 == -2

    NES 8-bit behavior expected:
        ~0x01 should behave like 0xFE

    Required implementation idea:
        value_inverted = (~value) & 0xFF

    This test is a proof case:
        A = 0x10
        value = 0x01
        Carry = 1
        result must be 0x0F
    """
    cpu = make_cpu()
    cpu.a = 0x10
    cpu.flags.set_carry_flag(True)

    instructions.sbc(cpu, 0x01)

    assert cpu.a == 0x0F
