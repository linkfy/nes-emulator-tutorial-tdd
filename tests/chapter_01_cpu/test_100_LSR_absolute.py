"""
Test 100 - Add LSR Absolute.

In this step, expose memory LSR through the existing 16-bit absolute resolver.

File and symbols:
    emulator/cpu/opcodes.py: lsr_absolute, OPCODE_TABLE[0x4E]

Why this step exists:
After the zero-page forms, this transition exposes memory LSR through the existing
16-bit `absolute` resolver while retaining the instruction-layer implementation.

Suggested implementation for this step:

    # emulator/cpu/opcodes.py
    def lsr_absolute(cpu: CPU):
        addr = absolute(cpu)
        lsr(cpu, addr)

    OPCODE_TABLE = {
        # existing entries unchanged
        0x4E: lsr_absolute,
    }

Important invariants:
    - `absolute(cpu)` decodes low byte then high byte
    - two operand bytes make this a three-byte instruction
    - `lsr` reads and writes the effective address and replaces C/Z/N
    - A and index registers remain unchanged

Common misconception:
For `4E 00 02`, the little-endian target is $0200, not $0002.

Out of scope:
    - LSR Absolute,X in Test 101
    - changes to absolute addressing or LSR behavior
    - cycle timing and page-cross behavior
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


def test_lsr_absolute_handler_exists_and_is_in_opcode_table():
    """Objective: create lsr_absolute(cpu) and add 0x4E to OPCODE_TABLE."""
    assert hasattr(opcodes, "lsr_absolute")
    assert callable(opcodes.lsr_absolute)
    assert list(inspect.signature(opcodes.lsr_absolute).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x4E] is opcodes.lsr_absolute


def test_opcode_4E_lsr_absolute_shifts_memory_value():
    """Objective: 4E 00 02 means LSR $0200, so RAM[$0200] is shifted."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x4E)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0200, 0b0000_0110)

    cpu.reset()
    cpu.step()

    assert bus.read(0x0200) == 0b0000_0011
    assert cpu.pc == 0x8003
