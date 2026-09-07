"""
Test 055 - Connect ADC zero page (opcode $65) to CPU dispatch.

File to update:
    emulator/cpu/opcodes.py

Symbols to create/update:
    opcodes.adc_zero_page
    OPCODE_TABLE[$65]

Why this step exists:
Unlike immediate mode, `zero_page(cpu)` resolves the operand byte to an
address. The handler must read the value at that address before handing the
value to the existing `adc` instruction.

Complete example implementation:

    # emulator/cpu/opcodes.py
    def adc_zero_page(cpu):
        addr = zero_page(cpu)
        value = cpu.bus.read(addr)
        adc(cpu, value)

    OPCODE_TABLE = {
        # ...existing entries...
        0x65: adc_zero_page,
    }

Important invariants:
    - the one-byte operand is an address in $0000-$00FF
    - exactly one data value is read and passed to `adc`
    - PC advances by two bytes total
    - address resolution remains in the opcode layer

Common misconception:
Do not pass the zero-page address itself to `adc`; ADC adds the byte stored at
that address.

Out of scope:
    - indexed, absolute, and indirect ADC modes
    - changes to `zero_page` or `adc`
    - cycle accounting
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


def test_adc_zero_page_handler_exists_and_is_in_opcode_table():
    """Objective: create adc_zero_page(cpu) and add 0x65 to OPCODE_TABLE."""
    assert hasattr(opcodes, "adc_zero_page")
    assert callable(opcodes.adc_zero_page)
    assert list(inspect.signature(opcodes.adc_zero_page).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x65] is opcodes.adc_zero_page


def test_opcode_65_adc_zero_page_adds_value_from_memory():
    """Objective: 65 10 means ADC $10, so add RAM[$0010] to A."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x65)
    rom.write(0x0001, 0x10)
    bus.write(0x0010, 0x05)

    cpu.reset()
    cpu.a = 0x10
    cpu.flags.set_carry_flag(False)
    cpu.step()

    assert cpu.a == 0x15
    assert cpu.pc == 0x8002
