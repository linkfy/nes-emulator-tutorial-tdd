"""Lesson 167: implement Branch if Not Equal behavior.

Why this step exists:
Zero clear records a non-equal result from an earlier operation, so BNE can
branch without performing another comparison.

In this step, add exactly this implementation:

``emulator/cpu/instructions.py::bne``::

    def bne(cpu: CPU, offset: int):
        if not cpu.flags.get_zero_flag():
            cpu.pc = (cpu.pc + offset) & 0xFFFF

The function applies the signed displacement to the already advanced PC and
constrains the target to 16 bits.

Invariants: Zero clear takes the branch, including wrapping underflow or
overflow; Zero set leaves PC unchanged.  Flags, other registers, and memory
remain untouched.  Misconception: BNE tests Zero, not Negative, and does not
perform a comparison or fetch an operand.

Out of scope: BPL/BMI/BVC/BVS are lessons 168-171.  Branch opcode imports,
handlers, and table entries are deferred to lessons 172-179.
"""

from emulator.cpu.instructions import bne
from tests.helpers import make_cpu


def test_bne_branches_when_zero_flag_is_clear():
    """Objective: if Zero is clear, PC is changed by the signed offset."""
    cpu = make_cpu()
    cpu.pc = 0x8002
    cpu.flags.set_zero_flag(False)

    bne(cpu, 0x05)

    assert cpu.pc == 0x8007


def test_bne_does_not_branch_when_zero_flag_is_set():
    """Objective: if Zero is set, PC remains unchanged."""
    cpu = make_cpu()
    cpu.pc = 0x8002
    cpu.flags.set_zero_flag(True)

    bne(cpu, 0x05)

    assert cpu.pc == 0x8002


def test_bne_wraps_pc_to_16_bits():
    """Objective: 0x0001 + (-2) wraps to 0xFFFF."""
    cpu = make_cpu()
    cpu.pc = 0x0001
    cpu.flags.set_zero_flag(False)

    bne(cpu, -2)

    assert cpu.pc == 0xFFFF
