"""
Test 052 - Introduce a public helper for processor-status flag access.

Files to create/update:
    emulator/cpu/flags_handler.py
    emulator/cpu/cpu.py

Symbols to create/update:
    FlagsHandler
    CPU.flags
    CPU.__post_init__

Why this step exists:
The existing CPU helper covers only Zero and Negative. The next arithmetic
instruction also needs Carry and Overflow, so status-bit access is collected in
an object that mutates the CPU-owned `p` register. The existing
`CPU._update_zero_and_negative_flags` stays intact for earlier instructions.

Complete example implementation:

    # emulator/cpu/flags_handler.py
    from __future__ import annotations
    from dataclasses import dataclass
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from emulator.cpu.cpu import CPU

    CARRY_FLAG = 1 << 0
    ZERO_FLAG = 1 << 1
    OVERFLOW_FLAG = 1 << 6
    NEGATIVE_FLAG = 1 << 7

    @dataclass
    class FlagsHandler:
        cpu: CPU

        def set_zero_flag(self, enabled: bool):
            if enabled:
                self.cpu.p |= ZERO_FLAG
            else:
                self.cpu.p &= ~ZERO_FLAG

        def set_negative_flag(self, enabled: bool):
            if enabled:
                self.cpu.p |= NEGATIVE_FLAG
            else:
                self.cpu.p &= ~NEGATIVE_FLAG

        def set_overflow_flag(self, enabled: bool):
            if enabled:
                self.cpu.p |= OVERFLOW_FLAG
            else:
                self.cpu.p &= ~OVERFLOW_FLAG

        def set_carry_flag(self, enabled: bool):
            if enabled:
                self.cpu.p |= CARRY_FLAG
            else:
                self.cpu.p &= ~CARRY_FLAG

        def get_zero_flag(self) -> bool:
            return bool(self.cpu.p & ZERO_FLAG)

        def get_negative_flag(self) -> bool:
            return bool(self.cpu.p & NEGATIVE_FLAG)

        def get_overflow_flag(self) -> bool:
            return bool(self.cpu.p & OVERFLOW_FLAG)

        def get_carry_flag(self) -> bool:
            return bool(self.cpu.p & CARRY_FLAG)

    # emulator/cpu/cpu.py
    from dataclasses import dataclass, field
    from emulator.cpu.flags_handler import FlagsHandler

    @dataclass
    class CPU:
        bus: CpuBus
        flags: FlagsHandler = field(init=False)

        def __post_init__(self):
            self.flags = FlagsHandler(self)

        # Keep the existing registers, fetch/reset/step methods, and
        # _update_zero_and_negative_flags implementation unchanged.

Important invariants:
    - `cpu.p` remains the single processor-status value
    - every setter changes only its own bit and supports both set and clear
    - every getter returns a bool
    - each CPU owns a handler whose `cpu` reference points back to that CPU
    - the old Zero/Negative CPU helper remains callable

Common misconception:
Do not give FlagsHandler a separate status byte or replace the old CPU helper;
that would split state or break the instructions introduced in earlier tests.

Out of scope:
    - ADC, which first consumes these public helpers in test 053
    - Break, interrupt-disable, decimal, and bit-5 helpers
    - stack and interrupt behavior
"""
import inspect
from pathlib import Path

from emulator.bus.cpu_bus import CpuBus
from emulator.cpu.cpu import CPU
from emulator.cpu.flags_handler import FlagsHandler


CARRY_FLAG = 1 << 0
ZERO_FLAG = 1 << 1
ONE_FLAG = 1 << 5
OVERFLOW_FLAG = 1 << 6
NEGATIVE_FLAG = 1 << 7


def make_cpu():
    return CPU(CpuBus())


def test_flags_handler_file_exists():
    """
    Objective:
    Create this file:

        emulator/cpu/flags_handler.py

    Why:
    CPU already has many responsibilities.
    A small FlagsHandler object can group flag-specific helpers in one place.

    Tradeoff:
    This adds one more object, but it reduces repeated flag bit operations
    across future instructions like ADC, SBC, CMP, ASL, LSR, and branches.
    """
    assert Path("emulator/cpu/flags_handler.py").exists()


def test_flags_handler_class_exists():
    """
    Objective:
    Create in flags_handler.py:

        class FlagsHandler:
            ...

    What it needs:
    - Store a reference to the CPU.
    - Read and write cpu.p, because cpu.p is the processor status register.

    Why not store a separate p value here?
    CPU must keep owning the real processor status register.
    FlagsHandler only helps modify that register.

    Example:
        @dataclass
        class FlagsHandler:
            cpu: CPU
    """
    assert inspect.isclass(FlagsHandler)


def test_flags_handler_can_be_created_with_cpu():
    """
    Objective:
    FlagsHandler must receive a CPU instance.

    Example:
        cpu = CPU(CpuBus())
        flags = FlagsHandler(cpu)

    Why:
    The handler modifies cpu.p, not its own local status register.

    Design rule:
    CPU owns the state.
    FlagsHandler owns the bit manipulation helpers.
    """
    cpu = make_cpu()
    flags = FlagsHandler(cpu)

    assert flags.cpu is cpu


def test_flags_handler_set_methods_exist():
    """
    Objective:
    Define setter methods for the common CPU flags:

        def set_zero_flag(self, enabled: bool):
            ...

        def set_negative_flag(self, enabled: bool):
            ...

        def set_overflow_flag(self, enabled: bool):
            ...

        def set_carry_flag(self, enabled: bool):
            ...

    Important:
    enabled=True means set the flag.
    enabled=False means clear the flag.

    Why boolean setters?
    Carry and Overflow are not always based on one bit of the result.
    Future instructions will decide the condition and then call the setter.

    Example:
        cpu.flags.set_carry_flag(result > 0xFF)
    """
    assert hasattr(FlagsHandler, "set_zero_flag")
    assert hasattr(FlagsHandler, "set_negative_flag")
    assert hasattr(FlagsHandler, "set_overflow_flag")
    assert hasattr(FlagsHandler, "set_carry_flag")
    # Required by Test 188; outside lesson 052's API.
    assert hasattr(FlagsHandler, "set_one_flag")


def test_flags_handler_get_methods_exist():
    """
    Objective:
    Define getter methods for the common CPU flags:

        def get_zero_flag(self) -> bool:
            ...

        def get_negative_flag(self) -> bool:
            ...

        def get_overflow_flag(self) -> bool:
            ...

        def get_carry_flag(self) -> bool:
            ...

    Example implementation:
        return bool(self.cpu.p & ZERO_FLAG)

    Why:
    Later branch instructions can ask if a flag is active.

    Example:
        if cpu.flags.get_zero_flag():
            ...
    """
    assert hasattr(FlagsHandler, "get_zero_flag")
    assert hasattr(FlagsHandler, "get_negative_flag")
    assert hasattr(FlagsHandler, "get_overflow_flag")
    assert hasattr(FlagsHandler, "get_carry_flag")
    # Required by Test 188; outside lesson 052's API.
    assert hasattr(FlagsHandler, "get_one_flag")


def test_flags_handler_sets_and_clears_zero_flag():
    """Objective: set_zero_flag(True) sets Z, and False clears Z."""
    cpu = make_cpu()
    flags = FlagsHandler(cpu)

    flags.set_zero_flag(True)
    assert (cpu.p & ZERO_FLAG) != 0
    assert flags.get_zero_flag() is True

    flags.set_zero_flag(False)
    assert (cpu.p & ZERO_FLAG) == 0
    assert flags.get_zero_flag() is False


def test_flags_handler_sets_and_clears_negative_flag():
    """Objective: set_negative_flag(True) sets N, and False clears N."""
    cpu = make_cpu()
    flags = FlagsHandler(cpu)

    flags.set_negative_flag(True)
    assert (cpu.p & NEGATIVE_FLAG) != 0
    assert flags.get_negative_flag() is True

    flags.set_negative_flag(False)
    assert (cpu.p & NEGATIVE_FLAG) == 0
    assert flags.get_negative_flag() is False


def test_flags_handler_sets_and_clears_overflow_flag():
    """Objective: set_overflow_flag(True) sets V, and False clears V."""
    cpu = make_cpu()
    flags = FlagsHandler(cpu)

    flags.set_overflow_flag(True)
    assert (cpu.p & OVERFLOW_FLAG) != 0
    assert flags.get_overflow_flag() is True

    flags.set_overflow_flag(False)
    assert (cpu.p & OVERFLOW_FLAG) == 0
    assert flags.get_overflow_flag() is False


def test_flags_handler_sets_and_clears_carry_flag():
    """Objective: set_carry_flag(True) sets C, and False clears C."""
    cpu = make_cpu()
    flags = FlagsHandler(cpu)

    flags.set_carry_flag(True)
    assert (cpu.p & CARRY_FLAG) != 0
    assert flags.get_carry_flag() is True

    flags.set_carry_flag(False)
    assert (cpu.p & CARRY_FLAG) == 0
    assert flags.get_carry_flag() is False


def test_flags_handler_sets_and_clears_one_flag():
    """
    Test 188 compatibility check, outside the scope of Test 052.

    This verifies that the bit-5 helper required by Test 188 can set and clear
    only that bit. In this step, the suggested implementation intentionally
    stops at C, Z, V, and N.
    """
    cpu = make_cpu()
    flags = FlagsHandler(cpu)

    flags.set_one_flag(True)
    assert (cpu.p & ONE_FLAG) != 0
    assert flags.get_one_flag() is True

    flags.set_one_flag(False)
    assert (cpu.p & ONE_FLAG) == 0
    assert flags.get_one_flag() is False


def test_cpu_has_flags_handler_instance():
    """
    Objective:
    Add a CPU attribute called flags.

    Example in cpu.py:
        flags: FlagsHandler = field(init=False)

        def __post_init__(self):
            self.flags = FlagsHandler(self)

    Why:
    FlagsHandler needs the CPU instance, so it cannot be created with
    default_factory=FlagsHandler.

    Tradeoff:
    This creates a small circular relationship:
        CPU -> flags
        flags -> CPU

    This is acceptable here because FlagsHandler is not an independent CPU.
    It is a helper object that operates on the CPU status register.
    """
    cpu = make_cpu()

    assert hasattr(cpu, "flags")
    assert isinstance(cpu.flags, FlagsHandler)
    assert cpu.flags.cpu is cpu


def test_cpu_keeps_old_zero_and_negative_update_method_for_compatibility():
    """
    Objective:
    Keep the old CPU method for previous tests:

        _update_zero_and_negative_flags(self, value)

    Why:
    This refactor adds FlagsHandler, but does not need to break old tests.

    Tradeoff:
    For now, old instructions can keep calling:
        cpu._update_zero_and_negative_flags(value)

    In this step, leave that method unchanged. Delegating it to FlagsHandler is
    not required by this lesson.
    """
    cpu = make_cpu()

    assert hasattr(cpu, "_update_zero_and_negative_flags")
    assert callable(cpu._update_zero_and_negative_flags)
