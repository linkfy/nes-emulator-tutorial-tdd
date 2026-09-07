"""Step 211: add `emulator/debug/cpu_trace.py::format_cpu_trace`.

Why this step exists:
In this step, add a formatter that provides observability before ROM-log
comparison without coupling debugging to CPU execution. Its line reports the
next PC/opcode and the A, X, Y, P, and S register values before execution:

    8000 A9 A:00 X:00 Y:00 P:04 S:FD

Suggested implementation:

    from __future__ import annotations
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from emulator.cpu.cpu import CPU


    def format_cpu_trace(cpu: CPU):
        opcode = cpu.bus.read(cpu.pc)
        return f"{cpu.pc:04X} {opcode:02X} A:{cpu.a:02X} X:{cpu.x:02X} Y:{cpu.y:02X} P:{cpu.p:02X} S:{cpu.s:02X}"

Invariants: formatting performs one non-advancing bus read, returns uppercase
fixed-width hexadecimal fields, and leaves PC, registers, and flags unchanged.
Do not use `CPU.fetch_byte()` or call `CPU.step()`; both confuse observation with
execution, and `fetch_byte()` advances PC. Out of scope: ROM and cartridge
support belong to later numbered steps.
"""

import inspect
from pathlib import Path

from emulator.debug.cpu_trace import format_cpu_trace
from tests.helpers import load_program, make_cpu_with_rom, write_reset_vector


def test_cpu_trace_file_exists_inside_emulator_debug():
    """
    Objective:
    Create the trace formatter in emulator/debug/cpu_trace.py.

    Why here:
    Debug tracing is observability, not CPU execution logic. Keeping it outside
    cpu.py prevents tracing concerns from coupling to instruction behavior.
    """
    assert Path("emulator/debug/cpu_trace.py").exists()


def test_format_cpu_trace_function_exists_and_takes_cpu():
    """Objective: expose format_cpu_trace(cpu) as a small read-only formatter."""
    assert callable(format_cpu_trace)
    assert list(inspect.signature(format_cpu_trace).parameters) == ["cpu"]


def test_format_cpu_trace_outputs_minimal_cpu_state_before_execution():
    """
    Objective:
    Trace should show the opcode at current PC and CPU registers before step().
    """
    cpu, bus, rom = make_cpu_with_rom()
    write_reset_vector(rom, 0x8000)
    load_program(rom, 0x8000, [0xA9, 0x42])

    cpu.reset()
    cpu.a = 0x00
    cpu.x = 0x11
    cpu.y = 0x22
    cpu.p = 0x04
    cpu.s = 0xFD

    trace = format_cpu_trace(cpu)

    assert trace == "8000 A9 A:00 X:11 Y:22 P:04 S:FD"


def test_format_cpu_trace_is_read_only():
    """
    Objective:
    Formatting a trace must not mutate CPU state.

    Failure mode this catches:
    Calling cpu.fetch_byte() inside the trace formatter would increment PC.
    """
    cpu, bus, rom = make_cpu_with_rom()
    write_reset_vector(rom, 0x8000)
    load_program(rom, 0x8000, [0xEA])

    cpu.reset()
    cpu.a = 0x12
    cpu.x = 0x34
    cpu.y = 0x56
    cpu.p = 0x78
    cpu.s = 0x9A

    before = (cpu.pc, cpu.a, cpu.x, cpu.y, cpu.p, cpu.s)
    format_cpu_trace(cpu)
    after = (cpu.pc, cpu.a, cpu.x, cpu.y, cpu.p, cpu.s)

    assert after == before


def test_format_cpu_trace_changes_after_cpu_step_because_cpu_state_changed():
    """
    Objective:
    Trace does not execute instructions, but it should reflect state changes made
    by normal CPU.step() calls.

    Program:
        LDA #$42
        NOP
    """
    cpu, bus, rom = make_cpu_with_rom()
    write_reset_vector(rom, 0x8000)
    load_program(rom, 0x8000, [0xA9, 0x42, 0xEA])

    cpu.reset()

    first_trace = format_cpu_trace(cpu)
    cpu.step()
    second_trace = format_cpu_trace(cpu)

    assert first_trace == "8000 A9 A:00 X:00 Y:00 P:04 S:FD"
    assert second_trace == "8002 EA A:42 X:00 Y:00 P:04 S:FD"
