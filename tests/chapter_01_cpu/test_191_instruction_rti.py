"""Step 191: implement RTI behavior.

In this step, change only ``emulator/cpu/instructions.py`` by adding
``rti(cpu)``. Prerequisite: step 188 introduced the required interrupt and Break
flag APIs.

Why this step exists:
Interrupt entry leaves status, return-PC low, and return-PC high at
the next three stack slots. RTI must pull those bytes in that LIFO order and
restore the exact PC; unlike RTS, it must not add one.

Suggested implementation::

    cpu.s = (cpu.s + 1) & 0xFF
    flags = cpu.bus.read(0x0100 | cpu.s)
    cpu.p = flags & 0b1100_1111

    cpu.s = (cpu.s + 1) & 0xFF
    low = cpu.bus.read(0x0100 | cpu.s)

    cpu.s = (cpu.s + 1) & 0xFF
    high = cpu.bus.read(0x0100 | cpu.s)

    cpu.pc = (high << 8) | low

Place those statements in ``def rti(cpu: CPU)``.

Invariants: increment the 8-bit S before every read; read only stack page
$0100; replace P after masking bits 4 and 5; pull low before high; increase S
three times; leave the restored PC unincremented.

Misconception: RTI is not RTS for interrupts. Applying RTS's final ``+ 1``
returns to the wrong instruction.

Out of scope: opcode import/registration at $40 belongs to step 192. NMI
behavior belongs to later steps and must not be added here.
"""

from emulator.cpu.instructions import rti
from tests.helpers import make_cpu


CARRY_FLAG = 1 << 0
ZERO_FLAG = 1 << 1
INTERRUPT_DISABLE_FLAG = 1 << 2
BREAK_FLAG = 1 << 4
ONE_FLAG = 1 << 5
OVERFLOW_FLAG = 1 << 6
NEGATIVE_FLAG = 1 << 7
STACK_BASE = 0x0100


def test_rti_restores_program_counter_from_stack_without_adding_one():
    """
    Objective:
    RTI restores the exact PC from the stack.

    If the stack contains $1234, PC becomes $1234, not $1235.
    """
    cpu = make_cpu()
    cpu.s = 0xFA
    cpu.bus.write(STACK_BASE | 0xFB, 0x00)
    cpu.bus.write(STACK_BASE | 0xFC, 0x34)
    cpu.bus.write(STACK_BASE | 0xFD, 0x12)

    rti(cpu)

    assert cpu.pc == 0x1234


def test_rti_pulls_status_then_pc_low_then_pc_high():
    """
    Objective:
    RTI must pull stack bytes in interrupt-return order:

        status -> PC low -> PC high

    This is the reverse of what BRK/interrupt entry pushed.
    """
    cpu = make_cpu()
    cpu.s = 0xFA
    cpu.bus.write(STACK_BASE | 0xFB, CARRY_FLAG | NEGATIVE_FLAG)
    cpu.bus.write(STACK_BASE | 0xFC, 0xCD)
    cpu.bus.write(STACK_BASE | 0xFD, 0xAB)

    rti(cpu)

    assert cpu.p == (CARRY_FLAG | NEGATIVE_FLAG)
    assert cpu.pc == 0xABCD


def test_rti_increments_stack_pointer_three_times():
    """Objective: RTI pulls status, PC low, and PC high, so S increases by 3."""
    cpu = make_cpu()
    cpu.s = 0xFA
    cpu.bus.write(STACK_BASE | 0xFB, 0x00)
    cpu.bus.write(STACK_BASE | 0xFC, 0x34)
    cpu.bus.write(STACK_BASE | 0xFD, 0x12)

    rti(cpu)

    assert cpu.s == 0xFD


def test_rti_restores_status_flags_from_stack():
    """
    Objective:
    RTI restores saved processor status flags from the stack.

    These flags affect later branches and arithmetic, so RTI must not leave the
    interrupt handler's temporary flags behind.
    """
    cpu = make_cpu()
    cpu.s = 0xFA
    saved_flags = CARRY_FLAG | ZERO_FLAG | INTERRUPT_DISABLE_FLAG | OVERFLOW_FLAG | NEGATIVE_FLAG
    cpu.bus.write(STACK_BASE | 0xFB, saved_flags)
    cpu.bus.write(STACK_BASE | 0xFC, 0x34)
    cpu.bus.write(STACK_BASE | 0xFD, 0x12)

    rti(cpu)

    assert cpu.p == saved_flags


def test_rti_clears_break_and_unused_status_bits_from_pulled_status():
    """
    Objective:
    In this emulator model, status bits 4 and 5 are not kept as persistent CPU
    state after RTI.

    Why:
    BRK may push a status byte with Break set, but Break is metadata in the
    saved stack byte, not a normal long-lived CPU flag here.
    """
    cpu = make_cpu()
    cpu.s = 0xFA
    saved_flags_with_break_and_unused = 0b0011_0000 | CARRY_FLAG | NEGATIVE_FLAG
    cpu.bus.write(STACK_BASE | 0xFB, saved_flags_with_break_and_unused)
    cpu.bus.write(STACK_BASE | 0xFC, 0x34)
    cpu.bus.write(STACK_BASE | 0xFD, 0x12)

    rti(cpu)

    assert (cpu.p & BREAK_FLAG) == 0
    assert (cpu.p & ONE_FLAG) == 0
    assert cpu.p == (CARRY_FLAG | NEGATIVE_FLAG)


def test_rti_stack_pointer_wraps_to_8_bits():
    """Objective: S is an 8-bit stack pointer and wraps while pulling bytes."""
    cpu = make_cpu()
    cpu.s = 0xFE
    cpu.bus.write(STACK_BASE | 0xFF, CARRY_FLAG)
    cpu.bus.write(STACK_BASE | 0x00, 0x78)
    cpu.bus.write(STACK_BASE | 0x01, 0x56)

    rti(cpu)

    assert cpu.p == CARRY_FLAG
    assert cpu.pc == 0x5678
    assert cpu.s == 0x01
