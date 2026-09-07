"""
Test 039 - Add STX absolute ($8E).

File to update:
    emulator/cpu/opcodes.py

Locations:
    opcodes.stx_absolute
    opcodes.OPCODE_TABLE[$8E]

Why this step exists:
This lesson adds STX's full 16-bit destination form. The existing `absolute` helper
decodes the little-endian address, while `stx` remains responsible only for writing X.

Complete example implementation:

    # emulator/cpu/opcodes.py
    def stx_absolute(cpu: CPU):
        addr = absolute(cpu)
        stx(cpu, addr)


    OPCODE_TABLE = {
        # Preserve existing entries.
        0x8E: stx_absolute,
    }

Important invariants:
    - $8E maps to stx_absolute
    - absolute consumes low byte then high byte and returns the destination address
    - the address itself is passed to stx, which writes X through the bus
    - the full instruction advances PC by three and does not modify flags

Common misconception:
`8E 00 02` stores X at $0200; the operand is a little-endian destination, not a value
to load into X or a big-endian address.

Out of scope:
    - indexed absolute STX encodings, which are not part of the supported STX set
    - changes to absolute or stx
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


def test_stx_absolute_handler_exists_and_is_in_opcode_table():
    """
    Objective:
    Create in opcodes.py:
        def stx_absolute(cpu):
            addr = absolute(cpu)
            stx(cpu, addr)

    Then add:
        0x8E: stx_absolute
    """
    assert hasattr(opcodes, "stx_absolute")
    assert callable(opcodes.stx_absolute)
    assert list(inspect.signature(opcodes.stx_absolute).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x8E] is opcodes.stx_absolute


def test_opcode_8E_stx_absolute_stores_register_x():
    """
    Objective:
    8E 00 02 means STX $0200.
    Store register X into RAM $0200.
    """
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x8E)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)

    cpu.reset()
    cpu.x = 0x42
    cpu.step()

    assert bus.read(0x0200) == 0x42
    assert cpu.pc == 0x8003


def test_opcode_8E_stx_absolute_does_not_change_flags():
    """
    Objective:
    STX Absolute stores X but does not update flags.
    """
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x8E)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)

    cpu.reset()
    cpu.x = 0x00
    cpu.p = NEGATIVE_FLAG
    cpu.step()

    assert bus.read(0x0200) == 0x00
    assert (cpu.p & ZERO_FLAG) == 0
    assert (cpu.p & NEGATIVE_FLAG) != 0
