"""Lesson 158: add CPX absolute opcode ``0xEC``.

Why this step exists:
Absolute CPX extends the comparison to a byte anywhere in CPU memory while
keeping little-endian address decoding outside the CPX primitive.

In this step, complete CPX by adding exactly the following to
``emulator/cpu/opcodes.py``:

    def cpx_absolute(cpu: CPU):
        addr = absolute(cpu)
        value = cpu.bus.read(addr)
        cpx(cpu, value)

    OPCODE_TABLE = {
        ...
        0xEC: cpx_absolute,
    }

``emulator/cpu/addressing_modes.py::absolute`` obtains a little-endian word
through ``CPU.fetch_word``; ``EC 00 02`` therefore compares X with the value
at ``$0200``.  Only C/Z/N change; X, memory, and Overflow are invariant, and
opcode plus word advances PC three bytes.

Misconception: the operand word is an address, not a 16-bit compared value.
Out of scope: the CPY instruction and its three opcodes (lessons 159-162).
"""
import inspect

from emulator.bus.cpu_bus import CpuBus
from emulator.cpu import opcodes
from emulator.cpu.cpu import CPU
from emulator.memory.fake_rom import FakeROM


CARRY_FLAG = 1 << 0


def make_cpu_with_rom():
    rom = FakeROM()
    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)
    bus = CpuBus(program_rom=rom)
    return CPU(bus), bus, rom


def test_cpx_absolute_handler_exists_and_is_in_opcode_table():
    """Objective: create cpx_absolute(cpu) and add 0xEC to OPCODE_TABLE."""
    assert hasattr(opcodes, "cpx_absolute")
    assert callable(opcodes.cpx_absolute)
    assert list(inspect.signature(opcodes.cpx_absolute).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xEC] is opcodes.cpx_absolute


def test_opcode_EC_cpx_absolute_reads_memory_value():
    """Objective: EC 00 02 means compare X with RAM[$0200]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xEC)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0200, 0x10)

    cpu.reset()
    cpu.x = 0x20
    cpu.step()

    assert (cpu.p & CARRY_FLAG) != 0
    assert cpu.pc == 0x8003
