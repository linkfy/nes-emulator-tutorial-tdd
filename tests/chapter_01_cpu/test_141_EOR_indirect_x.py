"""Lesson 141: add EOR (indirect,X) opcode ``0x41``.

Why this step exists:
Pre-indexed indirect EOR enables pointer-table access through zero page while
preserving the split between effective-address resolution and exclusive OR.

In this step, lessons 134-140 already provide ``or_e``, its opcode import, and
the earlier EOR modes.  Add exactly the following to
``emulator/cpu/opcodes.py``:

    def eor_indirect_x(cpu: CPU):
        addr = indirect_x(cpu)
        value = cpu.bus.read(addr)
        or_e(cpu, value)

    OPCODE_TABLE = {
        ...
        0x41: eor_indirect_x,
    }

``emulator/cpu/addressing_modes.py::indirect_x`` adds X to the operand in
zero page, reads the wrapped little-endian pointer there, and returns its
target.  The handler reads that target and delegates XOR semantics to
``emulator/cpu/instructions.py::or_e``.  A and Z/N may change; Carry,
Overflow, X, Y, and memory remain invariant; opcode plus operand advances PC
two bytes.

Misconception: X indexes the zero-page pointer location, not the final target.
Out of scope: EOR (indirect),Y is lesson 142; BIT begins in lesson 143.
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


def test_eor_indirect_x_handler_exists_and_is_in_opcode_table():
    """Objective: create eor_indirect_x(cpu) and add 0x41 to OPCODE_TABLE."""
    assert hasattr(opcodes, "eor_indirect_x")
    assert callable(opcodes.eor_indirect_x)
    assert list(inspect.signature(opcodes.eor_indirect_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x41] is opcodes.eor_indirect_x


def test_opcode_41_eor_indirect_x_reads_pointed_memory_value():
    """Objective: 41 20 with X=0x04 reads pointer at zero-page $24/$25."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x41)
    rom.write(0x0001, 0x20)
    bus.write(0x0024, 0x00)
    bus.write(0x0025, 0x02)
    bus.write(0x0200, 0x0F)

    cpu.reset()
    cpu.x = 0x04
    cpu.a = 0xF0
    cpu.step()

    assert cpu.a == 0xFF
    assert cpu.pc == 0x8002
