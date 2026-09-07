"""
Test 099 - Add LSR Zero Page,X.

In this step, add X indexing to the Zero Page LSR form from Test 098.

File and symbols:
    emulator/cpu/opcodes.py: lsr_zero_page_x, OPCODE_TABLE[0x56]

Why this step exists:
This transition adds indexed zero-page LSR by composing the existing `zero_page_x`
resolver with memory `lsr`; it adds no new shift semantics.

Suggested implementation for this step:

    # emulator/cpu/opcodes.py
    def lsr_zero_page_x(cpu: CPU):
        addr = zero_page_x(cpu)
        lsr(cpu, addr)

    OPCODE_TABLE = {
        # existing entries unchanged
        0x56: lsr_zero_page_x,
    }

Important invariants:
    - effective address calculation wraps to eight bits within zero page
    - only one operand byte is consumed, so PC advances by two including the opcode
    - `lsr` owns the memory write and C/Z/N changes
    - X selects the destination and is not modified

Common misconception:
Base 0xFE plus X=0x03 targets $0001, not $0101.

Out of scope:
    - LSR Absolute and Absolute,X in Tests 100-101
    - changes to addressing or LSR behavior
    - cycle timing
"""
import inspect

from emulator.bus.cpu_bus import CpuBus
from emulator.cpu import opcodes
from emulator.cpu.cpu import CPU
from emulator.memory.fake_rom import FakeROM


def make_cpu_with_rom():
    rom = FakeROM()
    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)
    bus = CpuBus(program_rom=rom)
    return CPU(bus), bus, rom


def test_lsr_zero_page_x_handler_exists_and_is_in_opcode_table():
    """Objective: create lsr_zero_page_x(cpu) and add 0x56 to OPCODE_TABLE."""
    assert hasattr(opcodes, "lsr_zero_page_x")
    assert callable(opcodes.lsr_zero_page_x)
    assert list(inspect.signature(opcodes.lsr_zero_page_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x56] is opcodes.lsr_zero_page_x


def test_opcode_56_lsr_zero_page_x_shifts_indexed_memory_value():
    """Objective: 56 20 with X=0x04 shifts RAM[$0024]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x56)
    rom.write(0x0001, 0x20)
    bus.write(0x0024, 0b0000_0110)

    cpu.reset()
    cpu.x = 0x04
    cpu.step()

    assert bus.read(0x0024) == 0b0000_0011
    assert cpu.pc == 0x8002


def test_opcode_56_lsr_zero_page_x_wraps_zero_page_address():
    """Objective: zero-page indexed addresses wrap to 8 bits."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x56)
    rom.write(0x0001, 0xFE)
    bus.write(0x0001, 0x04)

    cpu.reset()
    cpu.x = 0x03
    cpu.step()

    assert bus.read(0x0001) == 0x02
    assert cpu.pc == 0x8002
