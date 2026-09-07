"""Step 201: implement the TXS operation.

Why this step exists:
In this step, add ``emulator/cpu/instructions.py::txs``. This operation is
introduced now because stack transfers are the remaining stack-instruction
behavior: X is copied into the stack-pointer byte without a memory access.

Suggested implementation::

    def txs(cpu: CPU):
        cpu.s = cpu.x

Invariants: X, P, PC, A, Y, and memory are unchanged; S remains the low-byte
offset into the already-established $0100-$01FF stack page.  A common
misconception is to update Zero and Negative as other register transfers do;
TXS changes no flags, including when X is $00 or has bit 7 set.

Out of scope: registering implied opcode $9A in
``emulator/cpu/opcodes.py::OPCODE_TABLE`` belongs to step 202; TSX and its
opcode belong to steps 203-204.  Do not add those later APIs here.
"""

from emulator.cpu.instructions import txs
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG, make_cpu


CARRY_FLAG = 1 << 0
OVERFLOW_FLAG = 1 << 6


def test_txs_copies_x_to_stack_pointer():
    """Objective: TXS sets S to the current value of X."""
    cpu = make_cpu()
    cpu.x = 0x80
    cpu.s = 0xFD

    txs(cpu)

    assert cpu.s == 0x80


def test_txs_does_not_modify_x():
    """Objective: TXS copies X but leaves X unchanged."""
    cpu = make_cpu()
    cpu.x = 0x42
    cpu.s = 0xFD

    txs(cpu)

    assert cpu.x == 0x42


def test_txs_can_set_stack_pointer_to_zero_without_setting_zero_flag():
    """
    Objective:
    TXS does not update Zero, even if X is $00.
    """
    cpu = make_cpu()
    cpu.x = 0x00
    cpu.s = 0xFD
    cpu.flags.set_zero_flag(False)

    txs(cpu)

    assert cpu.s == 0x00
    assert cpu.flags.get_zero_flag() is False


def test_txs_can_set_stack_pointer_to_negative_value_without_setting_negative_flag():
    """
    Objective:
    TXS does not update Negative, even if bit 7 of X is set.
    """
    cpu = make_cpu()
    cpu.x = 0x80
    cpu.s = 0xFD
    cpu.flags.set_negative_flag(False)

    txs(cpu)

    assert cpu.s == 0x80
    assert cpu.flags.get_negative_flag() is False


def test_txs_preserves_all_status_flags():
    """Objective: TXS is a register transfer to S and does not change flags."""
    cpu = make_cpu()
    cpu.x = 0x12
    cpu.s = 0xFD
    cpu.p = CARRY_FLAG | ZERO_FLAG | OVERFLOW_FLAG | NEGATIVE_FLAG

    txs(cpu)

    assert cpu.p == (CARRY_FLAG | ZERO_FLAG | OVERFLOW_FLAG | NEGATIVE_FLAG)
