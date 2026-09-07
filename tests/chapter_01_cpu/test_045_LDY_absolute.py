"""
Test 045 - Add LDY absolute ($AC).

File to update:
    emulator/cpu/opcodes.py

Locations:
    opcodes imports of absolute and ldy
    opcodes.ldy_absolute
    opcodes.OPCODE_TABLE[$AC]

Why this step exists:
Absolute addressing extends LDY beyond page zero. The handler decodes the existing
little-endian 16-bit operand, reads that address, and delegates the loaded value to
`ldy`.

Complete example implementation:

    # emulator/cpu/opcodes.py
    from emulator.cpu.addressing_modes import absolute
    from emulator.cpu.instructions import ldy


    def ldy_absolute(cpu: CPU):
        addr = absolute(cpu)
        value = cpu.bus.read(addr)
        ldy(cpu, value)


    OPCODE_TABLE = {
        # Preserve existing entries.
        0xAC: ldy_absolute,
    }

Important invariants:
    - $AC maps to ldy_absolute and consumes two operand bytes
    - absolute combines the low byte first and high byte second
    - the handler reads the effective address and passes the resulting value to ldy
    - execution advances three bytes total, including the opcode

Common misconception:
Do not reverse `AC 00 02`; the established absolute helper resolves those operand
bytes to $0200, not $0002.

Out of scope:
    - absolute,X LDY
    - changing the absolute addressing helper
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


def test_ldy_absolute_handler_exists_and_is_in_opcode_table():
    """Objective: create ldy_absolute(cpu) and add 0xAC to OPCODE_TABLE."""
    assert hasattr(opcodes, "ldy_absolute")
    assert callable(opcodes.ldy_absolute)
    assert list(inspect.signature(opcodes.ldy_absolute).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xAC] is opcodes.ldy_absolute


def test_opcode_AC_ldy_absolute_loads_register_y():
    """Objective: AC 00 02 means LDY $0200, so Y loads RAM[$0200]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xAC)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0200, 0x42)

    cpu.reset()
    cpu.step()

    assert cpu.y == 0x42
    assert cpu.pc == 0x8003
