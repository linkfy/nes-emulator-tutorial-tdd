"""Step 172: connect BCC to its relative opcode.

In this step, add these pieces to ``emulator/cpu/opcodes.py``:

    from emulator.cpu.instructions import bcc
    from emulator.cpu.addressing_modes import relative

    def bcc_relative(cpu: CPU):
        offset = relative(cpu)
        bcc(cpu, offset)

    OPCODE_TABLE[0x90] = bcc_relative

The imports may be folded into the file's existing grouped imports, and the
table entry belongs in its literal.

Why this step exists:
``CPU.step`` has consumed the
opcode, ``relative`` consumes and signs the one-byte operand, and step 164's
``bcc`` applies it only when Carry is clear.

Invariants: opcode ``0x90`` resolves to the one-argument handler; every path
consumes the operand, so an untaken branch finishes at ``0x8002`` and a ``+5``
branch targets ``0x8007``.  The handler itself changes no flags or memory.
Misconception: the displacement is relative to PC after the operand, not to the
opcode address, and it must be fetched even when Carry prevents the branch.

Out of scope: BCS, BEQ, BNE, BPL, BMI, BVC, and BVS handlers/table entries are
steps 173-179.  Indirect JMP addressing begins at step 180.
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


def test_bcc_relative_handler_exists_and_is_in_opcode_table():
    """Objective: create bcc_relative(cpu) and add 0x90 to OPCODE_TABLE."""
    assert hasattr(opcodes, "bcc_relative")
    assert callable(opcodes.bcc_relative)
    assert list(inspect.signature(opcodes.bcc_relative).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x90] is opcodes.bcc_relative


def test_opcode_90_bcc_relative_branches_when_carry_clear():
    """Objective: 90 05 branches from next instruction address 0x8002 to 0x8007."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x90)
    rom.write(0x0001, 0x05)

    cpu.reset()
    cpu.flags.set_carry_flag(False)
    cpu.step()

    assert cpu.pc == 0x8007


def test_opcode_90_bcc_relative_does_not_branch_when_carry_set():
    """Objective: branch not taken still consumes opcode and offset bytes."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x90)
    rom.write(0x0001, 0x05)

    cpu.reset()
    cpu.flags.set_carry_flag(True)
    cpu.step()

    assert cpu.pc == 0x8002
