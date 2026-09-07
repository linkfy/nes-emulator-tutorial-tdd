"""Step 171: implement Branch if Overflow Set behavior.

In this step, add ``emulator/cpu/instructions.py::bvs``:

    def bvs(cpu: CPU, offset: int):
        if cpu.flags.get_overflow_flag():
            cpu.pc = (cpu.pc + offset) & 0xFFFF

Why this step exists:
Step 163 already decodes the signed displacement, and PC is
already at the next instruction when ``bvs`` runs.  BVS therefore only tests
Overflow and conditionally adds that displacement, masking the result to the
CPU's 16-bit address space.

Invariants: Overflow set takes the branch; Overflow clear leaves PC unchanged.
No flag, other register, or memory is changed.  Misconception: BVS observes
Overflow; it neither sets Overflow nor fetches or sign-converts an operand.

Out of scope: importing ``bvs`` into ``emulator/cpu/opcodes.py``, creating its
relative opcode handler, and registering opcode ``0x70`` belong to step 179.
Steps 172-178 first wire the other branch opcodes.
"""

from emulator.cpu.instructions import bvs
from tests.helpers import make_cpu


def test_bvs_branches_when_overflow_flag_is_set():
    """Objective: if Overflow is set, PC is changed by the signed offset."""
    cpu = make_cpu()
    cpu.pc = 0x8002
    cpu.flags.set_overflow_flag(True)

    bvs(cpu, 0x05)

    assert cpu.pc == 0x8007


def test_bvs_does_not_branch_when_overflow_flag_is_clear():
    """Objective: if Overflow is clear, PC remains unchanged."""
    cpu = make_cpu()
    cpu.pc = 0x8002
    cpu.flags.set_overflow_flag(False)

    bvs(cpu, 0x05)

    assert cpu.pc == 0x8002
