"""Step 208: implement the NOP operation.

Why this step exists:
In this step, add ``emulator/cpu/instructions.py::nop``. The explicit no-op
gives the official instruction a callable while leaving opcode-fetch concerns
to CPU.step.

Suggested implementation::

    def nop(cpu: CPU):
        pass

Invariant: a direct call changes no register, P bit, S, PC, or memory.  The
common misconception is to increment PC inside ``nop``; dispatch has already
fetched the opcode, and the operation itself owns no bytes.

Out of scope: importing NOP and mapping official opcode $EA in
``emulator/cpu/opcodes.py::OPCODE_TABLE`` belongs to step 209.  Unofficial NOP
variants, timing changes, and later tracing facilities are not introduced.
"""

from emulator.cpu.instructions import nop
from tests.helpers import make_cpu


def test_nop_does_not_modify_registers():
    """Objective: NOP does not modify A, X, or Y."""
    cpu = make_cpu()
    cpu.a = 0x11
    cpu.x = 0x22
    cpu.y = 0x33

    nop(cpu)

    assert cpu.a == 0x11
    assert cpu.x == 0x22
    assert cpu.y == 0x33


def test_nop_does_not_modify_stack_pointer():
    """Objective: NOP does not touch S."""
    cpu = make_cpu()
    cpu.s = 0xFD

    nop(cpu)

    assert cpu.s == 0xFD


def test_nop_does_not_modify_program_counter_when_called_directly():
    """
    Objective:
    nop(cpu) itself does not change PC.

    CPU.step() changes PC when it fetches the opcode. The instruction function
    should not add another increment.
    """
    cpu = make_cpu()
    cpu.pc = 0x8001

    nop(cpu)

    assert cpu.pc == 0x8001


def test_nop_does_not_modify_status_flags():
    """Objective: NOP preserves the processor status register P."""
    cpu = make_cpu()
    cpu.p = 0b1100_1111

    nop(cpu)

    assert cpu.p == 0b1100_1111


def test_nop_does_not_modify_memory():
    """Objective: NOP does not read/write data memory as part of instruction logic."""
    cpu = make_cpu()
    cpu.bus.write(0x0002, 0x42)

    nop(cpu)

    assert cpu.bus.read(0x0002) == 0x42
