"""
Test 043 - Add LDY zero page ($A4).

File to update:
    emulator/cpu/opcodes.py

Locations:
    opcodes imports of zero_page and ldy
    opcodes.ldy_zero_page
    opcodes.OPCODE_TABLE[$A4]

Why this step exists:
Unlike immediate LDY, zero-page LDY resolves the operand to an address, reads the
byte at that address, and then delegates register and flag behavior to `ldy`.

Complete example implementation:

    # emulator/cpu/opcodes.py
    from emulator.cpu.addressing_modes import zero_page
    from emulator.cpu.instructions import ldy


    def ldy_zero_page(cpu: CPU):
        addr = zero_page(cpu)
        value = cpu.bus.read(addr)
        ldy(cpu, value)


    OPCODE_TABLE = {
        # Preserve existing entries.
        0xA4: ldy_zero_page,
    }

Important invariants:
    - $A4 maps to ldy_zero_page and consumes one operand byte
    - zero_page returns an address in $0000-$00FF
    - the handler performs one data read and passes that value, not its address, to ldy
    - `ldy` updates Zero and Negative

Common misconception:
Passing `addr` directly to `ldy` would load the zero-page location number rather than
the byte stored there.

Out of scope:
    - zero-page,X and absolute LDY encodings
    - new addressing-mode helpers
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


def test_ldy_zero_page_handler_exists_and_is_in_opcode_table():
    """Objective: create ldy_zero_page(cpu) and add 0xA4 to OPCODE_TABLE."""
    assert hasattr(opcodes, "ldy_zero_page")
    assert callable(opcodes.ldy_zero_page)
    assert list(inspect.signature(opcodes.ldy_zero_page).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xA4] is opcodes.ldy_zero_page


def test_opcode_A4_ldy_zero_page_loads_register_y():
    """Objective: A4 10 means LDY $10, so Y loads RAM[$0010]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xA4)
    rom.write(0x0001, 0x10)
    bus.write(0x0010, 0x42)

    cpu.reset()
    cpu.step()

    assert cpu.y == 0x42
    assert cpu.pc == 0x8002
