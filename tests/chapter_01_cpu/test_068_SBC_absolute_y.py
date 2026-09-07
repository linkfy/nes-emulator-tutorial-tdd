"""
Test 068 - Add SBC Absolute,Y.

File to update:
    emulator/cpu/opcodes.py

Symbols to add/update:
    opcodes.sbc_absolute_y and OPCODE_TABLE[0xF9]

Why this step exists:
This lesson parallels Absolute,X using the existing `absolute_y` resolver so SBC
can subtract a byte from a Y-indexed 16-bit address.

Complete example implementation:

    # emulator/cpu/opcodes.py
    def sbc_absolute_y(cpu: CPU):
        addr = absolute_y(cpu)
        value = cpu.bus.read(addr)
        sbc(cpu, value)

    OPCODE_TABLE = {
        # ... existing entries ...
        0xF9: sbc_absolute_y,
    }

Important invariants:
    - `absolute_y` consumes two operand bytes and adds Y, not X
    - the handler reads from the final indexed address exactly once
    - `sbc` receives the byte value and owns arithmetic flag updates
    - executing the three-byte instruction advances PC by three bytes

Common misconception:
Do not copy the Absolute,X wrapper and leave it using X or `absolute_x`; opcode $F9
must resolve through Y.

Out of scope:
    - indirect SBC wrappers
    - page-cross cycle penalties
    - changes to addressing helpers or SBC arithmetic
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


def test_sbc_absolute_y_handler_exists_and_is_in_opcode_table():
    """Objective: create sbc_absolute_y(cpu) and add 0xF9 to OPCODE_TABLE."""
    assert hasattr(opcodes, "sbc_absolute_y")
    assert callable(opcodes.sbc_absolute_y)
    assert list(inspect.signature(opcodes.sbc_absolute_y).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xF9] is opcodes.sbc_absolute_y


def test_opcode_F9_sbc_absolute_y_subtracts_indexed_value():
    """Objective: F9 00 02 with Y=0x04 subtracts RAM[$0204] from A."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xF9)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0204, 0x01)

    cpu.reset()
    cpu.a = 0x10
    cpu.y = 0x04
    cpu.flags.set_carry_flag(True)
    cpu.step()

    assert cpu.a == 0x0F
    assert cpu.pc == 0x8003
