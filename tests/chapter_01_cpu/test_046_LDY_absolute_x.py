"""
Test 046 - Add LDY absolute,X ($BC).

File to update:
    emulator/cpu/opcodes.py

Locations:
    opcodes imports of absolute_x and ldy
    opcodes.ldy_absolute_x
    opcodes.OPCODE_TABLE[$BC]

Why this step exists:
This lesson completes the LDY opcode family by reusing absolute,X address resolution,
then reading the effective address and applying the existing `ldy` behavior.

Complete example implementation:

    # emulator/cpu/opcodes.py
    from emulator.cpu.addressing_modes import absolute_x
    from emulator.cpu.instructions import ldy


    def ldy_absolute_x(cpu: CPU):
        addr = absolute_x(cpu)
        value = cpu.bus.read(addr)
        ldy(cpu, value)


    OPCODE_TABLE = {
        # Preserve existing entries.
        0xBC: ldy_absolute_x,
    }

Important invariants:
    - $BC maps to ldy_absolute_x and consumes two operand bytes
    - X, not Y, is added to the decoded 16-bit base address
    - the effective address is read before its value is passed to ldy
    - `ldy` updates Zero and Negative from the loaded byte

Common misconception:
LDY absolute,X does not index with the destination register Y; the encoding explicitly
uses X.

Out of scope:
    - STY opcode handlers
    - page-crossing cycle penalties
    - changes to absolute_x
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


def test_ldy_absolute_x_handler_exists_and_is_in_opcode_table():
    """Objective: create ldy_absolute_x(cpu) and add 0xBC to OPCODE_TABLE."""
    assert hasattr(opcodes, "ldy_absolute_x")
    assert callable(opcodes.ldy_absolute_x)
    assert list(inspect.signature(opcodes.ldy_absolute_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xBC] is opcodes.ldy_absolute_x


def test_opcode_BC_ldy_absolute_x_loads_register_y():
    """Objective: BC 00 02 with X=0x04 reads RAM[$0204] into Y."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xBC)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0204, 0x42)

    cpu.reset()
    cpu.x = 0x04
    cpu.step()

    assert cpu.y == 0x42
    assert cpu.pc == 0x8003
