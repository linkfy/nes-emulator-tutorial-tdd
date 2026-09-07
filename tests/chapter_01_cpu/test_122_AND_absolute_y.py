"""Lesson 122: add AND absolute,Y opcode ``0x39``.

Why this step exists:
This supplies the Y-indexed counterpart to absolute,X so AND can use either
index register without duplicating its accumulator and flag semantics.

In this step, following absolute,X in lesson 121, add only this handler and
registration to ``emulator/cpu/opcodes.py``:

    def and_absolute_y(cpu: CPU):
        addr = absolute_y(cpu)
        value = cpu.bus.read(addr)
        and_a(cpu, value)

    OPCODE_TABLE = {
        ...
        0x39: and_absolute_y,
    }

``emulator/cpu/addressing_modes.py::absolute_y`` fetches the little-endian
base word before adding ``cpu.y``.  The resolved memory value feeds the
already-existing ``instructions.and_a``; A and Z/N change, while Y,
Carry/Overflow, and memory remain invariant.  The opcode and word consume
three bytes.

Misconception: absolute,Y is not zero-page,Y and does not constrain indexing
to page zero.  Out of scope: AND (indirect,X)/(indirect),Y (lessons 123-124)
and the ORA/EOR/BIT additions in lessons 125-145.
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


def test_and_absolute_y_handler_exists_and_is_in_opcode_table():
    """Objective: create and_absolute_y(cpu) and add 0x39 to OPCODE_TABLE."""
    assert hasattr(opcodes, "and_absolute_y")
    assert callable(opcodes.and_absolute_y)
    assert list(inspect.signature(opcodes.and_absolute_y).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x39] is opcodes.and_absolute_y


def test_opcode_39_and_absolute_y_reads_indexed_memory_value():
    """Objective: 39 00 02 with Y=0x04 reads RAM[$0204]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x39)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0204, 0x0F)

    cpu.reset()
    cpu.y = 0x04
    cpu.a = 0xF3
    cpu.step()

    assert cpu.a == 0x03
    assert cpu.pc == 0x8003
