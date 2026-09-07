"""
Test 057 - Connect ADC absolute (opcode $6D) to CPU dispatch.

File to update:
    emulator/cpu/opcodes.py

Symbols to create/update:
    opcodes.adc_absolute
    OPCODE_TABLE[$6D]

Why this step exists:
Absolute mode expands ADC to a little-endian 16-bit operand address. The
existing `absolute` helper consumes that word; the opcode handler reads the
addressed byte and delegates arithmetic to `adc`.

Complete example implementation:

    # emulator/cpu/opcodes.py
    def adc_absolute(cpu):
        addr = absolute(cpu)
        value = cpu.bus.read(addr)
        adc(cpu, value)

    OPCODE_TABLE = {
        # ...existing entries...
        0x6D: adc_absolute,
    }

Important invariants:
    - `absolute` combines the low operand byte before the high operand byte
    - the handler reads from the resulting 16-bit address
    - PC advances by three bytes total
    - `adc` remains the sole owner of arithmetic and flag behavior

Common misconception:
Do not pass the fetched 16-bit address to `adc`; first read the byte stored at
that address.

Out of scope:
    - absolute,X and absolute,Y ADC modes
    - page-crossing timing
    - changes to `absolute` or `adc`
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


def test_adc_absolute_handler_exists_and_is_in_opcode_table():
    """Objective: create adc_absolute(cpu) and add 0x6D to OPCODE_TABLE."""
    assert hasattr(opcodes, "adc_absolute")
    assert callable(opcodes.adc_absolute)
    assert list(inspect.signature(opcodes.adc_absolute).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x6D] is opcodes.adc_absolute


def test_opcode_6D_adc_absolute_adds_value_from_memory():
    """Objective: 6D 00 02 means ADC $0200, so add RAM[$0200] to A."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x6D)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0200, 0x05)

    cpu.reset()
    cpu.a = 0x10
    cpu.flags.set_carry_flag(False)
    cpu.step()

    assert cpu.a == 0x15
    assert cpu.pc == 0x8003
