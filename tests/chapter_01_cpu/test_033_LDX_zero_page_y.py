"""
Test 033 - Add LDX zero-page,Y ($B6).

File to update:
    emulator/cpu/opcodes.py

Locations:
    opcodes.ldx_zero_page_y
    opcodes.OPCODE_TABLE[$B6]

Why this step exists:
Test 029 introduced the wrapping zero-page,Y address helper. This lesson gives that
helper its first opcode use by combining it with a memory read and the existing
`ldx` instruction.

Complete example implementation:

    # emulator/cpu/opcodes.py
    def ldx_zero_page_y(cpu: CPU):
        addr = zero_page_y(cpu)
        value = cpu.bus.read(addr)
        ldx(cpu, value)


    OPCODE_TABLE = {
        # Preserve existing entries.
        0xB6: ldx_zero_page_y,
    }

Important invariants:
    - $B6 maps to ldx_zero_page_y
    - the index is Y, not X
    - base plus Y wraps to eight bits before the bus read
    - one operand byte is consumed, and ldx owns X and flag updates

Common misconception:
LDX's destination register does not select the index register: this encoding uses Y,
and `$FF,Y` with Y=$01 reads $0000 rather than $0100.

Out of scope:
    - changing zero_page_y or ldx
    - absolute LDX encodings
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


def test_ldx_zero_page_y_handler_exists_and_is_in_opcode_table():
    """Objective: create ldx_zero_page_y(cpu) and add 0xB6 to OPCODE_TABLE."""
    assert hasattr(opcodes, "ldx_zero_page_y")
    assert callable(opcodes.ldx_zero_page_y)
    assert list(inspect.signature(opcodes.ldx_zero_page_y).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xB6] is opcodes.ldx_zero_page_y


def test_opcode_B6_ldx_zero_page_y_loads_register_x():
    """Objective: B6 10 with Y=0x03 reads RAM[$0013] into X."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xB6)
    rom.write(0x0001, 0x10)
    bus.write(0x0013, 0x42)

    cpu.reset()
    cpu.y = 0x03
    cpu.step()

    assert cpu.x == 0x42
    assert cpu.pc == 0x8002


def test_opcode_B6_ldx_zero_page_y_wraps():
    """Objective: Zero Page,Y wraps inside page $00."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xB6)
    rom.write(0x0001, 0xFF)
    bus.write(0x0000, 0x37)

    cpu.reset()
    cpu.y = 0x01
    cpu.step()

    assert cpu.x == 0x37
    assert cpu.pc == 0x8002
