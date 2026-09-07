"""Step 178: connect BVC to its relative opcode.

Prerequisite: step 177 wired BMI. In this step, add the following to
``emulator/cpu/opcodes.py``:

    from emulator.cpu.instructions import bvc

    def bvc_relative(cpu: CPU):
        offset = relative(cpu)
        bvc(cpu, offset)

    OPCODE_TABLE[0x50] = bvc_relative

The import and entry should join the existing grouped import and table literal.
Why this step exists:
The handler decodes one signed operand, then step 170's
``instructions.bvc`` makes the Overflow-clear branch decision.

Invariants: opcode ``0x50`` always consumes its operand; Overflow clear applies
the offset from post-operand PC and Overflow set leaves PC there.  No flag or
memory is modified.  Misconception: BVC does not clear Overflow and does not
derive overflow from the branch offset; it only observes the current flag.

Out of scope: BVS opcode wiring is step 179.  Indirect JMP addressing follows
as step 180.
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


def test_bvc_relative_handler_exists_and_is_in_opcode_table():
    """Objective: create bvc_relative(cpu) and add 0x50 to OPCODE_TABLE."""
    assert hasattr(opcodes, "bvc_relative")
    assert callable(opcodes.bvc_relative)
    assert list(inspect.signature(opcodes.bvc_relative).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x50] is opcodes.bvc_relative


def test_opcode_50_bvc_relative_branches_when_overflow_clear():
    """Objective: BVC branches when Overflow is clear."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x50)
    rom.write(0x0001, 0x05)

    cpu.reset()
    cpu.flags.set_overflow_flag(False)
    cpu.step()

    assert cpu.pc == 0x8007


def test_opcode_50_bvc_relative_does_not_branch_when_overflow_set():
    """Objective: BVC does not branch when Overflow is set."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x50)
    rom.write(0x0001, 0x05)

    cpu.reset()
    cpu.flags.set_overflow_flag(True)
    cpu.step()

    assert cpu.pc == 0x8002
