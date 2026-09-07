"""
Test 054 - Connect ADC immediate (opcode $69) to CPU dispatch.

File to update:
    emulator/cpu/opcodes.py

Symbols to create/update:
    opcodes.adc_immediate
    OPCODE_TABLE[$69]
    the `adc` instruction import

Why this step exists:
Test 053 supplied arithmetic on an already-resolved value. Immediate mode
supplies the next program byte itself, so this handler passes the return value
of `immediate(cpu)` directly to `adc`.

Complete example implementation:

    # emulator/cpu/opcodes.py
    from emulator.cpu.instructions import ..., adc

    def adc_immediate(cpu):
        value = immediate(cpu)
        adc(cpu, value)

    OPCODE_TABLE = {
        # ...existing entries...
        0x69: adc_immediate,
    }

Important invariants:
    - the handler accepts only `cpu`
    - immediate mode consumes exactly one operand byte
    - PC advances by two bytes total: opcode plus operand
    - the handler delegates all arithmetic and flag changes to `adc`

Common misconception:
Do not treat the immediate byte as an address and read the bus a second time;
`immediate(cpu)` already returns the operand value.

Out of scope:
    - all memory-addressed ADC opcodes
    - changes to `adc` or the addressing helpers
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


def test_adc_immediate_handler_exists_and_is_in_opcode_table():
    """
    Objective:
    Create adc_immediate(cpu) and add 0x69 to OPCODE_TABLE.

    Important:
    immediate(cpu) returns the value directly.
    Do not read from cpu.bus again for immediate mode.
    """
    assert hasattr(opcodes, "adc_immediate")
    assert callable(opcodes.adc_immediate)
    assert list(inspect.signature(opcodes.adc_immediate).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x69] is opcodes.adc_immediate


def test_opcode_69_adc_immediate_adds_value_to_register_a():
    """Objective: 69 05 means ADC #$05, so A = A + 0x05 + Carry."""
    cpu, _, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x69)
    rom.write(0x0001, 0x05)

    cpu.reset()
    cpu.a = 0x10
    cpu.flags.set_carry_flag(False)
    cpu.step()

    assert cpu.a == 0x15
    assert cpu.pc == 0x8002


def test_opcode_69_adc_immediate_uses_carry_flag():
    """Objective: ADC includes the old Carry flag in the addition."""
    cpu, _, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x69)
    rom.write(0x0001, 0x05)

    cpu.reset()
    cpu.a = 0x10
    cpu.flags.set_carry_flag(True)
    cpu.step()

    assert cpu.a == 0x16
    assert cpu.pc == 0x8002
