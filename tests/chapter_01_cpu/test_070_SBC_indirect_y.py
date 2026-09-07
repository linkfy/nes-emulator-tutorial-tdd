"""
Test 070 - Add SBC (Indirect),Y.

File to update:
    emulator/cpu/opcodes.py

Symbols to add/update:
    opcodes.sbc_indirect_y and OPCODE_TABLE[0xF1]

Why this step exists:
This final SBC addressing variant uses the existing `indirect_y` resolver to read
a base pointer from zero page, add Y, and supply the target byte to `sbc`.

Complete example implementation:

    # emulator/cpu/opcodes.py
    def sbc_indirect_y(cpu: CPU):
        addr = indirect_y(cpu)
        value = cpu.bus.read(addr)
        sbc(cpu, value)

    OPCODE_TABLE = {
        # ... existing entries ...
        0xF1: sbc_indirect_y,
    }

Important invariants:
    - `indirect_y` reads the zero-page pointer before adding Y
    - the handler reads the byte at the final address exactly once
    - the read value is passed to `sbc`, which owns A and flag updates
    - executing the two-byte instruction advances PC by two bytes

Common misconception:
(Indirect),Y does not add Y to the zero-page pointer location before dereferencing;
that pre-indexing behavior belongs to (Indirect,X).

Out of scope:
    - later INC and other instruction families
    - changes to indirect addressing or SBC arithmetic
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


def test_sbc_indirect_y_handler_exists_and_is_in_opcode_table():
    """Objective: create sbc_indirect_y(cpu) and add 0xF1 to OPCODE_TABLE."""
    assert hasattr(opcodes, "sbc_indirect_y")
    assert callable(opcodes.sbc_indirect_y)
    assert list(inspect.signature(opcodes.sbc_indirect_y).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xF1] is opcodes.sbc_indirect_y


def test_opcode_F1_sbc_indirect_y_subtracts_value_from_final_address():
    """Objective: F1 20 with Y=0x04 uses base pointer $0200 and subtracts RAM[$0204]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xF1)
    rom.write(0x0001, 0x20)
    bus.write(0x0020, 0x00)
    bus.write(0x0021, 0x02)
    bus.write(0x0204, 0x01)

    cpu.reset()
    cpu.a = 0x10
    cpu.y = 0x04
    cpu.flags.set_carry_flag(True)
    cpu.step()

    assert cpu.a == 0x0F
    assert cpu.pc == 0x8002
