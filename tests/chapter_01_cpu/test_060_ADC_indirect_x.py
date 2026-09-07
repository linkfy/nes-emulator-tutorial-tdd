"""
Test 060 - Connect ADC (indirect,X) (opcode $61) to CPU dispatch.

File to update:
    emulator/cpu/opcodes.py

Symbols to create/update:
    opcodes.adc_indirect_x
    OPCODE_TABLE[$61]

Why this step exists:
`indirect_x` first adds X to the zero-page operand, reads a little-endian
pointer from page zero, and returns the final effective address. The handler
must then read the ADC value from that final address.

Complete example implementation:

    # emulator/cpu/opcodes.py
    def adc_indirect_x(cpu):
        addr = indirect_x(cpu)
        value = cpu.bus.read(addr)
        adc(cpu, value)

    OPCODE_TABLE = {
        # ...existing entries...
        0x61: adc_indirect_x,
    }

Important invariants:
    - X indexes the zero-page pointer location before dereferencing
    - pointer-byte reads wrap within page zero
    - the pointer target is an address, so the handler performs the final read
    - PC advances by two bytes total

Common misconception:
Do not add X to the final 16-bit target. That describes a different operation;
for (indirect,X), X selects the zero-page pointer before it is dereferenced.

Out of scope:
    - ADC (indirect),Y, introduced by the next numbered test
    - cycle accounting
    - changes to `indirect_x` or `adc`
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


def test_adc_indirect_x_handler_exists_and_is_in_opcode_table():
    """Objective: create adc_indirect_x(cpu) and add 0x61 to OPCODE_TABLE."""
    assert hasattr(opcodes, "adc_indirect_x")
    assert callable(opcodes.adc_indirect_x)
    assert list(inspect.signature(opcodes.adc_indirect_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x61] is opcodes.adc_indirect_x


def test_opcode_61_adc_indirect_x_adds_value_from_final_address():
    """Objective: 61 20 with X=0x04 uses pointer at $0024 and adds final memory value."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x61)
    rom.write(0x0001, 0x20)
    bus.write(0x0024, 0x00)
    bus.write(0x0025, 0x02)
    bus.write(0x0200, 0x05)

    cpu.reset()
    cpu.a = 0x10
    cpu.x = 0x04
    cpu.flags.set_carry_flag(False)
    cpu.step()

    assert cpu.a == 0x15
    assert cpu.pc == 0x8002
