"""Lesson 169: implement Branch if Minus behavior.

Why this step exists:
"Minus" means the Negative flag from an earlier result is set, so BMI consumes
that status without recomputing it.

In this step, add only this implementation:

``emulator/cpu/instructions.py::bmi``::

    def bmi(cpu: CPU, offset: int):
        if cpu.flags.get_negative_flag():
            cpu.pc = (cpu.pc + offset) & 0xFFFF

BMI applies the already decoded signed displacement to the PC after its
operand, masking the target to 16 bits.

Invariants: Negative set takes the branch and Negative clear leaves PC alone;
flags, other registers, and memory are unchanged.  Misconception: BMI does not
inspect the sign of ``offset`` or perform arithmetic to establish Negative.

Out of scope: BVC/BVS are lessons 170-171.  Imports into
``emulator/cpu/opcodes.py``, relative handlers, and opcode table entries belong
to lessons 172-179.
"""

from emulator.cpu.instructions import bmi
from tests.helpers import make_cpu


def test_bmi_branches_when_negative_flag_is_set():
    """Objective: if Negative is set, PC is changed by the signed offset."""
    cpu = make_cpu()
    cpu.pc = 0x8002
    cpu.flags.set_negative_flag(True)

    bmi(cpu, 0x05)

    assert cpu.pc == 0x8007


def test_bmi_does_not_branch_when_negative_flag_is_clear():
    """Objective: if Negative is clear, PC remains unchanged."""
    cpu = make_cpu()
    cpu.pc = 0x8002
    cpu.flags.set_negative_flag(False)

    bmi(cpu, 0x05)

    assert cpu.pc == 0x8002
