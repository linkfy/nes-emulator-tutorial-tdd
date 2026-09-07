"""Step 184: add addressing-independent JSR behavior.

In this step, add ``emulator/cpu/instructions.py::jsr``:

Instruction:
    JSR -> Jump to Subroutine

Goal:
implement jsr(cpu, addr) in instructions.py.

Student guidance:
JSR is like JMP, but it also saves a return address on the stack so RTS can
return later.

Important details:
    - The stack lives in page $0100.
    - S is only the low byte of the stack address.
    - Push high byte first, then low byte.
    - Decrement S after each push.
    - At jsr(cpu, addr) time, PC already points to the next instruction.
    - JSR pushes PC - 1 because RTS increments the pulled return address.

Example implementation shape:

    return_addr = (cpu.pc - 1) & 0xFFFF
    high = (return_addr >> 8) & 0xFF
    low = return_addr & 0xFF

    cpu.bus.write(0x0100 | cpu.s, high)
    cpu.s = (cpu.s - 1) & 0xFF

    cpu.bus.write(0x0100 | cpu.s, low)
    cpu.s = (cpu.s - 1) & 0xFF

    cpu.pc = addr & 0xFFFF

Why this step exists:
Operand decoding has already advanced PC past JSR, while the 6502
stack protocol stores one less than the continuation address for a future RTS.
Invariants: writes occur high then low at ``$0100 | S``; S decrements and wraps
after each write; PC and the supplied address are 16-bit; flags and other
registers are preserved.  Misconception: pushing the current PC, or pushing low
first, produces an incompatible return frame.

Out of scope: no opcode import, ``jsr_absolute`` handler, or $20 table entry
until step 185.  ``rts`` does not exist until step 186; it explains the
PC-minus-one convention but must not be implemented here.
"""

from emulator.cpu.instructions import jsr
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG, make_cpu


CARRY_FLAG = 1 << 0
OVERFLOW_FLAG = 1 << 6
STACK_BASE = 0x0100


def test_jsr_sets_program_counter_to_subroutine_address():
    """Objective: JSR jumps to the subroutine target address."""
    cpu = make_cpu()
    cpu.pc = 0x8003
    cpu.s = 0xFD

    jsr(cpu, 0x1234)

    assert cpu.pc == 0x1234


def test_jsr_pushes_return_address_high_then_low_to_stack():
    """
    Objective:
    If PC is 0x8003 when jsr(cpu, addr) runs, return address is 0x8002.

    JSR pushes:
        high byte = 0x80 to $01FD
        low byte  = 0x02 to $01FC
    """
    cpu = make_cpu()
    cpu.pc = 0x8003
    cpu.s = 0xFD

    jsr(cpu, 0x1234)

    assert cpu.bus.read(STACK_BASE | 0xFD) == 0x80
    assert cpu.bus.read(STACK_BASE | 0xFC) == 0x02


def test_jsr_decrements_stack_pointer_twice():
    """Objective: JSR pushes two bytes, so S decreases by 2."""
    cpu = make_cpu()
    cpu.pc = 0x8003
    cpu.s = 0xFD

    jsr(cpu, 0x1234)

    assert cpu.s == 0xFB


def test_jsr_stack_pointer_wraps_to_8_bits():
    """Objective: S is an 8-bit stack pointer and wraps after decrementing."""
    cpu = make_cpu()
    cpu.pc = 0x8003
    cpu.s = 0x00

    jsr(cpu, 0x1234)

    assert cpu.bus.read(STACK_BASE | 0x00) == 0x80
    assert cpu.bus.read(STACK_BASE | 0xFF) == 0x02
    assert cpu.s == 0xFE


def test_jsr_does_not_modify_status_flags():
    """Objective: JSR changes PC and stack only; status flags are preserved."""
    cpu = make_cpu()
    cpu.pc = 0x8003
    cpu.s = 0xFD
    cpu.p |= CARRY_FLAG
    cpu.p |= ZERO_FLAG
    cpu.p |= OVERFLOW_FLAG
    cpu.p |= NEGATIVE_FLAG

    jsr(cpu, 0x1234)

    assert (cpu.p & CARRY_FLAG) != 0
    assert (cpu.p & ZERO_FLAG) != 0
    assert (cpu.p & OVERFLOW_FLAG) != 0
    assert (cpu.p & NEGATIVE_FLAG) != 0
