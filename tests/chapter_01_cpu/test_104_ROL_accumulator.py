"""Lesson 104: expose ROL A as opcode ``0x2A``.

In this step, after lessons 102-103 define ``rol`` and ``rol_a``, add the ROL
imports needed by opcodes and the accumulator dispatch entry. Later memory
modes and ROR remain in their numbered steps.

Suggested implementation in the production locations:

``emulator/cpu/opcodes.py`` import list gains::

    rol, rol_a

``emulator/cpu/opcodes.py::OPCODE_TABLE`` gains::

    0x2A: rol_a,

Why this step exists:
Accumulator mode needs no adapter because ``rol_a(cpu)`` already
matches the opcode handler signature.

Invariants: fetching ``0x2A`` advances PC once before dispatch; ``rol_a``
consumes no operand, so final PC is start+1, only A is rotated, and its C/Z/N
flags retain lesson 103 semantics.

Misconception: do not create an addressing-mode wrapper or call ``rol`` with
A.  Accumulator mode is one byte and directly maps to ``rol_a``.

Out of scope: memory opcode adapters ``0x26``, ``0x36``, ``0x2E``, and
``0x3E`` are lessons 105-108; all ROR dispatch is lesson 111 onward.
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


def test_rol_accumulator_opcode_exists_and_is_in_opcode_table():
    """Objective: import rol_a and add 0x2A to OPCODE_TABLE."""
    assert hasattr(opcodes, "rol_a")
    assert callable(opcodes.rol_a)
    assert list(inspect.signature(opcodes.rol_a).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x2A] is opcodes.rol_a


def test_opcode_2A_rol_accumulator_rotates_a_and_advances_pc_by_one():
    """Objective: 2A means ROL A, so only A is rotated and PC advances by 1."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x2A)

    cpu.reset()
    cpu.a = 0b0000_0011
    cpu.step()

    assert cpu.a == 0b0000_0110
    assert cpu.pc == 0x8001


def test_opcode_2A_rol_accumulator_uses_old_carry_as_new_bit_0():
    """Objective: old Carry=1 is inserted into A bit 0."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x2A)

    cpu.reset()
    cpu.p |= CARRY_FLAG
    cpu.a = 0b0000_0010
    cpu.step()

    assert cpu.a == 0b0000_0101
    assert (cpu.p & CARRY_FLAG) == 0


def test_opcode_2A_rol_accumulator_sets_carry_from_old_a_bit_7():
    """Objective: old A bit 7 becomes Carry."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x2A)

    cpu.reset()
    cpu.a = 0b1000_0001
    cpu.step()

    assert cpu.a == 0b0000_0010
    assert (cpu.p & CARRY_FLAG) != 0
