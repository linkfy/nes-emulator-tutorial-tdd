"""
Test 031 - Add LDX immediate ($A2).

File to update:
    emulator/cpu/opcodes.py

Locations:
    opcodes import of ldx
    opcodes.ldx_immediate
    opcodes.OPCODE_TABLE[$A2]

Why this step exists:
Test 030 introduced the value-level `ldx` instruction. This lesson connects its
first machine-code encoding by fetching the literal operand and delegating register
and flag behavior to that existing instruction.

Complete example implementation:

    # emulator/cpu/opcodes.py
    from emulator.cpu.instructions import lda, sta, ldx


    def ldx_immediate(cpu: CPU):
        ldx(cpu, immediate(cpu))


    OPCODE_TABLE = {
        # Preserve existing entries.
        0xA2: ldx_immediate,
    }

Important invariants:
    - $A2 maps to ldx_immediate
    - immediate fetches exactly one byte, so the full instruction advances PC by two
    - the operand byte itself is loaded into X; it is not used as an address
    - `ldx` remains responsible for updating Zero and Negative

Common misconception:
Do not read memory at the operand's numeric value. `A2 42` loads $42 itself into X.

Out of scope:
    - zero-page, zero-page,Y, and absolute LDX encodings
    - changes to immediate or ldx
    - cycle timing
"""
import inspect

from emulator.bus.cpu_bus import CpuBus
from emulator.cpu import opcodes
from emulator.cpu.cpu import CPU
from emulator.memory.fake_rom import FakeROM
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG


def make_cpu_with_rom():
    rom = FakeROM()
    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)
    bus = CpuBus(program_rom=rom)
    return CPU(bus), bus, rom


def test_ldx_immediate_handler_exists_and_is_in_opcode_table():
    """Objective: create ldx_immediate(cpu) and add 0xA2 to OPCODE_TABLE."""
    assert hasattr(opcodes, "ldx_immediate")
    assert callable(opcodes.ldx_immediate)
    assert list(inspect.signature(opcodes.ldx_immediate).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xA2] is opcodes.ldx_immediate


def test_opcode_A2_ldx_immediate_loads_register_x():
    """Objective: A2 42 means LDX #$42, so X becomes 0x42."""
    cpu, _, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xA2)
    rom.write(0x0001, 0x42)

    cpu.reset()
    cpu.step()

    assert cpu.x == 0x42
    assert cpu.pc == 0x8002


def test_opcode_A2_ldx_immediate_updates_flags():
    """Objective: LDX Immediate updates Zero and Negative flags."""
    cpu, _, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xA2)
    rom.write(0x0001, 0x80)

    cpu.reset()
    cpu.step()

    assert cpu.x == 0x80
    assert (cpu.p & ZERO_FLAG) == 0
    assert (cpu.p & NEGATIVE_FLAG) != 0
