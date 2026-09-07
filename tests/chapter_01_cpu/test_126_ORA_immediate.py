"""Lesson 126: expose ORA immediate as opcode ``0x09``.

Why this step exists:
The immediate opcode exposes ORA to CPU execution with a literal byte and
checks that decoding delegates result and flag handling to the shared primitive.

In this step, after lesson 125 creates ``or_a``, make these additions in
``emulator/cpu/opcodes.py``:

    from emulator.cpu.instructions import (..., and_a, or_a)

    def ora_immediate(cpu: CPU):
        or_a(cpu, immediate(cpu))

    OPCODE_TABLE = {
        ...
        0x09: ora_immediate,
    }

``emulator/cpu/addressing_modes.py::immediate`` returns the byte fetched by
``CPU.fetch_byte`` directly.  ``instructions.or_a`` stores A | value and
changes only Z/N; Carry/Overflow and memory remain invariant, and opcode plus
operand advances PC two bytes.

Misconception: the immediate byte is the value, so reading it again through
``cpu.bus`` would wrongly treat it as an address.  Out of scope: memory-based
ORA handlers (lessons 127-133) and the EOR/BIT imports and handlers in lessons
134-145.
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


def test_ora_immediate_handler_exists_and_is_in_opcode_table():
    """Objective: create ora_immediate(cpu) and add 0x09 to OPCODE_TABLE."""
    assert hasattr(opcodes, "ora_immediate")
    assert callable(opcodes.ora_immediate)
    assert list(inspect.signature(opcodes.ora_immediate).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x09] is opcodes.ora_immediate


def test_opcode_09_ora_immediate_updates_accumulator():
    """Objective: 09 0F means ORA #$0F, so A becomes A | 0x0F."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x09)
    rom.write(0x0001, 0x0F)

    cpu.reset()
    cpu.a = 0xF0
    cpu.step()

    assert cpu.a == 0xFF
    assert cpu.pc == 0x8002


def test_opcode_09_ora_immediate_updates_zero_flag():
    """Objective: result 0 sets Zero flag."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x09)
    rom.write(0x0001, 0x00)

    cpu.reset()
    cpu.a = 0x00
    cpu.step()

    assert cpu.a == 0x00
    assert (cpu.p & ZERO_FLAG) != 0
    assert (cpu.p & NEGATIVE_FLAG) == 0


def test_opcode_09_ora_immediate_updates_negative_flag():
    """Objective: result bit 7 sets Negative flag."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x09)
    rom.write(0x0001, 0x80)

    cpu.reset()
    cpu.a = 0x01
    cpu.step()

    assert cpu.a == 0x81
    assert (cpu.p & NEGATIVE_FLAG) != 0
    assert (cpu.p & ZERO_FLAG) == 0
