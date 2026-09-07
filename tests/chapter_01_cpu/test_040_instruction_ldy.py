"""
Test 040 - Add the core LDY instruction.

File to update:
    emulator/cpu/instructions.py

Location:
    instructions.ldy, beside stx

Why this step exists:
LDY begins the Y-register load family by establishing its value-level behavior before
any LDY opcode is connected. It mirrors LDA and LDX: assign an already-resolved value
to the destination register, then update Zero and Negative.

Complete example implementation:

    # emulator/cpu/instructions.py
    def ldy(cpu: CPU, value):
        cpu.y = value
        cpu._update_zero_and_negative_flags(cpu.y)

Important invariants:
    - ldy receives a value, not an address
    - Y receives the value while A and X remain unchanged
    - Zero is set exactly for $00 and cleared otherwise
    - Negative mirrors bit 7 and is cleared when bit 7 is zero

Common misconception:
Do not fetch an operand or read memory inside `ldy`; future opcode handlers will
resolve a value before calling this instruction.

Out of scope:
    - all LDY opcode handlers and opcode-table entries
    - the STY instruction and its encodings
    - cycle timing
"""
import inspect

from emulator.cpu import instructions
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG, make_cpu


def test_ldy_instruction_exists():
    """
    Objective:
    Create in instructions.py:
        def ldy(cpu, value):
            ...

    Example implementation:
        cpu.y = value
        cpu._update_zero_and_negative_flags(cpu.y)
    """
    assert hasattr(instructions, "ldy")
    assert callable(instructions.ldy)
    assert list(inspect.signature(instructions.ldy).parameters) == ["cpu", "value"]


def test_ldy_loads_value_into_register_y():
    """Objective: ldy(cpu, value) must put value inside cpu.y."""
    cpu = make_cpu()

    instructions.ldy(cpu, 0x42)

    assert cpu.y == 0x42


def test_ldy_sets_zero_flag_when_value_is_zero():
    """Objective: if LDY loads 0x00, Zero flag is set."""
    cpu = make_cpu()

    instructions.ldy(cpu, 0x00)

    assert cpu.y == 0x00
    assert (cpu.p & ZERO_FLAG) != 0


def test_ldy_clears_zero_flag_when_value_is_not_zero():
    """Objective: if LDY loads non-zero value, Zero flag is clear."""
    cpu = make_cpu()
    cpu.p |= ZERO_FLAG

    instructions.ldy(cpu, 0x01)

    assert cpu.y == 0x01
    assert (cpu.p & ZERO_FLAG) == 0


def test_ldy_sets_negative_flag_when_bit_7_is_one():
    """Objective: if LDY loads a value with bit 7 active, Negative flag is set."""
    cpu = make_cpu()

    instructions.ldy(cpu, 0x80)

    assert cpu.y == 0x80
    assert (cpu.p & NEGATIVE_FLAG) != 0


def test_ldy_clears_negative_flag_when_bit_7_is_zero():
    """Objective: if LDY loads a value with bit 7 inactive, Negative flag is clear."""
    cpu = make_cpu()
    cpu.p |= NEGATIVE_FLAG

    instructions.ldy(cpu, 0x7F)

    assert cpu.y == 0x7F
    assert (cpu.p & NEGATIVE_FLAG) == 0
