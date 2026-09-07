"""Lesson 170: implement Branch if Overflow Clear behavior.

Why this step exists:
BVC observes the existing signed-arithmetic Overflow condition and branches
when that flag is clear without modifying it.

In this step, after BMI, add exactly:

``emulator/cpu/instructions.py::bvc``::

    def bvc(cpu: CPU, offset: int):
        if not cpu.flags.get_overflow_flag():
            cpu.pc = (cpu.pc + offset) & 0xFFFF

If clear, it adds the signed relative displacement to the post-operand PC and
masks the target into the 16-bit address space.

Invariants: Overflow clear takes the branch; Overflow set leaves PC unchanged.
The instruction changes no flags, other registers, or memory.  Misconception:
BVC neither clears Overflow nor decides from Carry or the offset's sign.

Out of scope: complementary BVS is lesson 171.  Branch imports, relative
opcode handlers, and table entries are lessons 172-179.
"""

from emulator.cpu.instructions import bvc
from tests.helpers import make_cpu


def test_bvc_branches_when_overflow_flag_is_clear():
    """Objective: if Overflow is clear, PC is changed by the signed offset."""
    cpu = make_cpu()
    cpu.pc = 0x8002
    cpu.flags.set_overflow_flag(False)

    bvc(cpu, 0x05)

    assert cpu.pc == 0x8007


def test_bvc_does_not_branch_when_overflow_flag_is_set():
    """Objective: if Overflow is set, PC remains unchanged."""
    cpu = make_cpu()
    cpu.pc = 0x8002
    cpu.flags.set_overflow_flag(True)

    bvc(cpu, 0x05)

    assert cpu.pc == 0x8002
