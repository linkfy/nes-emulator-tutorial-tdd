"""
Test 023 — Add zero-page,X STA ($95).

File to update:
    emulator/cpu/opcodes.py

Locations:
    opcodes.sta_zero_page_x
    opcodes.OPCODE_TABLE[$95]

Why this step exists:
This reuses the `sta` instruction from Test 022 and the wrapping `zero_page_x`
addressing mode from Test 017, showing that a store opcode handler only composes an
existing address calculation with the existing write operation.

Complete example implementation:

    # emulator/cpu/opcodes.py
    def sta_zero_page_x(cpu) -> None:
        address = zero_page_x(cpu)
        sta(cpu, address)


    OPCODE_TABLE = {
        # Preserve existing entries.
        0x95: sta_zero_page_x,
    }

Important invariants:
    - $95 consumes one operand byte
    - base plus X wraps within page $00
    - the value written is cpu.a
    - STA does not modify Zero or Negative

Common misconception:
Zero-page indexing does not carry into page $01; `$FF,X` with X=$01 targets $0000,
not $0100.

Out of scope:
    - changes to zero_page_x or sta
    - absolute and indirect STA opcodes
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


def test_sta_zero_page_x_handler_exists_and_is_in_opcode_table():
    """
    Objective:
    Create in opcodes.py:
        def sta_zero_page_x(cpu):
            addr = zero_page_x(cpu)
            sta(cpu, addr)

    Then add:
        0x95: sta_zero_page_x
    """
    assert hasattr(opcodes, "sta_zero_page_x")
    assert callable(opcodes.sta_zero_page_x)
    assert list(inspect.signature(opcodes.sta_zero_page_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x95] is opcodes.sta_zero_page_x


def test_opcode_95_sta_zero_page_x_stores_register_a():
    """
    Objective:
    95 10 means STA $10,X.
    If X is 0x03, store A into RAM $0013.
    """
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x95)
    rom.write(0x0001, 0x10)

    cpu.reset()
    cpu.a = 0x42
    cpu.x = 0x03
    cpu.step()

    assert bus.read(0x0013) == 0x42
    assert cpu.pc == 0x8002


def test_opcode_95_sta_zero_page_x_wraps_and_does_not_change_flags():
    """
    Objective:
    Zero Page,X wraps inside page $00.
    STA must not change Zero or Negative flags.
    """
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x95)
    rom.write(0x0001, 0xFF)

    cpu.reset()
    cpu.a = 0x00
    cpu.x = 0x01
    cpu.p = NEGATIVE_FLAG
    cpu.step()

    assert bus.read(0x0000) == 0x00
    assert (cpu.p & ZERO_FLAG) == 0
    assert (cpu.p & NEGATIVE_FLAG) != 0
