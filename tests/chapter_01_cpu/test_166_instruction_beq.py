"""Lesson 166: implement Branch if Equal behavior.

Why this step exists:
Comparisons and other earlier instructions encode equality as Zero set, so BEQ
only reads that existing condition and applies the signed offset.

In this step, following BCC and BCS, add exactly:

``emulator/cpu/instructions.py::beq``::

    def beq(cpu: CPU, offset: int):
        if cpu.flags.get_zero_flag():
            cpu.pc = (cpu.pc + offset) & 0xFFFF

The offset is applied to the PC after the operand, and the mask preserves
16-bit wrapping.

Invariants: Zero set takes the branch and Zero clear leaves PC unchanged;
neither path changes flags, other registers, or memory.  Misconception: BEQ
does not compare values itself and does not set Zero; it consumes prior state.

Out of scope: BNE and the remaining branch semantics are lessons 167-171.
Opcode imports, relative handlers, and table entries wait for lessons 172-179.
"""

from emulator.cpu.instructions import beq
from tests.helpers import make_cpu


def test_beq_branches_when_zero_flag_is_set():
    """Objective: if Zero is set, PC is changed by the signed offset."""
    cpu = make_cpu()
    cpu.pc = 0x8002
    cpu.flags.set_zero_flag(True)

    beq(cpu, 0x05)

    assert cpu.pc == 0x8007


def test_beq_does_not_branch_when_zero_flag_is_clear():
    """Objective: if Zero is clear, PC remains unchanged."""
    cpu = make_cpu()
    cpu.pc = 0x8002
    cpu.flags.set_zero_flag(False)

    beq(cpu, 0x05)

    assert cpu.pc == 0x8002


def test_beq_accepts_negative_signed_offsets():
    """Objective: offsets from relative(cpu) may be negative."""
    cpu = make_cpu()
    cpu.pc = 0x8002
    cpu.flags.set_zero_flag(True)

    beq(cpu, -2)

    assert cpu.pc == 0x8000
