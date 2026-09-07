"""Lesson 129: add ORA absolute opcode ``0x0D``.

Why this step exists:
Absolute ORA extends the operation beyond zero page by decoding a full
little-endian address and reading its value before updating A and Z/N.

In this step, ``or_a`` and the immediate/zero-page handlers already exist, so
add exactly the following to ``emulator/cpu/opcodes.py``:

    def ora_absolute(cpu: CPU):
        addr = absolute(cpu)
        value = cpu.bus.read(addr)
        or_a(cpu, value)

    OPCODE_TABLE = {
        ...
        0x0D: ora_absolute,
    }

``emulator/cpu/addressing_modes.py::absolute`` obtains a little-endian word
through ``CPU.fetch_word``.  Therefore ``0D 00 02`` reads ``$0200`` and sends
that value to ``instructions.or_a``.  A and Z/N change; Carry/Overflow and
memory are invariant; opcode plus word advances PC three bytes.

Misconception: the operand word is an address, not an immediate value, and
its low byte comes first.  Out of scope: indexed absolute and indirect ORA
modes (lessons 130-133).
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


def test_ora_absolute_handler_exists_and_is_in_opcode_table():
    """Objective: create ora_absolute(cpu) and add 0x0D to OPCODE_TABLE."""
    assert hasattr(opcodes, "ora_absolute")
    assert callable(opcodes.ora_absolute)
    assert list(inspect.signature(opcodes.ora_absolute).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x0D] is opcodes.ora_absolute


def test_opcode_0D_ora_absolute_reads_memory_value():
    """Objective: 0D 00 02 means ORA value at RAM[$0200]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x0D)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0200, 0x0F)

    cpu.reset()
    cpu.a = 0xF0
    cpu.step()

    assert cpu.a == 0xFF
    assert cpu.pc == 0x8003
