"""
Test 093 - Add ASL Absolute.

In this step, extend memory ASL to the existing 16-bit absolute resolver.

File and symbols:
    emulator/cpu/opcodes.py: asl_absolute, OPCODE_TABLE[0x0E]

Why this step exists:
This transition extends the same memory ASL behavior from zero-page addresses to
the existing 16-bit `absolute` resolver; instruction semantics remain unchanged.

Suggested implementation for this step:

    # emulator/cpu/opcodes.py
    def asl_absolute(cpu: CPU):
        addr = absolute(cpu)
        asl(cpu, addr)

    OPCODE_TABLE = {
        # existing entries unchanged
        0x0E: asl_absolute,
    }

Important invariants:
    - `absolute(cpu)` consumes low byte then high byte and returns a 16-bit address
    - the three-byte instruction advances PC by three including the opcode
    - `asl` reads and writes the resolved memory location and updates C, Z, and N
    - A and X are unchanged

Common misconception:
For `0E 00 02`, little-endian decoding targets $0200, not $0002.

Out of scope:
    - ASL Absolute,X in Test 094
    - changes to absolute addressing or ASL semantics
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


def test_asl_absolute_handler_exists_and_is_in_opcode_table():
    """Objective: create asl_absolute(cpu) and add 0x0E to OPCODE_TABLE."""
    assert hasattr(opcodes, "asl_absolute")
    assert callable(opcodes.asl_absolute)
    assert list(inspect.signature(opcodes.asl_absolute).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x0E] is opcodes.asl_absolute


def test_opcode_0E_asl_absolute_shifts_memory_value():
    """Objective: 0E 00 02 means ASL $0200, so RAM[$0200] is shifted."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x0E)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0200, 0b0000_0011)

    cpu.reset()
    cpu.step()

    assert bus.read(0x0200) == 0b0000_0110
    assert cpu.pc == 0x8003
