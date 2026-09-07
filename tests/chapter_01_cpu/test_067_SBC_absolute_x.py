"""
Test 067 - Add SBC Absolute,X.

File to update:
    emulator/cpu/opcodes.py

Symbols to add/update:
    opcodes.sbc_absolute_x and OPCODE_TABLE[0xFD]

Why this step exists:
SBC gains X-indexed absolute access by reusing the existing `absolute_x` resolver;
the opcode wrapper remains responsible only for reading and delegating.

Complete example implementation:

    # emulator/cpu/opcodes.py
    def sbc_absolute_x(cpu: CPU):
        addr = absolute_x(cpu)
        value = cpu.bus.read(addr)
        sbc(cpu, value)

    OPCODE_TABLE = {
        # ... existing entries ...
        0xFD: sbc_absolute_x,
    }

Important invariants:
    - `absolute_x` consumes two operand bytes and adds X to the base address
    - the handler reads the byte at the final indexed address
    - the read value is passed once to `sbc`
    - executing the three-byte instruction advances PC by three bytes

Common misconception:
Do not add X again in the wrapper; `absolute_x` already returns the final indexed
address.

Out of scope:
    - Absolute,Y and indirect SBC wrappers
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


def test_sbc_absolute_x_handler_exists_and_is_in_opcode_table():
    """Objective: create sbc_absolute_x(cpu) and add 0xFD to OPCODE_TABLE."""
    assert hasattr(opcodes, "sbc_absolute_x")
    assert callable(opcodes.sbc_absolute_x)
    assert list(inspect.signature(opcodes.sbc_absolute_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xFD] is opcodes.sbc_absolute_x


def test_opcode_FD_sbc_absolute_x_subtracts_indexed_value():
    """Objective: FD 00 02 with X=0x04 subtracts RAM[$0204] from A."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xFD)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0204, 0x01)

    cpu.reset()
    cpu.a = 0x10
    cpu.x = 0x04
    cpu.flags.set_carry_flag(True)
    cpu.step()

    assert cpu.a == 0x0F
    assert cpu.pc == 0x8003
