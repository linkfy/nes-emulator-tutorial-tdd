"""Step 186: add addressing-independent RTS behavior.

Prerequisite: steps 184-185 added JSR behavior and opcode wiring. In this step,
add ``emulator/cpu/instructions.py::rts``:

Instruction:
    RTS -> Return from Subroutine

Goal:
implement rts(cpu) in instructions.py.

Student guidance:
RTS is the matching return instruction for JSR. JSR saves a return address on
the stack, and RTS pulls that address back, then adds 1 to continue execution
after the original JSR instruction.

Important details:
    - The stack lives in page $0100.
    - S is only the low byte of the stack address.
    - Pull increments S first, then reads from $0100 | S.
    - RTS pulls low byte first, then high byte.
    - RTS sets PC to pulled_address + 1.

Example:
    If the stack contains return address $8002:

        $01FC = $02  low byte
        $01FD = $80  high byte
        S = $FB

    Then RTS pulls $8002 and sets PC to $8003.

Example implementation shape:

    cpu.s = (cpu.s + 1) & 0xFF
    low = cpu.bus.read(0x0100 | cpu.s)

    cpu.s = (cpu.s + 1) & 0xFF
    high = cpu.bus.read(0x0100 | cpu.s)

    addr = (high << 8) | low
    cpu.pc = (addr + 1) & 0xFFFF

Why this step exists:
JSR stored PC-minus-one, so RTS reconstructs that word and advances
once to the continuation.  Invariants: each pull increments 8-bit S before its
read; low is pulled before high; final PC wraps to 16 bits; status, other
registers, and memory are unchanged.  Misconception: reading before incrementing
S, or omitting the final PC increment, does not invert JSR's stack protocol.

Out of scope: importing/mapping opcode $60 is step 187.  BRK/RTI and shared
CPU stack helpers belong to later steps.
"""

from emulator.cpu.instructions import rts
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG, make_cpu


CARRY_FLAG = 1 << 0
OVERFLOW_FLAG = 1 << 6
STACK_BASE = 0x0100


def test_rts_sets_program_counter_to_pulled_return_address_plus_one():
    """Objective: RTS pulls the saved return address and continues at address + 1."""
    cpu = make_cpu()
    cpu.s = 0xFB
    cpu.bus.write(STACK_BASE | 0xFC, 0x02)
    cpu.bus.write(STACK_BASE | 0xFD, 0x80)

    rts(cpu)

    assert cpu.pc == 0x8003


def test_rts_pulls_low_byte_then_high_byte_from_stack():
    """
    Objective:
    RTS pulls low byte first, then high byte.

    With S = $FB:
        first pull reads from $01FC -> low byte $34
        second pull reads from $01FD -> high byte $12

    Pulled address is $1234, so PC becomes $1235.
    """
    cpu = make_cpu()
    cpu.s = 0xFB
    cpu.bus.write(STACK_BASE | 0xFC, 0x34)
    cpu.bus.write(STACK_BASE | 0xFD, 0x12)

    rts(cpu)

    assert cpu.pc == 0x1235


def test_rts_increments_stack_pointer_twice():
    """Objective: RTS pulls two bytes, so S increases by 2."""
    cpu = make_cpu()
    cpu.s = 0xFB
    cpu.bus.write(STACK_BASE | 0xFC, 0x02)
    cpu.bus.write(STACK_BASE | 0xFD, 0x80)

    rts(cpu)

    assert cpu.s == 0xFD


def test_rts_stack_pointer_wraps_to_8_bits():
    """Objective: S is an 8-bit stack pointer and wraps after incrementing."""
    cpu = make_cpu()
    cpu.s = 0xFE
    cpu.bus.write(STACK_BASE | 0xFF, 0xFE)
    cpu.bus.write(STACK_BASE | 0x00, 0xCA)

    rts(cpu)

    assert cpu.pc == 0xCAFF
    assert cpu.s == 0x00


def test_rts_program_counter_wraps_to_16_bits():
    """Objective: PC is 16-bit, so returning from $FFFF wraps to $0000."""
    cpu = make_cpu()
    cpu.s = 0xFB
    cpu.bus.write(STACK_BASE | 0xFC, 0xFF)
    cpu.bus.write(STACK_BASE | 0xFD, 0xFF)

    rts(cpu)

    assert cpu.pc == 0x0000


def test_rts_does_not_modify_status_flags():
    """Objective: RTS changes PC and stack only; status flags are preserved."""
    cpu = make_cpu()
    cpu.s = 0xFB
    cpu.bus.write(STACK_BASE | 0xFC, 0x02)
    cpu.bus.write(STACK_BASE | 0xFD, 0x80)
    cpu.p |= CARRY_FLAG
    cpu.p |= ZERO_FLAG
    cpu.p |= OVERFLOW_FLAG
    cpu.p |= NEGATIVE_FLAG

    rts(cpu)

    assert (cpu.p & CARRY_FLAG) != 0
    assert (cpu.p & ZERO_FLAG) != 0
    assert (cpu.p & OVERFLOW_FLAG) != 0
    assert (cpu.p & NEGATIVE_FLAG) != 0
