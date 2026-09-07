"""Lesson 168: implement Branch if Plus behavior.

Why this step exists:
In 6502 terminology, "plus" means the existing Negative flag is clear, so BPL
selects on that flag rather than inspecting the offset or PC.

In this step, after BNE, add exactly:

``emulator/cpu/instructions.py::bpl``::

    def bpl(cpu: CPU, offset: int):
        if not cpu.flags.get_negative_flag():
            cpu.pc = (cpu.pc + offset) & 0xFFFF

The function applies the decoded signed offset to the post-operand PC
and masks the result to the 16-bit address space.

Invariants: Negative clear takes the branch; Negative set leaves PC unchanged.
No flags, other registers, or memory change.  Misconception: BPL does not test
whether PC or ``offset`` is positive and does not recompute Negative.

Out of scope: BMI/BVC/BVS are lessons 169-171.  Opcode imports, relative
handlers, and table entries are lessons 172-179.
"""

from emulator.cpu.instructions import bpl
from tests.helpers import make_cpu


def test_bpl_branches_when_negative_flag_is_clear():
    """Objective: if Negative is clear, PC is changed by the signed offset."""
    cpu = make_cpu()
    cpu.pc = 0x8002
    cpu.flags.set_negative_flag(False)

    bpl(cpu, 0x05)

    assert cpu.pc == 0x8007


def test_bpl_does_not_branch_when_negative_flag_is_set():
    """Objective: if Negative is set, PC remains unchanged."""
    cpu = make_cpu()
    cpu.pc = 0x8002
    cpu.flags.set_negative_flag(True)

    bpl(cpu, 0x05)

    assert cpu.pc == 0x8002
