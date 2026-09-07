"""
Test 049 - Add STY absolute ($8C).

File to update:
    emulator/cpu/opcodes.py

Locations:
    opcodes imports of absolute and sty
    opcodes.sty_absolute
    opcodes.OPCODE_TABLE[$8C]

Why this step exists:
Absolute STY completes the supported STY family by decoding a 16-bit destination and
passing that address to the existing store instruction.

Complete example implementation:

    # emulator/cpu/opcodes.py
    from emulator.cpu.addressing_modes import absolute
    from emulator.cpu.instructions import sty


    def sty_absolute(cpu: CPU):
        addr = absolute(cpu)
        sty(cpu, addr)


    OPCODE_TABLE = {
        # Preserve existing entries.
        0x8C: sty_absolute,
    }

Important invariants:
    - $8C maps to sty_absolute and consumes two operand bytes
    - the little-endian operand is resolved as a 16-bit destination address
    - sty writes Y to that address through the bus
    - execution advances three bytes total and flags remain unchanged

Common misconception:
Do not pass a value read from the absolute address to `sty`; the core store instruction
requires the destination address itself.

Out of scope:
    - transfer instructions and their opcodes
    - additional STY addressing modes
    - cycle timing and write-side hardware effects
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


def test_sty_absolute_handler_exists_and_is_in_opcode_table():
    """Objective: create sty_absolute(cpu) and add 0x8C to OPCODE_TABLE."""
    assert hasattr(opcodes, "sty_absolute")
    assert callable(opcodes.sty_absolute)
    assert list(inspect.signature(opcodes.sty_absolute).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x8C] is opcodes.sty_absolute


def test_opcode_8C_sty_absolute_stores_register_y():
    """Objective: 8C 00 02 means STY $0200, so RAM[$0200] gets Y."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x8C)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)

    cpu.reset()
    cpu.y = 0x42
    cpu.step()

    assert bus.read(0x0200) == 0x42
    assert cpu.pc == 0x8003


def test_opcode_8C_sty_absolute_does_not_change_flags():
    """Objective: STY Absolute stores Y but does not update flags."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x8C)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)

    cpu.reset()
    cpu.y = 0x00
    cpu.p = NEGATIVE_FLAG
    cpu.step()

    assert bus.read(0x0200) == 0x00
    assert (cpu.p & ZERO_FLAG) == 0
    assert (cpu.p & NEGATIVE_FLAG) != 0
