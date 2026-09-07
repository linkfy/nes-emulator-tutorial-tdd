"""
Test 047 - Add STY zero page ($84).

File to update:
    emulator/cpu/opcodes.py

Locations:
    opcodes imports of zero_page and sty
    opcodes.sty_zero_page
    opcodes.OPCODE_TABLE[$84]

Why this step exists:
The core `sty` instruction already performs the write. This lesson connects its first
encoding by resolving a one-byte zero-page destination and passing that address to
`sty`.

Complete example implementation:

    # emulator/cpu/opcodes.py
    from emulator.cpu.addressing_modes import zero_page
    from emulator.cpu.instructions import sty


    def sty_zero_page(cpu: CPU):
        addr = zero_page(cpu)
        sty(cpu, addr)


    OPCODE_TABLE = {
        # Preserve existing entries.
        0x84: sty_zero_page,
    }

Important invariants:
    - $84 maps to sty_zero_page and consumes one operand byte
    - the operand resolves to $00nn and is passed as an address
    - `sty` writes Y through the bus
    - STY leaves Zero and Negative unchanged

Common misconception:
Do not read from the resolved address before calling `sty`; stores pass a destination
address to the core instruction, not a value.

Out of scope:
    - zero-page,X and absolute STY encodings
    - new addressing modes
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


def test_sty_zero_page_handler_exists_and_is_in_opcode_table():
    """Objective: create sty_zero_page(cpu) and add 0x84 to OPCODE_TABLE."""
    assert hasattr(opcodes, "sty_zero_page")
    assert callable(opcodes.sty_zero_page)
    assert list(inspect.signature(opcodes.sty_zero_page).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x84] is opcodes.sty_zero_page


def test_opcode_84_sty_zero_page_stores_register_y():
    """Objective: 84 10 means STY $10, so RAM[$0010] gets Y."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x84)
    rom.write(0x0001, 0x10)

    cpu.reset()
    cpu.y = 0x42
    cpu.step()

    assert bus.read(0x0010) == 0x42
    assert cpu.pc == 0x8002


def test_opcode_84_sty_zero_page_does_not_change_flags():
    """Objective: STY stores Y but does not update flags."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x84)
    rom.write(0x0001, 0x10)

    cpu.reset()
    cpu.y = 0x00
    cpu.p = NEGATIVE_FLAG
    cpu.step()

    assert bus.read(0x0010) == 0x00
    assert (cpu.p & ZERO_FLAG) == 0
    assert (cpu.p & NEGATIVE_FLAG) != 0
