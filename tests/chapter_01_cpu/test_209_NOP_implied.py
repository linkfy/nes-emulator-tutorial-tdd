"""Step 209: wire official implied NOP opcode $EA.

Why this step exists:
In this step, update ``emulator/cpu/opcodes.py``'s instruction import and
``OPCODE_TABLE``; ``emulator/cpu/instructions.py::nop`` already exists from
step 208.  This mapping permits CPU.step to execute padding in real programs.

Suggested implementation::

    from emulator.cpu.instructions import nop  # add to the existing import

    OPCODE_TABLE = {
        # existing entries
        0xEA: nop,
    }

Invariant: $EA is one byte, so a step from $8000 ends at $8001 solely because
CPU.step fetched the opcode; registers, S, P, and memory remain unchanged.  The
common misconception is to increment PC in ``nop`` or fetch a phantom operand.

Out of scope: unofficial multi-byte NOP opcodes and timing changes belong to
later steps. Multi-instruction CPU verification belongs to step 210.
"""
import inspect

from emulator.bus.cpu_bus import CpuBus
from emulator.cpu import opcodes
from emulator.cpu.cpu import CPU
from emulator.cpu.instructions import nop
from emulator.memory.fake_rom import FakeROM


def make_cpu_with_rom():
    rom = FakeROM()
    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)
    bus = CpuBus(program_rom=rom)
    return CPU(bus), bus, rom


def test_nop_implied_is_in_opcode_table():
    """Objective: opcode 0xEA is the official NOP opcode."""
    assert opcodes.OPCODE_TABLE[0xEA] is nop


def test_nop_instruction_signature_takes_only_cpu():
    """Objective: NOP is implied, so nop(cpu) does not need an operand argument."""
    assert list(inspect.signature(nop).parameters) == ["cpu"]


def test_opcode_EA_nop_advances_pc_only_by_opcode_fetch():
    """
    Objective:
    Executing opcode 0xEA advances PC from $8000 to $8001.

    That one-byte advance comes from CPU.step() fetching the opcode, not from
    nop(cpu) itself.
    """
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xEA)

    cpu.reset()
    cpu.step()

    assert cpu.pc == 0x8001


def test_opcode_EA_nop_does_not_fetch_operand_bytes():
    """
    Objective:
    NOP is one byte long. The byte after NOP is the next instruction, not an
    operand consumed by NOP.
    """
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xEA)
    rom.write(0x0001, 0x99)

    cpu.reset()
    cpu.step()

    assert cpu.pc == 0x8001


def test_opcode_EA_nop_preserves_registers_and_flags():
    """Objective: executing NOP preserves registers and flags."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xEA)

    cpu.reset()
    cpu.a = 0x11
    cpu.x = 0x22
    cpu.y = 0x33
    cpu.s = 0xFD
    cpu.p = 0b1100_1111
    cpu.step()

    assert cpu.a == 0x11
    assert cpu.x == 0x22
    assert cpu.y == 0x33
    assert cpu.s == 0xFD
    assert cpu.p == 0b1100_1111
