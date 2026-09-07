"""
Test 044 - Add LDY zero page,X ($B4).

File to update:
    emulator/cpu/opcodes.py

Locations:
    opcodes imports of zero_page_x and ldy
    opcodes.ldy_zero_page_x
    opcodes.OPCODE_TABLE[$B4]

Why this step exists:
This encoding reuses the established zero-page,X address calculation, including its
eight-bit wrap, before loading the resolved byte through the core `ldy` instruction.

Complete example implementation:

    # emulator/cpu/opcodes.py
    from emulator.cpu.addressing_modes import zero_page_x
    from emulator.cpu.instructions import ldy


    def ldy_zero_page_x(cpu: CPU):
        addr = zero_page_x(cpu)
        value = cpu.bus.read(addr)
        ldy(cpu, value)


    OPCODE_TABLE = {
        # Preserve existing entries.
        0xB4: ldy_zero_page_x,
    }

Important invariants:
    - $B4 maps to ldy_zero_page_x and consumes one operand byte
    - X, not Y, indexes the zero-page operand
    - the effective address wraps within page $00
    - the resolved memory value is passed to ldy, which updates Zero and Negative

Common misconception:
LDY names the destination register, not the index register. The $B4 encoding uses X
to calculate the address.

Out of scope:
    - absolute and absolute,X LDY encodings
    - changing zero_page_x
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


def test_ldy_zero_page_x_handler_exists_and_is_in_opcode_table():
    """Objective: create ldy_zero_page_x(cpu) and add 0xB4 to OPCODE_TABLE."""
    assert hasattr(opcodes, "ldy_zero_page_x")
    assert callable(opcodes.ldy_zero_page_x)
    assert list(inspect.signature(opcodes.ldy_zero_page_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xB4] is opcodes.ldy_zero_page_x


def test_opcode_B4_ldy_zero_page_x_loads_register_y():
    """Objective: B4 10 with X=0x03 reads RAM[$0013] into Y."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xB4)
    rom.write(0x0001, 0x10)
    bus.write(0x0013, 0x42)

    cpu.reset()
    cpu.x = 0x03
    cpu.step()

    assert cpu.y == 0x42
    assert cpu.pc == 0x8002


def test_opcode_B4_ldy_zero_page_x_wraps():
    """Objective: Zero Page,X wraps inside page $00."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xB4)
    rom.write(0x0001, 0xFF)
    bus.write(0x0000, 0x37)

    cpu.reset()
    cpu.x = 0x01
    cpu.step()

    assert cpu.y == 0x37
    assert cpu.pc == 0x8002
