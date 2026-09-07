"""Lesson 101: wire LSR Absolute,X (opcode ``0x5E``).

In this step, add only the final LSR addressing-mode adapter and dispatch entry
below. The instruction primitive and other LSR modes from lessons 095-100 are
prerequisites.

Suggested implementation in the production locations:

``emulator/cpu/opcodes.py::lsr_absolute_x``::

    def lsr_absolute_x(cpu: CPU):
        addr = absolute_x(cpu)
        lsr(cpu, addr)

``emulator/cpu/opcodes.py::OPCODE_TABLE``::

    0x5E: lsr_absolute_x,

Why this step exists:
Opcode handlers translate encoded operands into effective
addresses; ``instructions.lsr`` remains independent of addressing mode.

Invariants: ``absolute_x(cpu)`` consumes the little-endian two-byte operand,
adds ``cpu.x``, and leaves the PC three bytes past the opcode; ``lsr`` performs
the read/modify/write and flag updates at that address.  Thus ``5E 00 02``
with X=``0x04`` targets ``$0204``.

Misconception: the operand is neither the value to shift nor an 8-bit
zero-page address; do not add X to only one operand byte or call ``lsr_a``.

Out of scope: ROL/ROR behavior and opcodes begin in lessons 102 onward; cycle
accuracy and page-cross timing are not part of this step.
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


def test_lsr_absolute_x_handler_exists_and_is_in_opcode_table():
    """Objective: create lsr_absolute_x(cpu) and add 0x5E to OPCODE_TABLE."""
    assert hasattr(opcodes, "lsr_absolute_x")
    assert callable(opcodes.lsr_absolute_x)
    assert list(inspect.signature(opcodes.lsr_absolute_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x5E] is opcodes.lsr_absolute_x


def test_opcode_5E_lsr_absolute_x_shifts_indexed_memory_value():
    """Objective: 5E 00 02 with X=0x04 shifts RAM[$0204]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x5E)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0204, 0b0000_0110)

    cpu.reset()
    cpu.x = 0x04
    cpu.step()

    assert bus.read(0x0204) == 0b0000_0011
    assert cpu.pc == 0x8003
