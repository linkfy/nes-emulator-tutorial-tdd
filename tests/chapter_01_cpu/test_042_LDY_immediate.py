"""
Test 042 - Add LDY immediate ($A0).

File to update:
    emulator/cpu/opcodes.py

Locations:
    opcodes import of ldy
    opcodes.ldy_immediate
    opcodes.OPCODE_TABLE[$A0]

Why this step exists:
The core `ldy` instruction already owns the register and flag behavior. This lesson
connects its first encoding by fetching one literal operand and passing that value to
`ldy`.

Complete example implementation:

    # emulator/cpu/opcodes.py
    from emulator.cpu.addressing_modes import immediate
    from emulator.cpu.instructions import ldy


    def ldy_immediate(cpu: CPU):
        ldy(cpu, immediate(cpu))


    OPCODE_TABLE = {
        # Preserve existing entries.
        0xA0: ldy_immediate,
    }

Important invariants:
    - $A0 maps to ldy_immediate
    - immediate fetches exactly one operand byte, advancing PC by one after the opcode
    - the operand itself is loaded; it is not treated as a memory address
    - `ldy` remains responsible for updating Zero and Negative

Common misconception:
Do not read the bus at the immediate byte's numeric value. For `A0 42`, Y receives
$42 directly.

Out of scope:
    - LDY zero-page, indexed, and absolute encodings
    - STY opcode handlers
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


def test_ldy_immediate_handler_exists_and_is_in_opcode_table():
    """Objective: create ldy_immediate(cpu) and add 0xA0 to OPCODE_TABLE."""
    assert hasattr(opcodes, "ldy_immediate")
    assert callable(opcodes.ldy_immediate)
    assert list(inspect.signature(opcodes.ldy_immediate).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xA0] is opcodes.ldy_immediate


def test_opcode_A0_ldy_immediate_loads_register_y():
    """Objective: A0 42 means LDY #$42, so Y becomes 0x42."""
    cpu, _, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xA0)
    rom.write(0x0001, 0x42)

    cpu.reset()
    cpu.step()

    assert cpu.y == 0x42
    assert cpu.pc == 0x8002


def test_opcode_A0_ldy_immediate_updates_flags():
    """Objective: LDY Immediate updates Zero and Negative flags."""
    cpu, _, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xA0)
    rom.write(0x0001, 0x80)

    cpu.reset()
    cpu.step()

    assert cpu.y == 0x80
    assert (cpu.p & ZERO_FLAG) == 0
    assert (cpu.p & NEGATIVE_FLAG) != 0
