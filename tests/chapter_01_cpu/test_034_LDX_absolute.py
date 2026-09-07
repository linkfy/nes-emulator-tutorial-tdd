"""
Test 034 - Add LDX absolute ($AE).

File to update:
    emulator/cpu/opcodes.py

Locations:
    opcodes.ldx_absolute
    opcodes.OPCODE_TABLE[$AE]

Why this step exists:
This lesson extends LDX from one-byte addresses to a full 16-bit memory address while
preserving the established boundary: `absolute` decodes the operand, the handler
reads memory, and `ldx` updates X and its flags.

Complete example implementation:

    # emulator/cpu/opcodes.py
    def ldx_absolute(cpu: CPU):
        addr = absolute(cpu)
        value = cpu.bus.read(addr)
        ldx(cpu, value)


    OPCODE_TABLE = {
        # Preserve existing entries.
        0xAE: ldx_absolute,
    }

Important invariants:
    - $AE maps to ldx_absolute
    - absolute consumes the low operand byte before the high operand byte
    - one byte is read from the resulting 16-bit address and passed to ldx
    - the full instruction advances PC by three bytes

Common misconception:
`AE 00 02` addresses $0200 because 6502 operands are little-endian; it does not
address $0002 or load either operand byte directly.

Out of scope:
    - absolute,Y LDX
    - changes to absolute or ldx
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


def test_ldx_absolute_handler_exists_and_is_in_opcode_table():
    """Objective: create ldx_absolute(cpu) and add 0xAE to OPCODE_TABLE."""
    assert hasattr(opcodes, "ldx_absolute")
    assert callable(opcodes.ldx_absolute)
    assert list(inspect.signature(opcodes.ldx_absolute).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xAE] is opcodes.ldx_absolute


def test_opcode_AE_ldx_absolute_loads_register_x():
    """Objective: AE 00 02 means LDX $0200, so X loads RAM[$0200]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xAE)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0200, 0x42)

    cpu.reset()
    cpu.step()

    assert cpu.x == 0x42
    assert cpu.pc == 0x8003
