"""Lesson 133: add ORA (indirect),Y opcode ``0x11``.

Why this step exists:
This completes ORA's addressing forms by resolving a zero-page pointer and then
adding Y, without duplicating the operation's result or flag logic.

In this step, complete ORA after lessons 125-132 by adding the following to
``emulator/cpu/opcodes.py``:

    def ora_indirect_y(cpu: CPU):
        addr = indirect_y(cpu)
        value = cpu.bus.read(addr)
        or_a(cpu, value)

    OPCODE_TABLE = {
        ...
        0x11: ora_indirect_y,
    }

``emulator/cpu/addressing_modes.py::indirect_y`` fetches a zero-page pointer,
reads its little-endian target with a wrapping high-byte lookup, and only then
adds Y.  The handler reads that indexed target and calls ``instructions.or_a``.
A and Z/N may change; Carry/Overflow, memory, X, and Y are invariant; opcode
plus operand advances PC two bytes.

Misconception: unlike (indirect,X), Y does not select the pointer location; it
indexes the resolved target.  Out of scope: EOR and BIT (lessons 134-145).
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


def test_ora_indirect_y_handler_exists_and_is_in_opcode_table():
    """Objective: create ora_indirect_y(cpu) and add 0x11 to OPCODE_TABLE."""
    assert hasattr(opcodes, "ora_indirect_y")
    assert callable(opcodes.ora_indirect_y)
    assert list(inspect.signature(opcodes.ora_indirect_y).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x11] is opcodes.ora_indirect_y


def test_opcode_11_ora_indirect_y_reads_pointed_indexed_memory_value():
    """Objective: 11 20 reads pointer at $20/$21, then adds Y."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x11)
    rom.write(0x0001, 0x20)
    bus.write(0x0020, 0x00)
    bus.write(0x0021, 0x02)
    bus.write(0x0204, 0x0F)

    cpu.reset()
    cpu.y = 0x04
    cpu.a = 0xF0
    cpu.step()

    assert cpu.a == 0xFF
    assert cpu.pc == 0x8002
