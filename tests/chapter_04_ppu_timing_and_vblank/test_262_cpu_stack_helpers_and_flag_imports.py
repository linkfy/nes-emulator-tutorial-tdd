"""
Refactor CPU interrupt support around shared flags and stack helpers.

Files to update:
    emulator/cpu/cpu.py
    emulator/cpu/flags_handler.py

Why this step exists:
Before implementing and testing CPU.interrupt_nmi(), the CPU core needs two small
cleanup pieces:

    1. CPU should import status flag constants from flags_handler.py.
    2. CPU should expose stack helpers for interrupt code:
        push_stack(value)
        pop_stack() -> int

This is a refactor/helper step, not the NMI interrupt behavior test yet.

Important context:
Older CPU tests often declared local flag constants. That was fine while the CPU
chapter was being built incrementally. Now that interrupts need correct status
byte handling, the shared source of truth should be:

    emulator/cpu/flags_handler.py

Correct status bit layout:

    CARRY_FLAG      = 1 << 0
    ZERO_FLAG       = 1 << 1
    INTERRUPT_FLAG  = 1 << 2
    DECIMAL_FLAG    = 1 << 3
    B_FLAG          = 1 << 4
    ONE_FLAG        = 1 << 5
    OVERFLOW_FLAG   = 1 << 6
    NEGATIVE_FLAG   = 1 << 7

Stack rule:

    push:
        write to $0100 | S
        decrement S

    pop/pull:
        increment S
        read from $0100 | S

Suggested implementation example:

    from emulator.cpu.flags_handler import (
        B_FLAG,
        INTERRUPT_FLAG,
        NEGATIVE_FLAG,
        ONE_FLAG,
        ZERO_FLAG,
    )

    STACK_BASE = 0x0100

    class CPU:
        ...

        def push_stack(self, value: int) -> None:
            self.bus.write(STACK_BASE | self.s, value & 0xFF)
            self.s = (self.s - 1) & 0xFF

        def pop_stack(self) -> int:
            self.s = (self.s + 1) & 0xFF
            return self.bus.read(STACK_BASE | self.s)

Why pop_stack is added now:
CPU.interrupt_nmi() only needs push_stack, but the matching tests and future CPU
interrupt cleanup need a clear pull helper too. Adding both helpers together makes
the stack invariant explicit before NMI behavior is tested.

Out of scope:
    - CPU.interrupt_nmi() behavior
    - PPU NMI request consumption
    - IRQ/APU/mapper interrupts
    - refactoring every old stack instruction to use these helpers
"""

from emulator.cpu import cpu as cpu_module
from emulator.cpu.cpu import CPU
from emulator.cpu.flags_handler import (
    B_FLAG,
    CARRY_FLAG,
    DECIMAL_FLAG,
    INTERRUPT_FLAG,
    NEGATIVE_FLAG,
    ONE_FLAG,
    OVERFLOW_FLAG,
    ZERO_FLAG,
)
from tests.helpers import make_cpu


def test_cpu_uses_shared_status_flag_constants_from_flags_handler():
    """
    Objective:
    CPU interrupt code should use the corrected shared status flag constants from
    flags_handler.py, not stale local definitions.
    """
    assert CARRY_FLAG == 1 << 0
    assert ZERO_FLAG == 1 << 1
    assert INTERRUPT_FLAG == 1 << 2
    assert DECIMAL_FLAG == 1 << 3
    assert B_FLAG == 1 << 4
    assert ONE_FLAG == 1 << 5
    assert OVERFLOW_FLAG == 1 << 6
    assert NEGATIVE_FLAG == 1 << 7

    assert cpu_module.B_FLAG is B_FLAG
    assert cpu_module.ONE_FLAG is ONE_FLAG
    assert cpu_module.INTERRUPT_FLAG is INTERRUPT_FLAG


def test_cpu_declares_stack_base_constant():
    """
    Objective:
    Name the 6502 stack page used by CPU stack helpers.
    """
    assert cpu_module.STACK_BASE == 0x0100


def test_cpu_has_push_and_pop_stack_helpers():
    """
    Objective:
    CPU exposes shared stack helpers for interrupt code.
    """
    assert hasattr(CPU, "push_stack")
    assert callable(CPU.push_stack)
    assert hasattr(CPU, "pop_stack")
    assert callable(CPU.pop_stack)


def test_push_stack_writes_to_stack_page_and_decrements_stack_pointer():
    """
    Objective:
    push_stack writes to $0100 | S first, then decrements S.
    """
    cpu = make_cpu()
    cpu.s = 0xFD

    cpu.push_stack(0xAB)

    assert cpu.bus.read(0x01FD) == 0xAB
    assert cpu.s == 0xFC


def test_push_stack_masks_written_value_to_one_byte():
    """
    Objective:
    CPU stack stores bytes, so push_stack masks values to the low 8 bits.
    """
    cpu = make_cpu()
    cpu.s = 0xFD

    cpu.push_stack(0x1AB)

    assert cpu.bus.read(0x01FD) == 0xAB


def test_pop_stack_increments_stack_pointer_before_reading():
    """
    Objective:
    pop_stack follows 6502 pull behavior: increment S first, then read.
    """
    cpu = make_cpu()
    cpu.s = 0xFC
    cpu.bus.write(0x01FD, 0xCD)

    value = cpu.pop_stack()

    assert value == 0xCD
    assert cpu.s == 0xFD


def test_push_then_pop_stack_round_trips_value_and_restores_stack_pointer():
    """
    Objective:
    A value pushed to the stack should be read back by pop_stack, restoring S to
    its original value.
    """
    cpu = make_cpu()
    cpu.s = 0x80

    cpu.push_stack(0x42)
    value = cpu.pop_stack()

    assert value == 0x42
    assert cpu.s == 0x80


def test_stack_helpers_wrap_stack_pointer_to_8_bits():
    """
    Objective:
    S is an 8-bit stack pointer, so push/pop wrap around within page $0100.
    """
    cpu = make_cpu()
    cpu.s = 0x00

    cpu.push_stack(0x99)

    assert cpu.bus.read(0x0100) == 0x99
    assert cpu.s == 0xFF

    value = cpu.pop_stack()

    assert value == 0x99
    assert cpu.s == 0x00
