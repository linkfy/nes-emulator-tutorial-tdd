"""Step 177: connect BMI to its relative opcode.

Prerequisite: step 176 wired BPL. In this step, add these pieces to
``emulator/cpu/opcodes.py``:

    from emulator.cpu.instructions import bmi

    def bmi_relative(cpu: CPU):
        offset = relative(cpu)
        bmi(cpu, offset)

    OPCODE_TABLE[0x30] = bmi_relative

Merge the import and mapping into the file's existing grouped forms.
Why this step exists:
``relative`` owns operand decoding, while step 169's
``instructions.bmi`` interprets "minus" as Negative set and applies the offset.

Invariants: ``0x30`` consumes its operand on taken and untaken paths; Negative
set branches relative to post-operand PC and Negative clear leaves it there.
No flags or memory change.  Misconception: BMI tests the Negative status bit,
not Python integer negativity of the offset or any register.

Out of scope: BVC and BVS opcode wiring are steps 178 and 179.  Indirect JMP
addressing starts at step 180.
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


def test_bmi_relative_handler_exists_and_is_in_opcode_table():
    """Objective: create bmi_relative(cpu) and add 0x30 to OPCODE_TABLE."""
    assert hasattr(opcodes, "bmi_relative")
    assert callable(opcodes.bmi_relative)
    assert list(inspect.signature(opcodes.bmi_relative).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x30] is opcodes.bmi_relative


def test_opcode_30_bmi_relative_branches_when_negative_set():
    """Objective: BMI branches when Negative is set."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x30)
    rom.write(0x0001, 0x05)

    cpu.reset()
    cpu.flags.set_negative_flag(True)
    cpu.step()

    assert cpu.pc == 0x8007


def test_opcode_30_bmi_relative_does_not_branch_when_negative_clear():
    """Objective: BMI does not branch when Negative is clear."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x30)
    rom.write(0x0001, 0x05)

    cpu.reset()
    cpu.flags.set_negative_flag(False)
    cpu.step()

    assert cpu.pc == 0x8002
