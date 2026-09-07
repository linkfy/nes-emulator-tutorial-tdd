"""Lesson 152: add CMP absolute,Y opcode ``0xD9``.

Why this step exists:
Absolute,Y provides the corresponding indexed comparison through Y while
reusing the shared CMP behavior.

In this step, lesson 151 has already added absolute,X.  Add exactly the
following to ``emulator/cpu/opcodes.py``:

    def cmp_absolute_y(cpu: CPU):
        addr = absolute_y(cpu)
        value = cpu.bus.read(addr)
        cmp(cpu, value)

    OPCODE_TABLE = {
        ...
        0xD9: cmp_absolute_y,
    }

``emulator/cpu/addressing_modes.py::absolute_y`` fetches the little-endian
base word and adds Y before the bus read.  ``instructions.cmp`` changes only
C/Z/N; A, Y, memory, and Overflow remain invariant, while opcode plus word
advances PC three bytes.

Misconception: Y modifies the effective address, not the fetched value, and
the base bytes are not big-endian.  Out of scope: CMP indirect,X and
indirect,Y (153-154), then CPX/CPY (155-162).
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


def test_cmp_absolute_y_handler_exists_and_is_in_opcode_table():
    """Objective: create cmp_absolute_y(cpu) and add 0xD9 to OPCODE_TABLE."""
    assert hasattr(opcodes, "cmp_absolute_y")
    assert callable(opcodes.cmp_absolute_y)
    assert list(inspect.signature(opcodes.cmp_absolute_y).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xD9] is opcodes.cmp_absolute_y


def test_opcode_D9_cmp_absolute_y_reads_indexed_memory_value():
    """Objective: D9 00 02 with Y=0x04 compares A with RAM[$0204]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xD9)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0204, 0x10)

    cpu.reset()
    cpu.y = 0x04
    cpu.a = 0x20
    cpu.step()

    assert (cpu.p & CARRY_FLAG) != 0
    assert cpu.pc == 0x8003
