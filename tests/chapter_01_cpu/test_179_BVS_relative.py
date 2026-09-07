"""Step 179: connect BVS to its relative opcode.

Prerequisite: step 171 added ``instructions.bvs``. In this step, add these
pieces to ``emulator/cpu/opcodes.py``:

    from emulator.cpu.instructions import bvs

    def bvs_relative(cpu: CPU):
        offset = relative(cpu)
        bvs(cpu, offset)

    OPCODE_TABLE[0x70] = bvs_relative

Fold the import and mapping into the existing grouped structures.

Why this step exists:
``relative`` consumes and signs the displacement, then step 171's
``instructions.bvs`` branches from post-operand PC when Overflow is set.

Invariants: ``0x70`` maps to a one-argument handler and consumes its operand on
both paths; Overflow set applies the offset and Overflow clear leaves PC after
the operand.  Flags and memory are unchanged.  Misconception: BVS does not set
Overflow, and an untaken branch still occupies and consumes two instruction
bytes including its opcode.

Out of scope: step 180 independently adds ``addressing_modes.indirect`` for
JMP.  The ``jmp`` instruction and absolute/indirect JMP opcode APIs arrive only
in later steps 181-183 and must not be added here.
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


def test_bvs_relative_handler_exists_and_is_in_opcode_table():
    """Objective: create bvs_relative(cpu) and add 0x70 to OPCODE_TABLE."""
    assert hasattr(opcodes, "bvs_relative")
    assert callable(opcodes.bvs_relative)
    assert list(inspect.signature(opcodes.bvs_relative).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x70] is opcodes.bvs_relative


def test_opcode_70_bvs_relative_branches_when_overflow_set():
    """Objective: BVS branches when Overflow is set."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x70)
    rom.write(0x0001, 0x05)

    cpu.reset()
    cpu.flags.set_overflow_flag(True)
    cpu.step()

    assert cpu.pc == 0x8007


def test_opcode_70_bvs_relative_does_not_branch_when_overflow_clear():
    """Objective: BVS does not branch when Overflow is clear."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x70)
    rom.write(0x0001, 0x05)

    cpu.reset()
    cpu.flags.set_overflow_flag(False)
    cpu.step()

    assert cpu.pc == 0x8002
