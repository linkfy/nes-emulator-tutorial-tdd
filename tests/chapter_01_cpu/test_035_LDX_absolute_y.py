"""
Test 035 - Add LDX absolute,Y ($BE).

File to update:
    emulator/cpu/opcodes.py

Locations:
    opcodes.ldx_absolute_y
    opcodes.OPCODE_TABLE[$BE]

Why this step exists:
This lesson completes the LDX opcode family available at this point by reusing the
existing absolute,Y helper. As with the other memory forms, the handler resolves and
reads the operand before passing its value to `ldx`.

Complete example implementation:

    # emulator/cpu/opcodes.py
    def ldx_absolute_y(cpu: CPU):
        addr = absolute_y(cpu)
        value = cpu.bus.read(addr)
        ldx(cpu, value)


    OPCODE_TABLE = {
        # Preserve existing entries.
        0xBE: ldx_absolute_y,
    }

Important invariants:
    - $BE maps to ldx_absolute_y
    - the little-endian base address is indexed with Y, not X
    - the byte at the indexed address is passed to ldx
    - two operand bytes are consumed, so the full instruction advances PC by three

Common misconception:
Do not wrap absolute,Y within page $00; unlike zero-page,Y, its indexed address is a
16-bit result.

Out of scope:
    - store-X and load-Y instructions
    - changes to absolute_y or ldx
    - cycle timing and page-cross penalties
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


def test_ldx_absolute_y_handler_exists_and_is_in_opcode_table():
    """Objective: create ldx_absolute_y(cpu) and add 0xBE to OPCODE_TABLE."""
    assert hasattr(opcodes, "ldx_absolute_y")
    assert callable(opcodes.ldx_absolute_y)
    assert list(inspect.signature(opcodes.ldx_absolute_y).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xBE] is opcodes.ldx_absolute_y


def test_opcode_BE_ldx_absolute_y_loads_register_x():
    """Objective: BE 00 02 with Y=0x04 reads RAM[$0204] into X."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xBE)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0204, 0x42)

    cpu.reset()
    cpu.y = 0x04
    cpu.step()

    assert cpu.x == 0x42
    assert cpu.pc == 0x8003
