"""Step 175: connect BNE to its relative opcode.

Prerequisite: step 174 wired BEQ. In this step, add these pieces to
``emulator/cpu/opcodes.py``:

    from emulator.cpu.instructions import bne

    def bne_relative(cpu: CPU):
        offset = relative(cpu)
        bne(cpu, offset)

    OPCODE_TABLE[0xD0] = bne_relative

Merge the import and table item into their existing grouped forms.

Why this step exists:
The opcode layer consumes and decodes the displacement, then delegates the
Zero-clear decision to step 167's ``instructions.bne``.

Invariants: ``0xD0`` always consumes one operand byte; Zero clear applies the
signed offset to post-operand PC and Zero set leaves that PC unchanged.  The
handler changes no flags or memory.  Misconception: BNE does not perform a
comparison, and an untaken branch must not leave PC on its operand.

Out of scope: BPL/BMI/BVC/BVS opcode wiring follows in steps 176-179.  The
next addressing-mode feature, indirect JMP, is step 180.
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


def test_bne_relative_handler_exists_and_is_in_opcode_table():
    """Objective: create bne_relative(cpu) and add 0xD0 to OPCODE_TABLE."""
    assert hasattr(opcodes, "bne_relative")
    assert callable(opcodes.bne_relative)
    assert list(inspect.signature(opcodes.bne_relative).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xD0] is opcodes.bne_relative


def test_opcode_D0_bne_relative_branches_when_zero_clear():
    """Objective: BNE branches when Zero is clear."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xD0)
    rom.write(0x0001, 0x05)

    cpu.reset()
    cpu.flags.set_zero_flag(False)
    cpu.step()

    assert cpu.pc == 0x8007


def test_opcode_D0_bne_relative_does_not_branch_when_zero_set():
    """Objective: BNE does not branch when Zero is set."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xD0)
    rom.write(0x0001, 0x05)

    cpu.reset()
    cpu.flags.set_zero_flag(True)
    cpu.step()

    assert cpu.pc == 0x8002
