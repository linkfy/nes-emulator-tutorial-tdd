"""
Test 058 - Connect ADC absolute,X (opcode $7D) to CPU dispatch.

File to update:
    emulator/cpu/opcodes.py

Symbols to create/update:
    opcodes.adc_absolute_x
    OPCODE_TABLE[$7D]

Why this step exists:
The existing `absolute_x` helper consumes the little-endian base address and
adds X. This handler reads the byte at that effective address and reuses the ADC
instruction implemented in test 053.

Complete example implementation:

    # emulator/cpu/opcodes.py
    def adc_absolute_x(cpu):
        addr = absolute_x(cpu)
        value = cpu.bus.read(addr)
        adc(cpu, value)

    OPCODE_TABLE = {
        # ...existing entries...
        0x7D: adc_absolute_x,
    }

Important invariants:
    - X is applied exactly once by `absolute_x`
    - the effective address is not constrained to page zero
    - PC advances by three bytes total
    - the addressed value is passed to `adc`

Common misconception:
Do not apply zero-page wrapping to an absolute indexed address; this mode may
cross into the next page.

Out of scope:
    - absolute,Y and indirect ADC modes
    - page-crossing timing penalties
    - 16-bit address wrapping policy beyond the existing helper
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


def test_adc_absolute_x_handler_exists_and_is_in_opcode_table():
    """Objective: create adc_absolute_x(cpu) and add 0x7D to OPCODE_TABLE."""
    assert hasattr(opcodes, "adc_absolute_x")
    assert callable(opcodes.adc_absolute_x)
    assert list(inspect.signature(opcodes.adc_absolute_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x7D] is opcodes.adc_absolute_x


def test_opcode_7D_adc_absolute_x_adds_indexed_value():
    """Objective: 7D 00 02 with X=0x04 adds RAM[$0204] to A."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x7D)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0204, 0x05)

    cpu.reset()
    cpu.a = 0x10
    cpu.x = 0x04
    cpu.flags.set_carry_flag(False)
    cpu.step()

    assert cpu.a == 0x15
    assert cpu.pc == 0x8003
