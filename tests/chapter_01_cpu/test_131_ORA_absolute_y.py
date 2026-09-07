"""Lesson 131: add ORA absolute,Y opcode ``0x19``.

Why this step exists:
The Y-indexed absolute form gives ORA equivalent access through either index
register and continues to reuse the same addressing-independent primitive.

In this step, after lessons 125-130, ``or_a`` and the first five ORA modes
already exist.  Add exactly the following to ``emulator/cpu/opcodes.py``:

    def ora_absolute_y(cpu: CPU):
        addr = absolute_y(cpu)
        value = cpu.bus.read(addr)
        or_a(cpu, value)

    OPCODE_TABLE = {
        ...
        0x19: ora_absolute_y,
    }

``emulator/cpu/addressing_modes.py::absolute_y`` fetches the little-endian
base word and adds Y; the handler then reads that effective address and passes
the value to ``emulator/cpu/instructions.py::or_a``.  A and Z/N may change;
Carry/Overflow, memory, X, and Y are invariant, and opcode plus word advances
PC three bytes.

Misconception: Y indexes the decoded address, not either operand byte, and the
handler must read memory rather than OR the address itself.  Out of scope:
ORA (indirect,X)/(indirect),Y (lessons 132-133) and all EOR/BIT work (134-145).
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


def test_ora_absolute_y_handler_exists_and_is_in_opcode_table():
    """Objective: create ora_absolute_y(cpu) and add 0x19 to OPCODE_TABLE."""
    assert hasattr(opcodes, "ora_absolute_y")
    assert callable(opcodes.ora_absolute_y)
    assert list(inspect.signature(opcodes.ora_absolute_y).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x19] is opcodes.ora_absolute_y


def test_opcode_19_ora_absolute_y_reads_indexed_memory_value():
    """Objective: 19 00 02 with Y=0x04 reads RAM[$0204]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x19)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0204, 0x0F)

    cpu.reset()
    cpu.y = 0x04
    cpu.a = 0xF0
    cpu.step()

    assert cpu.a == 0xFF
    assert cpu.pc == 0x8003
