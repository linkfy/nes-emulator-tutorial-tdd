"""Step 176: connect BPL to its relative opcode.

Prerequisite: step 175 wired BNE. In this step, add the following to
``emulator/cpu/opcodes.py``:

    from emulator.cpu.instructions import bpl

    def bpl_relative(cpu: CPU):
        offset = relative(cpu)
        bpl(cpu, offset)

    OPCODE_TABLE[0x10] = bpl_relative

Fold the import and entry into the existing grouped import and table literal.
Why this step exists:
``relative`` consumes the operand and step 168's
``instructions.bpl`` interprets "plus" as Negative clear before changing PC.

Invariants: ``0x10`` maps to the one-argument handler; both outcomes consume
the signed operand; Negative clear branches from post-operand PC and Negative
set does not.  Flags and memory remain unchanged.  Misconception: BPL does not
test whether the offset or PC is positive; it tests only the Negative flag.

Out of scope: BMI/BVC/BVS opcode wiring is introduced by steps 177-179, and
indirect JMP addressing is step 180.
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


def test_bpl_relative_handler_exists_and_is_in_opcode_table():
    """Objective: create bpl_relative(cpu) and add 0x10 to OPCODE_TABLE."""
    assert hasattr(opcodes, "bpl_relative")
    assert callable(opcodes.bpl_relative)
    assert list(inspect.signature(opcodes.bpl_relative).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x10] is opcodes.bpl_relative


def test_opcode_10_bpl_relative_branches_when_negative_clear():
    """Objective: BPL branches when Negative is clear."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x10)
    rom.write(0x0001, 0x05)

    cpu.reset()
    cpu.flags.set_negative_flag(False)
    cpu.step()

    assert cpu.pc == 0x8007


def test_opcode_10_bpl_relative_does_not_branch_when_negative_set():
    """Objective: BPL does not branch when Negative is set."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x10)
    rom.write(0x0001, 0x05)

    cpu.reset()
    cpu.flags.set_negative_flag(True)
    cpu.step()

    assert cpu.pc == 0x8002
