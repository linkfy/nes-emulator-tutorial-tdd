"""
Test 053 - Add the addressing-independent ADC instruction.

File to update:
    emulator/cpu/instructions.py

Symbol to create:
    instructions.adc(cpu, value)

Why this step exists:
ADC is arithmetic behavior, not operand decoding. It accepts the value already
resolved by an opcode handler, adds it to A with the incoming Carry, truncates
the result to one byte, and updates C, Z, N, and V through the FlagsHandler from
test 052.

Complete example implementation:

    # emulator/cpu/instructions.py
    def adc(cpu, value: int):
        carry = int(cpu.flags.get_carry_flag())
        old_a = cpu.a
        total = old_a + value + carry
        result = total & 0xFF

        cpu.flags.set_carry_flag(total > 0xFF)
        cpu.flags.set_zero_flag(result == 0)
        cpu.flags.set_negative_flag((result & 0x80) != 0)
        overflow = (result ^ old_a) & (result ^ value) & 0x80
        cpu.flags.set_overflow_flag(overflow != 0)
        cpu.a = result

Important invariants:
    - incoming Carry is read before any flags are changed
    - A stores only the low eight bits of the full sum
    - Carry reports unsigned overflow; Overflow reports signed overflow
    - Zero and Negative are derived from the truncated result
    - flags not named above and registers X/Y remain unchanged

Common misconception:
Carry and Overflow are not interchangeable. Carry comes from bit 8 of the
unsigned sum, while Overflow occurs when equal-sign operands produce a result
with the opposite sign.

Out of scope:
    - every ADC addressing-mode handler and opcode-table entry
    - SBC and decimal-mode arithmetic
    - cycle accounting

Reference:
    https://www.nesdev.org/wiki/Instruction_reference#ADC
"""
import inspect

from emulator.cpu import instructions
from tests.helpers import make_cpu


def test_adc_instruction_exists():
    """
    Objective:
    Create in instructions.py:
        def adc(cpu, value):
            ...

    What it does:
    - Read the current Carry flag.
    - Add A + value + carry.
    - Store only the low 8 bits in A.
    - Update flags: C, Z, N, V.

    Example:
        A = 0x01
        value = 0x02
        Carry = 0
        result = 0x03
    """
    assert hasattr(instructions, "adc")
    assert callable(instructions.adc)
    assert list(inspect.signature(instructions.adc).parameters) == ["cpu", "value"]


def test_adc_adds_value_to_register_a_without_carry_in():
    """
    Objective:
    ADC must add value to register A.

    Example:
    A is 0x10.
    value is 0x05.
    Carry is clear.
    A becomes 0x15.
    """
    cpu = make_cpu()
    cpu.a = 0x10
    cpu.flags.set_carry_flag(False)

    instructions.adc(cpu, 0x05)

    assert cpu.a == 0x15
    assert cpu.flags.get_carry_flag() is False
    assert cpu.flags.get_zero_flag() is False
    assert cpu.flags.get_negative_flag() is False
    assert cpu.flags.get_overflow_flag() is False


def test_adc_includes_carry_in():
    """
    Objective:
    ADC must include the old Carry flag in the addition.

    Example:
    A is 0x10.
    value is 0x05.
    Carry is set.
    A becomes 0x16.
    """
    cpu = make_cpu()
    cpu.a = 0x10
    cpu.flags.set_carry_flag(True)

    instructions.adc(cpu, 0x05)

    assert cpu.a == 0x16


def test_adc_sets_carry_flag_when_result_is_bigger_than_8_bits():
    """
    Objective:
    If the full result is greater than 0xFF, Carry flag must be set.

    Example:
    0xFF + 0x01 = 0x100.
    A stores only 0x00.
    Carry is set.
    Zero is set.
    """
    cpu = make_cpu()
    cpu.a = 0xFF
    cpu.flags.set_carry_flag(False)

    instructions.adc(cpu, 0x01)

    assert cpu.a == 0x00
    assert cpu.flags.get_carry_flag() is True
    assert cpu.flags.get_zero_flag() is True
    assert cpu.flags.get_negative_flag() is False


def test_adc_sets_negative_flag_from_bit_7_of_8_bit_result():
    """
    Objective:
    Negative flag follows bit 7 of the 8-bit result.

    Example:
    0x40 + 0x40 = 0x80.
    Bit 7 is active, so Negative is set.
    """
    cpu = make_cpu()
    cpu.a = 0x40
    cpu.flags.set_carry_flag(False)

    instructions.adc(cpu, 0x40)

    assert cpu.a == 0x80
    assert cpu.flags.get_negative_flag() is True


def test_adc_sets_overflow_flag_on_signed_positive_overflow():
    """
    Objective:
    Overflow flag is set when signed addition overflows.

    Reference formula:
        (result ^ A) & (result ^ value) & 0x80

    Example:
    0x7F is +127.
    0x01 is +1.
    0x7F + 0x01 = 0x80.

    As signed 8-bit numbers, +127 + +1 cannot fit.
    Overflow is set.
    """
    cpu = make_cpu()
    cpu.a = 0x7F
    cpu.flags.set_carry_flag(False)

    instructions.adc(cpu, 0x01)

    assert cpu.a == 0x80
    assert cpu.flags.get_overflow_flag() is True
    assert cpu.flags.get_negative_flag() is True
    assert cpu.flags.get_carry_flag() is False


def test_adc_sets_overflow_flag_on_signed_negative_overflow():
    """
    Objective:
    Overflow also happens when two negative numbers produce a positive result.

    Example:
    0x80 is -128 as signed 8-bit.
    0x80 + 0x80 = 0x00 with Carry.
    Signed result cannot fit, so Overflow is set.
    """
    cpu = make_cpu()
    cpu.a = 0x80
    cpu.flags.set_carry_flag(False)

    instructions.adc(cpu, 0x80)

    assert cpu.a == 0x00
    assert cpu.flags.get_carry_flag() is True
    assert cpu.flags.get_zero_flag() is True
    assert cpu.flags.get_overflow_flag() is True
    assert cpu.flags.get_negative_flag() is False


def test_adc_clears_overflow_when_signs_are_different():
    """
    Objective:
    Adding values with different signs does not create signed overflow.

    Example:
    0x7F is positive.
    0xFF is negative (-1 as signed 8-bit).
    Result is 0x7E.
    Overflow is clear.
    """
    cpu = make_cpu()
    cpu.a = 0x7F
    cpu.flags.set_carry_flag(False)
    cpu.flags.set_overflow_flag(True)

    instructions.adc(cpu, 0xFF)

    assert cpu.a == 0x7E
    assert cpu.flags.get_overflow_flag() is False
    assert cpu.flags.get_carry_flag() is True
