"""
Test 092 - Add ASL Zero Page,X.

In this step, extend the Zero Page form from Test 091 with X indexing.

File and symbols:
    emulator/cpu/opcodes.py: asl_zero_page_x, OPCODE_TABLE[0x16]

Why this step exists:
After Test 091 wired plain zero-page ASL, this transition reuses the established
`zero_page_x` resolver so indexing and zero-page wrap remain addressing concerns.

Suggested implementation for this step:

    # emulator/cpu/opcodes.py
    def asl_zero_page_x(cpu: CPU):
        addr = zero_page_x(cpu)
        asl(cpu, addr)

    OPCODE_TABLE = {
        # existing entries unchanged
        0x16: asl_zero_page_x,
    }

Important invariants:
    - the effective address is `(operand + cpu.x) & 0xFF`
    - one operand byte is consumed, so PC advances by two including the opcode
    - `asl` owns the memory write and Carry, Zero, and Negative updates
    - indexing changes the destination, not the value passed to `asl`

Common misconception:
Zero Page,X does not spill into page one: base 0xFE plus X=0x03 targets $0001.

Out of scope:
    - ASL Absolute and Absolute,X in Tests 093-094
    - changing `zero_page_x` or `asl`
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


def test_asl_zero_page_x_handler_exists_and_is_in_opcode_table():
    """Objective: create asl_zero_page_x(cpu) and add 0x16 to OPCODE_TABLE."""
    assert hasattr(opcodes, "asl_zero_page_x")
    assert callable(opcodes.asl_zero_page_x)
    assert list(inspect.signature(opcodes.asl_zero_page_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x16] is opcodes.asl_zero_page_x


def test_opcode_16_asl_zero_page_x_shifts_indexed_memory_value():
    """Objective: 16 20 with X=0x04 shifts RAM[$0024]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x16)
    rom.write(0x0001, 0x20)
    bus.write(0x0024, 0b0000_0011)

    cpu.reset()
    cpu.x = 0x04
    cpu.step()

    assert bus.read(0x0024) == 0b0000_0110
    assert cpu.pc == 0x8002


def test_opcode_16_asl_zero_page_x_wraps_zero_page_address():
    """Objective: zero-page indexed addresses wrap to 8 bits."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x16)
    rom.write(0x0001, 0xFE)
    bus.write(0x0001, 0x02)

    cpu.reset()
    cpu.x = 0x03
    cpu.step()

    assert bus.read(0x0001) == 0x04
    assert cpu.pc == 0x8002
