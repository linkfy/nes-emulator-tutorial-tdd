"""
Test 026 — Add absolute,Y STA ($99).

File to update:
    emulator/cpu/opcodes.py

Locations:
    opcodes.sta_absolute_y
    opcodes.OPCODE_TABLE[$99]

Why this step exists:
This is the Y-indexed counterpart to Test 025. It reuses `absolute_y` so the handler
only coordinates destination resolution and the existing `sta` write.

Complete example implementation:

    # emulator/cpu/opcodes.py
    def sta_absolute_y(cpu) -> None:
        address = absolute_y(cpu)
        sta(cpu, address)


    OPCODE_TABLE = {
        # Preserve existing entries.
        0x99: sta_absolute_y,
    }

Important invariants:
    - two operand bytes form the base before Y is added
    - Y, not X, selects the final destination
    - the full indexed address is passed to sta
    - STA does not update flags

Common misconception:
Copying the absolute,X handler without changing the addressing helper silently uses
the wrong index register when X and Y differ.

Out of scope:
    - indirect STA opcodes
    - page-cross cycle behavior
    - changes to absolute_y or sta
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


def test_sta_absolute_y_handler_exists_and_is_in_opcode_table():
    """
    Objective:
    Create sta_absolute_y(cpu) and add 0x99 to OPCODE_TABLE.
    """
    assert hasattr(opcodes, "sta_absolute_y")
    assert callable(opcodes.sta_absolute_y)
    assert list(inspect.signature(opcodes.sta_absolute_y).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x99] is opcodes.sta_absolute_y


def test_opcode_99_sta_absolute_y_stores_register_a():
    """
    Objective:
    99 00 02 means STA $0200,Y.
    If Y is 0x04, store A into RAM $0204.
    """
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x99)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)

    cpu.reset()
    cpu.a = 0x42
    cpu.y = 0x04
    cpu.step()

    assert bus.read(0x0204) == 0x42
    assert cpu.pc == 0x8003
