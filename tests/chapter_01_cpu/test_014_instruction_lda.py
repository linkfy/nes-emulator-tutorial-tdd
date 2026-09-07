"""
Test 014 — Extract the LDA instruction mechanism.

Files to update:
    emulator/cpu/instructions.py
    emulator/cpu/cpu.py

Locations:
    instructions.lda
    CPU.step, existing $A9 and $AD branches

Why this step exists:
An instruction defines the state transition after an operand is available. LDA always
stores a value in A and updates Z/N, regardless of how that value was addressed.

Complete example implementation:

    # emulator/cpu/instructions.py
    def lda(cpu, value: int) -> None:
        cpu.a = value
        cpu._update_zero_and_negative_flags(value)


    # emulator/cpu/cpu.py
    from emulator.cpu.addressing_modes import absolute, immediate
    from emulator.cpu.instructions import lda


    class CPU:
        def step(self) -> None:
            opcode = self.fetch_byte()

            if opcode == 0xA9:
                return lda(self, immediate(self))

            if opcode == 0xAD:
                return lda(self, absolute(self))

            raise NotImplementedError(
                f"Opcode ${opcode:02X} is not implemented"
            )

Important boundaries:
    - the current addressing helpers return values for LDA
    - CPU.step selects the addressing mode
    - lda changes CPU state and flags

Common misconception:
`lda` should not fetch instruction bytes. If it did, instruction behavior would become
coupled to one addressing mode.

Out of scope:
    - zero-page LDA
    - opcode-handler functions and OPCODE_TABLE
    - other load instructions
"""
from emulator.cpu import instructions
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG, make_cpu


def test_lda_instruction_exists():
    """
    Objective:
    Create in instructions.py:
        def lda(cpu, value):
            ...

    LDA means: Load Accumulator.
    The accumulator is the CPU register called A.

    Example inside cpu:
    ...
    if opcode == 0xA9: # LDA Inmediate
        return lda(self, immediate(self))
    ...

    """
    assert hasattr(instructions, "lda")
    assert callable(instructions.lda)


def test_lda_loads_value_into_register_a():
    """
    Objective:
    lda(cpu, value) must put value inside cpu.a.

    Example:
    lda(cpu, 0x42) means cpu.a becomes 0x42.
    """
    cpu = make_cpu()

    instructions.lda(cpu, 0x42)

    assert cpu.a == 0x42


def test_lda_sets_zero_flag_when_value_is_zero():
    """
    Objective:
    If LDA loads 0x00, the Zero flag must be set.
    """
    cpu = make_cpu()

    instructions.lda(cpu, 0x00)

    assert cpu.a == 0x00
    assert (cpu.p & ZERO_FLAG) != 0


def test_lda_clears_zero_flag_when_value_is_not_zero():
    """
    Objective:
    If LDA loads a value different from 0x00, the Zero flag must be clear.
    """
    cpu = make_cpu()
    cpu.p |= ZERO_FLAG

    instructions.lda(cpu, 0x01)

    assert cpu.a == 0x01
    assert (cpu.p & ZERO_FLAG) == 0


def test_lda_sets_negative_flag_when_bit_7_is_one():
    """
    Objective:
    If LDA loads a value with bit 7 active, the Negative flag must be set.

    Example:
    0x80 is 1000_0000, so bit 7 is active.
    """
    cpu = make_cpu()

    instructions.lda(cpu, 0x80)

    assert cpu.a == 0x80
    assert (cpu.p & NEGATIVE_FLAG) != 0


def test_lda_clears_negative_flag_when_bit_7_is_zero():
    """
    Objective:
    If LDA loads a value with bit 7 inactive, the Negative flag must be clear.

    Example:
    0x7F is 0111_1111, so bit 7 is inactive.
    """
    cpu = make_cpu()
    cpu.p |= NEGATIVE_FLAG

    instructions.lda(cpu, 0x7F)

    assert cpu.a == 0x7F
    assert (cpu.p & NEGATIVE_FLAG) == 0
