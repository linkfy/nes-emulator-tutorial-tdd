"""Lesson 120: add AND absolute opcode ``0x2D``.

In this step, use ``and_a``, its opcode import, and the simpler modes from
lessons 116-119, then add only the absolute handler and table entry.

Why this step exists:
Absolute mode lets AND read from the full CPU address space and verifies the
separation between little-endian address decoding and logical operation.

Suggested implementation in ``emulator/cpu/opcodes.py``:

    def and_absolute(cpu: CPU):
        addr = absolute(cpu)
        value = cpu.bus.read(addr)
        and_a(cpu, value)

    OPCODE_TABLE = {
        ...
        0x2D: and_absolute,
    }

``emulator/cpu/addressing_modes.py::absolute`` obtains a little-endian word
through ``CPU.fetch_word``.  Therefore ``2D 00 02`` reads the value at
``$0200`` and passes it to ``instructions.and_a``.  A and Z/N change;
Carry/Overflow and memory are invariant; opcode plus word advances PC three
bytes.

Misconception: the operand word is an address, not the value, and its bytes
are not big-endian.  Out of scope later work: AND absolute,X, absolute,Y,
(indirect,X), and (indirect),Y are lessons 121-124; ORA/EOR/BIT are 125-145.
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


def test_and_absolute_handler_exists_and_is_in_opcode_table():
    """Objective: create and_absolute(cpu) and add 0x2D to OPCODE_TABLE."""
    assert hasattr(opcodes, "and_absolute")
    assert callable(opcodes.and_absolute)
    assert list(inspect.signature(opcodes.and_absolute).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x2D] is opcodes.and_absolute


def test_opcode_2D_and_absolute_reads_memory_value():
    """Objective: 2D 00 02 means AND value at RAM[$0200]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x2D)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0200, 0x0F)

    cpu.reset()
    cpu.a = 0xF3
    cpu.step()

    assert cpu.a == 0x03
    assert cpu.pc == 0x8003
