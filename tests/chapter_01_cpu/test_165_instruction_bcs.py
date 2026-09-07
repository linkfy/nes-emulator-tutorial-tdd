"""Lesson 165: implement Branch if Carry Set behavior.

Why this step exists:
The addressing layer has already consumed and signed the operand, so BCS only
selects on Carry and applies the displacement to the next-instruction PC.

In this step, after BCC in lesson 164, add exactly:

``emulator/cpu/instructions.py::bcs``::

    def bcs(cpu: CPU, offset: int):
        if cpu.flags.get_carry_flag():
            cpu.pc = (cpu.pc + offset) & 0xFFFF

Masking makes both overflow and underflow wrap to 16 bits.

Invariants: Carry set takes the branch; Carry clear leaves PC unchanged.  No
status flag, other register, or memory changes.  Misconception: BCS does not
set Carry and does not branch when Carry is clear; it merely reads that flag.

Out of scope: subsequent branch instruction functions are lessons 166-171;
all branch opcode imports, handlers, and table entries are lessons 172-179.
"""

from emulator.cpu.instructions import bcs
from tests.helpers import make_cpu


def test_bcs_branches_when_carry_flag_is_set():
    """Objective: if Carry is set, PC is changed by the signed offset."""
    cpu = make_cpu()
    cpu.pc = 0x8002
    cpu.flags.set_carry_flag(True)

    bcs(cpu, 0x05)

    assert cpu.pc == 0x8007


def test_bcs_does_not_branch_when_carry_flag_is_clear():
    """Objective: if Carry is clear, PC remains unchanged."""
    cpu = make_cpu()
    cpu.pc = 0x8002
    cpu.flags.set_carry_flag(False)

    bcs(cpu, 0x05)

    assert cpu.pc == 0x8002


def test_bcs_wraps_pc_to_16_bits():
    """Objective: 0xFFFF + 1 wraps to 0x0000."""
    cpu = make_cpu()
    cpu.pc = 0xFFFF
    cpu.flags.set_carry_flag(True)

    bcs(cpu, 1)

    assert cpu.pc == 0x0000
