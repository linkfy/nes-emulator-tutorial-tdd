"""Step 173: connect BCS to its relative opcode.

Prerequisite: step 172 imported ``relative`` and wired BCC. In this step, add
these pieces
to ``emulator/cpu/opcodes.py``:

    from emulator.cpu.instructions import bcs

    def bcs_relative(cpu: CPU):
        offset = relative(cpu)
        bcs(cpu, offset)

    OPCODE_TABLE[0xB0] = bcs_relative

Fold the import and table item into the existing grouped import and table
literal.

Why this step exists:
Addressing remains in the opcode layer, while step 165's ``instructions.bcs``
owns the complementary Carry-set decision.

Invariants: ``0xB0`` maps to ``bcs_relative(cpu)``; the signed operand is always
consumed; Carry set branches from post-operand PC and Carry clear leaves that PC
unchanged.  Flags and memory are untouched.  Misconception: BCS means Carry
set, not Carry clear, and the handler must not duplicate sign conversion.

Out of scope: BEQ/BNE/BPL/BMI/BVC/BVS opcode wiring remains for steps 174-179;
JMP addressing is step 180.
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


def test_bcs_relative_handler_exists_and_is_in_opcode_table():
    """Objective: create bcs_relative(cpu) and add 0xB0 to OPCODE_TABLE."""
    assert hasattr(opcodes, "bcs_relative")
    assert callable(opcodes.bcs_relative)
    assert list(inspect.signature(opcodes.bcs_relative).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xB0] is opcodes.bcs_relative


def test_opcode_B0_bcs_relative_branches_when_carry_set():
    """Objective: BCS branches when Carry is set."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xB0)
    rom.write(0x0001, 0x05)

    cpu.reset()
    cpu.flags.set_carry_flag(True)
    cpu.step()

    assert cpu.pc == 0x8007


def test_opcode_B0_bcs_relative_does_not_branch_when_carry_clear():
    """Objective: BCS does not branch when Carry is clear."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xB0)
    rom.write(0x0001, 0x05)

    cpu.reset()
    cpu.flags.set_carry_flag(False)
    cpu.step()

    assert cpu.pc == 0x8002
