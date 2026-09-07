"""Lesson 130: add ORA absolute,X opcode ``0x1D``.

Why this step exists:
This permits ORA against full-address tables indexed by X while keeping address
resolution separate from the operation's accumulator and flag semantics.

In this step, following unindexed absolute ORA in lesson 129, add only this
code to ``emulator/cpu/opcodes.py``:

    def ora_absolute_x(cpu: CPU):
        addr = absolute_x(cpu)
        value = cpu.bus.read(addr)
        or_a(cpu, value)

    OPCODE_TABLE = {
        ...
        0x1D: ora_absolute_x,
    }

``emulator/cpu/addressing_modes.py::absolute_x`` fetches the little-endian
base word before adding ``cpu.x``.  The handler reads that resolved address
and passes its value to ``instructions.or_a``.  A and Z/N change; X,
Carry/Overflow, and memory are invariant; opcode plus word advances PC three
bytes.

Misconception: X indexes the decoded address, not an operand byte or the data
read from memory.  Out of scope: ORA absolute,Y and indirect modes (lessons
131-133), followed by EOR and BIT in lessons 134-145.
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


def test_ora_absolute_x_handler_exists_and_is_in_opcode_table():
    """Objective: create ora_absolute_x(cpu) and add 0x1D to OPCODE_TABLE."""
    assert hasattr(opcodes, "ora_absolute_x")
    assert callable(opcodes.ora_absolute_x)
    assert list(inspect.signature(opcodes.ora_absolute_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x1D] is opcodes.ora_absolute_x


def test_opcode_1D_ora_absolute_x_reads_indexed_memory_value():
    """Objective: 1D 00 02 with X=0x04 reads RAM[$0204]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x1D)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0204, 0x0F)

    cpu.reset()
    cpu.x = 0x04
    cpu.a = 0xF0
    cpu.step()

    assert cpu.a == 0xFF
    assert cpu.pc == 0x8003
