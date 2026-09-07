"""Lesson 163: decode an eight-bit relative branch offset.

Why this step exists:
A branch stores a signed displacement from the PC after its operand rather
than a full target, so decoding must be separate from the branch decision.

In this step, add only this implementation to
``emulator/cpu/addressing_modes.py::relative``:

    def relative(cpu: CPU) -> int:
        offset = cpu.fetch_byte()
        # Transform to signed integer
        # 0x7F -> +127
        # 0x80 -> -128
        # 0xFF -> -1
        if offset & 0x80: # offset has bit 7 active, is negative
            offset -= 0x100
        return offset

``CPU.fetch_byte`` reads the operand and advances PC once;
subtracting ``0x100`` for bit-7-set values maps unsigned ``0x80..0xFF`` to
signed ``-128..-1`` while preserving ``0x00..0x7F`` as ``0..127``.

Invariants: this helper always consumes exactly one byte and never changes PC
by the returned offset.  It does not inspect flags or alter registers, memory,
or status.  Misconception: ``relative`` decodes a displacement; it neither
decides whether a branch is taken nor computes an absolute target itself.

Out of scope: ``instructions.bcc`` belongs to lesson 164.  Other branch
semantics are lessons 165-171, and opcode handlers/table entries are lessons
172-179.
"""
import inspect

from emulator.bus.cpu_bus import CpuBus
from emulator.cpu import addressing_modes
from emulator.cpu.cpu import CPU
from emulator.memory.fake_rom import FakeROM


def make_cpu_with_rom():
    rom = FakeROM()
    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)
    bus = CpuBus(program_rom=rom)
    return CPU(bus), bus, rom


def test_relative_addressing_mode_exists():
    """
    Objective:
    Create in addressing_modes.py:
        def relative(cpu):
            ...

    What it does:
    - Read the next byte from the CPU bus.
    - Move PC to the next position.
    - Return that byte as a signed integer.

    Important:
    This function must not jump. It only decodes the offset.
    Branch instructions will decide later whether to add the offset to PC.

    """
    assert hasattr(addressing_modes, "relative")
    assert callable(addressing_modes.relative)
    assert list(inspect.signature(addressing_modes.relative).parameters) == ["cpu"]


def test_relative_returns_positive_offset_when_bit_7_is_clear():
    """
    Objective:
    If the offset byte is 0x05, relative(cpu) returns +5.

    Why:
    Values 0x00 through 0x7F are positive relative offsets.
    """
    cpu, _, rom = make_cpu_with_rom()

    cpu.reset()
    rom.write(0x0000, 0x05)

    offset = addressing_modes.relative(cpu)

    assert offset == 5
    assert cpu.pc == 0x8001


def test_relative_returns_zero_offset():
    """
    Objective:
    0x00 means offset 0.

    Why:
    This is still a valid relative offset, and fetching it must advance PC.
    """
    cpu, _, rom = make_cpu_with_rom()

    cpu.reset()
    rom.write(0x0000, 0x00)

    offset = addressing_modes.relative(cpu)

    assert offset == 0
    assert cpu.pc == 0x8001


def test_relative_returns_largest_positive_offset():
    """
    Objective:
    0x7F means +127.

    Why:
    In signed 8-bit representation, bit 7 is the sign bit.
    0x7F has bit 7 clear, so it remains positive.
    """
    cpu, _, rom = make_cpu_with_rom()

    cpu.reset()
    rom.write(0x0000, 0x7F)

    offset = addressing_modes.relative(cpu)

    assert offset == 127
    assert cpu.pc == 0x8001


def test_relative_returns_minus_one_for_ff():
    """
    Objective:
    0xFF means -1.

    Step by step:
    - Read 0xFF, which is 255 as an unsigned byte.
    - Bit 7 is set, so it is a negative signed offset.
    - Convert by subtracting 0x100: 255 - 256 == -1.
    """
    cpu, _, rom = make_cpu_with_rom()

    cpu.reset()
    rom.write(0x0000, 0xFF)

    offset = addressing_modes.relative(cpu)

    assert offset == -1
    assert cpu.pc == 0x8001


def test_relative_returns_largest_negative_offset():
    """
    Objective:
    0x80 means -128.

    Step by step:
    - Read 0x80, which is 128 as an unsigned byte.
    - Bit 7 is set, so it is negative.
    - Convert by subtracting 0x100: 128 - 256 == -128.
    """
    cpu, _, rom = make_cpu_with_rom()

    cpu.reset()
    rom.write(0x0000, 0x80)

    offset = addressing_modes.relative(cpu)

    assert offset == -128
    assert cpu.pc == 0x8001


def test_relative_does_not_change_pc_to_branch_target():
    """
    Objective:
    relative(cpu) only fetches and decodes the offset.

    Example:
    If PC starts at 0x8000 and the offset is 0xFE (-2), relative(cpu) should
    leave PC at 0x8001, not jump to 0x7FFF.

    The branch instruction will apply the offset later if its condition is true.
    """
    cpu, _, rom = make_cpu_with_rom()

    cpu.reset()
    rom.write(0x0000, 0xFE)

    offset = addressing_modes.relative(cpu)

    assert offset == -2
    assert cpu.pc == 0x8001
