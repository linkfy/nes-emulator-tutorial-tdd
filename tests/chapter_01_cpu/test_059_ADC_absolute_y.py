"""
Test 059 - Connect ADC absolute,Y (opcode $79) to CPU dispatch.

File to update:
    emulator/cpu/opcodes.py

Symbols to create/update:
    opcodes.adc_absolute_y
    OPCODE_TABLE[$79]

Why this step exists:
This is the Y-indexed counterpart to test 058. `absolute_y` consumes the
two-byte base address and applies Y; the handler reads the resulting location
and delegates the value to `adc`.

Complete example implementation:

    # emulator/cpu/opcodes.py
    def adc_absolute_y(cpu):
        addr = absolute_y(cpu)
        value = cpu.bus.read(addr)
        adc(cpu, value)

    OPCODE_TABLE = {
        # ...existing entries...
        0x79: adc_absolute_y,
    }

Important invariants:
    - Y is applied exactly once by `absolute_y`
    - the effective address is not constrained to page zero
    - PC advances by three bytes total
    - the addressed value is passed to `adc`

Common misconception:
Do not copy the absolute,X handler and leave it using X; opcode $79 indexes the
base address with Y.

Out of scope:
    - indirect ADC modes
    - page-crossing timing penalties
    - changes to the addressing or arithmetic helpers
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


def test_adc_absolute_y_handler_exists_and_is_in_opcode_table():
    """Objective: create adc_absolute_y(cpu) and add 0x79 to OPCODE_TABLE."""
    assert hasattr(opcodes, "adc_absolute_y")
    assert callable(opcodes.adc_absolute_y)
    assert list(inspect.signature(opcodes.adc_absolute_y).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x79] is opcodes.adc_absolute_y


def test_opcode_79_adc_absolute_y_adds_indexed_value():
    """Objective: 79 00 02 with Y=0x04 adds RAM[$0204] to A."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x79)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0204, 0x05)

    cpu.reset()
    cpu.a = 0x10
    cpu.y = 0x04
    cpu.flags.set_carry_flag(False)
    cpu.step()

    assert cpu.a == 0x15
    assert cpu.pc == 0x8003
