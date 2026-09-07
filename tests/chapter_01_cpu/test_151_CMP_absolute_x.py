"""Lesson 151: add CMP absolute,X opcode ``0xDD``.

Why this step exists:
Absolute,X lets CMP compare A with indexed tables outside zero page while
keeping address calculation separate from comparison semantics.

In this step, lessons 146-150 already provide ``cmp``, its opcode import, and
the earlier CMP modes.  Add the following to ``emulator/cpu/opcodes.py``:

    def cmp_absolute_x(cpu: CPU):
        addr = absolute_x(cpu)
        value = cpu.bus.read(addr)
        cmp(cpu, value)

    OPCODE_TABLE = {
        ...
        0xDD: cmp_absolute_x,
    }

``emulator/cpu/addressing_modes.py::absolute_x`` fetches the little-endian
base word and adds X; the handler reads that effective address and compares
its value with A.  Only C/Z/N change; A, X, memory, and Overflow are invariant,
and opcode plus word advances PC three bytes.

Misconception: X indexes the decoded address, not either operand byte, and is
not itself modified.  Out of scope: CMP absolute,Y and indirect modes
(lessons 152-154), plus CPX/CPY work in lessons 155-162.
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


def test_cmp_absolute_x_handler_exists_and_is_in_opcode_table():
    """Objective: create cmp_absolute_x(cpu) and add 0xDD to OPCODE_TABLE."""
    assert hasattr(opcodes, "cmp_absolute_x")
    assert callable(opcodes.cmp_absolute_x)
    assert list(inspect.signature(opcodes.cmp_absolute_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xDD] is opcodes.cmp_absolute_x


def test_opcode_DD_cmp_absolute_x_reads_indexed_memory_value():
    """Objective: DD 00 02 with X=0x04 compares A with RAM[$0204]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xDD)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0204, 0x10)

    cpu.reset()
    cpu.x = 0x04
    cpu.a = 0x20
    cpu.step()

    assert (cpu.p & CARRY_FLAG) != 0
    assert cpu.pc == 0x8003
