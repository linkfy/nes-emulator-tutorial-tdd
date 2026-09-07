"""
Test 050 - Add the core TAX, TXA, TAY, and TYA instructions.

File to update:
    emulator/cpu/instructions.py

Locations:
    instructions.tax
    instructions.txa
    instructions.tay
    instructions.tya

Why this step exists:
These implied-addressing operations copy between A, X, and Y without fetching an
operand. Each destination value then uses the same Zero/Negative update already used
by load instructions.

Complete example implementation:

    # emulator/cpu/instructions.py
    def tax(cpu: CPU):
        cpu.x = cpu.a
        cpu._update_zero_and_negative_flags(cpu.x)


    def txa(cpu: CPU):
        cpu.a = cpu.x
        cpu._update_zero_and_negative_flags(cpu.a)


    def tay(cpu: CPU):
        cpu.y = cpu.a
        cpu._update_zero_and_negative_flags(cpu.y)


    def tya(cpu: CPU):
        cpu.a = cpu.y
        cpu._update_zero_and_negative_flags(cpu.a)

Important invariants:
    - TAX copies A to X, TXA copies X to A, TAY copies A to Y, and TYA copies Y to A
    - the source register remains unchanged
    - Zero is set exactly for $00 and Negative mirrors destination bit 7
    - both flags are also cleared when the copied value no longer satisfies them
    - these functions fetch no bytes and perform no bus access

Common misconception:
Updating only flags that become set leaves stale state behind. Reuse
`cpu._update_zero_and_negative_flags` with the destination register after every copy.

Out of scope:
    - transfer opcode imports and OPCODE_TABLE entries, introduced in Test 051
    - stack-pointer transfers
    - cycle timing
"""
import inspect

from emulator.cpu import instructions
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG, make_cpu


def test_tax_instruction_exists():
    """
    Objective:
    Create in instructions.py:
        def tax(cpu):
            ...

    TAX means:
        X = A
    """
    assert hasattr(instructions, "tax")
    assert callable(instructions.tax)
    assert list(inspect.signature(instructions.tax).parameters) == ["cpu"]


def test_txa_instruction_exists():
    """
    Objective:
    Create in instructions.py:
        def txa(cpu):
            ...

    TXA means:
        A = X
    """
    assert hasattr(instructions, "txa")
    assert callable(instructions.txa)
    assert list(inspect.signature(instructions.txa).parameters) == ["cpu"]


def test_tay_instruction_exists():
    """
    Objective:
    Create in instructions.py:
        def tay(cpu):
            ...

    TAY means:
        Y = A
    """
    assert hasattr(instructions, "tay")
    assert callable(instructions.tay)
    assert list(inspect.signature(instructions.tay).parameters) == ["cpu"]


def test_tya_instruction_exists():
    """
    Objective:
    Create in instructions.py:
        def tya(cpu):
            ...

    TYA means:
        A = Y
    """
    assert hasattr(instructions, "tya")
    assert callable(instructions.tya)
    assert list(inspect.signature(instructions.tya).parameters) == ["cpu"]


def test_tax_transfers_a_to_x_and_updates_flags():
    """Objective: TAX copies A into X and updates Zero/Negative flags."""
    cpu = make_cpu()
    cpu.a = 0x80

    instructions.tax(cpu)

    assert cpu.x == 0x80
    assert (cpu.p & ZERO_FLAG) == 0
    assert (cpu.p & NEGATIVE_FLAG) != 0


def test_txa_transfers_x_to_a_and_updates_flags():
    """Objective: TXA copies X into A and updates Zero/Negative flags."""
    cpu = make_cpu()
    cpu.x = 0x00

    instructions.txa(cpu)

    assert cpu.a == 0x00
    assert (cpu.p & ZERO_FLAG) != 0
    assert (cpu.p & NEGATIVE_FLAG) == 0


def test_tay_transfers_a_to_y_and_updates_flags():
    """Objective: TAY copies A into Y and updates Zero/Negative flags."""
    cpu = make_cpu()
    cpu.a = 0x42
    cpu.p |= ZERO_FLAG | NEGATIVE_FLAG

    instructions.tay(cpu)

    assert cpu.y == 0x42
    assert (cpu.p & ZERO_FLAG) == 0
    assert (cpu.p & NEGATIVE_FLAG) == 0


def test_tya_transfers_y_to_a_and_updates_flags():
    """Objective: TYA copies Y into A and updates Zero/Negative flags."""
    cpu = make_cpu()
    cpu.y = 0x80

    instructions.tya(cpu)

    assert cpu.a == 0x80
    assert (cpu.p & ZERO_FLAG) == 0
    assert (cpu.p & NEGATIVE_FLAG) != 0
