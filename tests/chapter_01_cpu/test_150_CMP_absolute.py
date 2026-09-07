"""Lesson 150: add CMP absolute opcode ``0xCD``.

Why this step exists:
Absolute CMP allows A to be compared with a byte anywhere in CPU memory while
keeping little-endian effective-address decoding separate from flag semantics.

In this step, lessons 146-149 already provide CMP semantics, import, and
immediate/zero-page modes.  Add exactly the following to
``emulator/cpu/opcodes.py``:

    def cmp_absolute(cpu: CPU):
        addr = absolute(cpu)
        value = cpu.bus.read(addr)
        cmp(cpu, value)

    OPCODE_TABLE = {
        ...
        0xCD: cmp_absolute,
    }

``emulator/cpu/addressing_modes.py::absolute`` obtains a little-endian word
through ``CPU.fetch_word``; ``CD 00 02`` therefore compares A with the value
read at ``$0200``.  C/Z/N may change; A, Overflow, X, Y, and memory remain
invariant; opcode plus word advances PC three bytes.

Misconception: the operand word is an address, not an immediate comparison
value, and its bytes are not big-endian.  Out of scope: CMP absolute,X,
absolute,Y, (indirect,X), and (indirect),Y are lessons 151-154; CPX/CPY follow.
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


def test_cmp_absolute_handler_exists_and_is_in_opcode_table():
    """Objective: create cmp_absolute(cpu) and add 0xCD to OPCODE_TABLE."""
    assert hasattr(opcodes, "cmp_absolute")
    assert callable(opcodes.cmp_absolute)
    assert list(inspect.signature(opcodes.cmp_absolute).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xCD] is opcodes.cmp_absolute


def test_opcode_CD_cmp_absolute_reads_memory_value():
    """Objective: CD 00 02 means compare A with RAM[$0200]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xCD)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0200, 0x10)

    cpu.reset()
    cpu.a = 0x20
    cpu.step()

    assert (cpu.p & CARRY_FLAG) != 0
    assert cpu.pc == 0x8003
