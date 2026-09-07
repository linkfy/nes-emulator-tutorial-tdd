"""
Test 094 - Add ASL Absolute,X.

In this step, complete the ASL addressing sequence with Absolute,X.

File and symbols:
    emulator/cpu/opcodes.py: asl_absolute_x, OPCODE_TABLE[0x1E]

Why this step exists:
This is the final ASL addressing transition. It composes the existing
`absolute_x` resolver with the memory `asl` implementation introduced earlier.

Suggested implementation for this step:

    # emulator/cpu/opcodes.py
    def asl_absolute_x(cpu: CPU):
        addr = absolute_x(cpu)
        asl(cpu, addr)

    OPCODE_TABLE = {
        # existing entries unchanged
        0x1E: asl_absolute_x,
    }

Important invariants:
    - decode the little-endian 16-bit base before adding X
    - the instruction remains three bytes; X is a register, not another operand
    - `asl` owns read/modify/write and flag updates at the effective address
    - the accumulator is unchanged

Common misconception:
For `1E 00 02` with X=0x04, add X to $0200, not to either operand byte.

Out of scope:
    - LSR introduced by Tests 095-101
    - modifying `absolute_x` or `asl`
    - page-cross and read/modify/write cycle timing
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


def test_asl_absolute_x_handler_exists_and_is_in_opcode_table():
    """Objective: create asl_absolute_x(cpu) and add 0x1E to OPCODE_TABLE."""
    assert hasattr(opcodes, "asl_absolute_x")
    assert callable(opcodes.asl_absolute_x)
    assert list(inspect.signature(opcodes.asl_absolute_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x1E] is opcodes.asl_absolute_x


def test_opcode_1E_asl_absolute_x_shifts_indexed_memory_value():
    """Objective: 1E 00 02 with X=0x04 shifts RAM[$0204]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x1E)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0204, 0b0000_0011)

    cpu.reset()
    cpu.x = 0x04
    cpu.step()

    assert bus.read(0x0204) == 0b0000_0110
    assert cpu.pc == 0x8003
