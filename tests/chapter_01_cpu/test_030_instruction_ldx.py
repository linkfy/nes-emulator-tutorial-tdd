"""
Test 030 — Add the core LDX instruction.

File to update:
    emulator/cpu/instructions.py

Location:
    instructions.ldx, beside lda and sta

Why this step exists:
LDX starts the next load family while preserving the instruction/opcode boundary
established for LDA. The core instruction receives an already-resolved value, stores
it in X, and applies the same Zero/Negative rules as `lda`.

Complete example implementation:

    # emulator/cpu/instructions.py
    def ldx(cpu, value) -> None:
        cpu.x = value
        cpu._update_zero_and_negative_flags(cpu.x)

Important invariants:
    - ldx receives a value, not an address
    - X receives the value while A and Y remain unchanged
    - Zero is set exactly for $00 and cleared otherwise
    - Negative mirrors bit 7 and is cleared when bit 7 is zero

Common misconception:
Do not fetch an operand or read the bus inside `ldx`; opcode handlers will perform
addressing and memory access before calling this instruction.

Out of scope:
    - all LDX opcode handlers and opcode-table entries
    - zero-page,Y integration with an opcode
    - the later FlagsHandler refactor
"""
import inspect

from emulator.cpu import instructions
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG, make_cpu


def test_ldx_instruction_exists():
    """
    Objective:
    Create in instructions.py:
        def ldx(cpu, value):
            ...

    Example implementation:
        cpu.x = value
        cpu._update_zero_and_negative_flags(cpu.x)
    """
    assert hasattr(instructions, "ldx")
    assert callable(instructions.ldx)
    assert list(inspect.signature(instructions.ldx).parameters) == ["cpu", "value"]


def test_ldx_loads_value_into_register_x():
    """Objective: ldx(cpu, value) must put value inside cpu.x."""
    cpu = make_cpu()

    instructions.ldx(cpu, 0x42)

    assert cpu.x == 0x42


def test_ldx_sets_zero_flag_when_value_is_zero():
    """Objective: if LDX loads 0x00, Zero flag is set."""
    cpu = make_cpu()

    instructions.ldx(cpu, 0x00)

    assert cpu.x == 0x00
    assert (cpu.p & ZERO_FLAG) != 0


def test_ldx_clears_zero_flag_when_value_is_not_zero():
    """Objective: if LDX loads non-zero value, Zero flag is clear."""
    cpu = make_cpu()
    cpu.p |= ZERO_FLAG

    instructions.ldx(cpu, 0x01)

    assert cpu.x == 0x01
    assert (cpu.p & ZERO_FLAG) == 0


def test_ldx_sets_negative_flag_when_bit_7_is_one():
    """Objective: if LDX loads a value with bit 7 active, Negative flag is set."""
    cpu = make_cpu()

    instructions.ldx(cpu, 0x80)

    assert cpu.x == 0x80
    assert (cpu.p & NEGATIVE_FLAG) != 0


def test_ldx_clears_negative_flag_when_bit_7_is_zero():
    """Objective: if LDX loads a value with bit 7 inactive, Negative flag is clear."""
    cpu = make_cpu()
    cpu.p |= NEGATIVE_FLAG

    instructions.ldx(cpu, 0x7F)

    assert cpu.x == 0x7F
    assert (cpu.p & NEGATIVE_FLAG) == 0
