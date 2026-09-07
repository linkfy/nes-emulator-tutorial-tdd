"""Step 174: connect BEQ to its relative opcode.

Prerequisite: step 173 wired BCS. In this step, add the following to
``emulator/cpu/opcodes.py``:

    from emulator.cpu.instructions import beq

    def beq_relative(cpu: CPU):
        offset = relative(cpu)
        beq(cpu, offset)

    OPCODE_TABLE[0xF0] = beq_relative

The import and mapping can be merged into the existing grouped structures.
Why this step exists:
``relative`` supplies the signed, post-operand displacement and
step 166's ``instructions.beq`` branches when the existing Zero flag is set.

Invariants: ``0xF0`` dispatches to a one-argument handler and consumes its
operand whether or not Zero is set; ``+5`` from ``0x8002`` reaches ``0x8007``.
No flags or memory change.  Misconception: BEQ does not compare values itself;
it only observes Zero as established by an earlier operation.

Out of scope: BNE/BPL/BMI/BVC/BVS opcode wiring belongs to steps 175-179;
indirect JMP addressing belongs to step 180.
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


def test_beq_relative_handler_exists_and_is_in_opcode_table():
    """Objective: create beq_relative(cpu) and add 0xF0 to OPCODE_TABLE."""
    assert hasattr(opcodes, "beq_relative")
    assert callable(opcodes.beq_relative)
    assert list(inspect.signature(opcodes.beq_relative).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xF0] is opcodes.beq_relative


def test_opcode_F0_beq_relative_branches_when_zero_set():
    """Objective: BEQ branches when Zero is set."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xF0)
    rom.write(0x0001, 0x05)

    cpu.reset()
    cpu.flags.set_zero_flag(True)
    cpu.step()

    assert cpu.pc == 0x8007


def test_opcode_F0_beq_relative_does_not_branch_when_zero_clear():
    """Objective: BEQ does not branch when Zero is clear."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xF0)
    rom.write(0x0001, 0x05)

    cpu.reset()
    cpu.flags.set_zero_flag(False)
    cpu.step()

    assert cpu.pc == 0x8002
