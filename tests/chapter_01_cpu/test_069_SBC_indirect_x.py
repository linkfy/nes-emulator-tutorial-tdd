"""
Test 069 - Add SBC (Indirect,X).

File to update:
    emulator/cpu/opcodes.py

Symbols to add/update:
    opcodes.sbc_indirect_x and OPCODE_TABLE[0xE1]

Why this step exists:
SBC gains pre-indexed indirect access by composing the existing `indirect_x`
resolver with the standard memory-read and instruction-delegation wrapper.

Complete example implementation:

    # emulator/cpu/opcodes.py
    def sbc_indirect_x(cpu: CPU):
        addr = indirect_x(cpu)
        value = cpu.bus.read(addr)
        sbc(cpu, value)

    OPCODE_TABLE = {
        # ... existing entries ...
        0xE1: sbc_indirect_x,
    }

Important invariants:
    - `indirect_x` adds X to the zero-page operand before reading the pointer
    - the pointer bytes and their zero-page wrap are handled by the resolver
    - the wrapper reads the final address and passes that byte to `sbc`
    - executing the two-byte instruction advances PC by two bytes

Common misconception:
Do not read the zero-page pointer location as the SBC operand; `indirect_x` returns
the final 16-bit target address whose contents must be read.

Out of scope:
    - the (Indirect),Y SBC wrapper
    - changes to indirect addressing or SBC arithmetic
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


def test_sbc_indirect_x_handler_exists_and_is_in_opcode_table():
    """Objective: create sbc_indirect_x(cpu) and add 0xE1 to OPCODE_TABLE."""
    assert hasattr(opcodes, "sbc_indirect_x")
    assert callable(opcodes.sbc_indirect_x)
    assert list(inspect.signature(opcodes.sbc_indirect_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xE1] is opcodes.sbc_indirect_x


def test_opcode_E1_sbc_indirect_x_subtracts_value_from_final_address():
    """Objective: E1 20 with X=0x04 uses pointer at $0024 and subtracts final memory value."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xE1)
    rom.write(0x0001, 0x20)
    bus.write(0x0024, 0x00)
    bus.write(0x0025, 0x02)
    bus.write(0x0200, 0x01)

    cpu.reset()
    cpu.a = 0x10
    cpu.x = 0x04
    cpu.flags.set_carry_flag(True)
    cpu.step()

    assert cpu.a == 0x0F
    assert cpu.pc == 0x8002
