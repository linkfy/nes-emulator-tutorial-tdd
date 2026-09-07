"""
Test 029 — Add zero-page,Y addressing.

File to update:
    emulator/cpu/addressing_modes.py

Location:
    addressing_modes.zero_page_y

Why this step exists:
Some later instruction encodings index a zero-page operand with Y rather than X.
This lesson introduces only that reusable address calculation, parallel to Test 017's
`zero_page_x`, before connecting it to any opcode.

Complete example implementation:

    # emulator/cpu/addressing_modes.py
    def zero_page_y(cpu) -> int:
        base = cpu.fetch_byte()
        address = (base + cpu.y) & 0xFF
        return address

Important invariants:
    - exactly one operand byte is fetched
    - Y, not X, is added to the operand
    - the result wraps to eight bits and therefore remains in page $00
    - the helper returns an address and performs no memory read at that address

Common misconception:
Mask the sum, not merely the operand: `$FF + $01` must become $0000 rather than
$0100.

Out of scope:
    - adding or changing opcode handlers
    - the LDX instruction itself
    - cycle timing
"""
import inspect

from emulator.bus.cpu_bus import CpuBus
from emulator.cpu import addressing_modes
from emulator.cpu.cpu import CPU
from emulator.memory.fake_rom import FakeROM


def make_cpu_with_rom():
    rom = FakeROM()
    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)
    bus = CpuBus(program_rom=rom)
    return CPU(bus), bus, rom


def test_zero_page_y_addressing_mode_exists():
    """
    Objective:
    Create in addressing_modes.py:
        def zero_page_y(cpu):
            ...

    Example implementation:
        base = cpu.fetch_byte()
        return (base + cpu.y) & 0xFF
    """
    assert hasattr(addressing_modes, "zero_page_y")
    assert callable(addressing_modes.zero_page_y)
    assert list(inspect.signature(addressing_modes.zero_page_y).parameters) == ["cpu"]


def test_zero_page_y_adds_y_to_base_address():
    """
    Objective:
    If the operand is 0x10 and Y is 0x03,
    zero_page_y(cpu) returns 0x0013.
    """
    cpu, _, rom = make_cpu_with_rom()

    cpu.reset()
    cpu.y = 0x03
    rom.write(0x0000, 0x10)

    addr = addressing_modes.zero_page_y(cpu)

    assert addr == 0x0013
    assert cpu.pc == 0x8001


def test_zero_page_y_wraps_inside_page_zero():
    """
    Objective:
    Zero Page,Y wraps inside page $00.

    Example:
    0xFF + Y where Y is 0x01 becomes 0x00, not 0x0100.
    """
    cpu, _, rom = make_cpu_with_rom()

    cpu.reset()
    cpu.y = 0x01
    rom.write(0x0000, 0xFF)

    addr = addressing_modes.zero_page_y(cpu)

    assert addr == 0x0000
    assert cpu.pc == 0x8001
