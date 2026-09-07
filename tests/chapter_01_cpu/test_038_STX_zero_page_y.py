"""
Test 038 - Add STX zero-page,Y ($96).

File to update:
    emulator/cpu/opcodes.py

Locations:
    opcodes.stx_zero_page_y
    opcodes.OPCODE_TABLE[$96]

Why this step exists:
This lesson reuses the zero-page,Y helper first introduced in Test 029 to add STX's
indexed zero-page encoding. Address calculation remains separate from the core store
operation.

Complete example implementation:

    # emulator/cpu/opcodes.py
    def stx_zero_page_y(cpu: CPU):
        addr = zero_page_y(cpu)
        stx(cpu, addr)


    OPCODE_TABLE = {
        # Preserve existing entries.
        0x96: stx_zero_page_y,
    }

Important invariants:
    - $96 maps to stx_zero_page_y
    - Y, not X, indexes the one-byte operand
    - base plus Y wraps within page $00
    - stx writes X and leaves Zero and Negative unchanged

Common misconception:
The register being stored does not choose the index register. STX $nn,Y stores X but
uses Y to calculate the destination.

Out of scope:
    - absolute STX
    - changes to zero_page_y or stx
    - cycle timing
"""
import inspect

from emulator.bus.cpu_bus import CpuBus
from emulator.cpu import opcodes
from emulator.cpu.cpu import CPU
from emulator.memory.fake_rom import FakeROM
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG


def make_cpu_with_rom():
    rom = FakeROM()
    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)
    bus = CpuBus(program_rom=rom)
    return CPU(bus), bus, rom


def test_stx_zero_page_y_handler_exists_and_is_in_opcode_table():
    """
    Objective:
    Create in opcodes.py:
        def stx_zero_page_y(cpu):
            addr = zero_page_y(cpu)
            stx(cpu, addr)

    Then add:
        0x96: stx_zero_page_y

    Important:
    STX Zero Page uses Y, not X.
    """
    assert hasattr(opcodes, "stx_zero_page_y")
    assert callable(opcodes.stx_zero_page_y)
    assert list(inspect.signature(opcodes.stx_zero_page_y).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x96] is opcodes.stx_zero_page_y


def test_opcode_96_stx_zero_page_y_stores_register_x():
    """
    Objective:
    96 10 means STX $10,Y.
    If Y is 0x03, store X into RAM $0013.
    """
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x96)
    rom.write(0x0001, 0x10)

    cpu.reset()
    cpu.x = 0x42
    cpu.y = 0x03
    cpu.step()

    assert bus.read(0x0013) == 0x42
    assert cpu.pc == 0x8002


def test_opcode_96_stx_zero_page_y_wraps_inside_page_zero():
    """
    Objective:
    Zero Page,Y wraps inside page $00.
    """
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x96)
    rom.write(0x0001, 0xFF)

    cpu.reset()
    cpu.x = 0x37
    cpu.y = 0x01
    cpu.step()

    assert bus.read(0x0000) == 0x37
    assert cpu.pc == 0x8002


def test_opcode_96_stx_zero_page_y_does_not_change_flags():
    """
    Objective:
    STX Zero Page,Y stores X but does not update flags.
    """
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x96)
    rom.write(0x0001, 0x10)

    cpu.reset()
    cpu.x = 0x00
    cpu.y = 0x03
    cpu.p = NEGATIVE_FLAG
    cpu.step()

    assert bus.read(0x0013) == 0x00
    assert (cpu.p & ZERO_FLAG) == 0
    assert (cpu.p & NEGATIVE_FLAG) != 0
