"""Step 207: wire implied flag-control opcodes.

Why this step exists:
In this step, update ``emulator/cpu/opcodes.py``'s instruction import and
``OPCODE_TABLE``.  The functions from step 206 become executable through
``emulator/cpu/cpu.py::CPU.step``.

Suggested implementation::

    # Add clc, sec, cli, sei, cld, sed, clv to the instruction import.
    OPCODE_TABLE = {
        # existing entries
        0x18: clc,
        0x38: sec,
        0x58: cli,
        0x78: sei,
        0xD8: cld,
        0xF8: sed,
        0xB8: clv,
    }

Invariant: every mapping dispatches directly to a one-argument operation; each
instruction is one byte, so opcode fetch alone advances PC to the next byte and
only the target flag changes.  The common misconception is to add an addressing
mode that consumes an operand, or to transpose set/clear opcode pairs.

Out of scope: NOP and opcode $EA belong to steps 208-209, and interrupt delivery
semantics are later behavior.
"""
import inspect

import pytest

from emulator.bus.cpu_bus import CpuBus
from emulator.cpu import opcodes
from emulator.cpu.cpu import CPU
from emulator.cpu.instructions import clc, cld, cli, clv, sec, sed, sei
from emulator.memory.fake_rom import FakeROM


CARRY_FLAG = 1 << 0
INTERRUPT_DISABLE_FLAG = 1 << 2
DECIMAL_FLAG = 1 << 3
OVERFLOW_FLAG = 1 << 6


def make_cpu_with_rom():
    rom = FakeROM()
    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)
    bus = CpuBus(program_rom=rom)
    return CPU(bus), bus, rom


@pytest.mark.parametrize(
    ("opcode", "instruction"),
    [
        (0x18, clc),
        (0x38, sec),
        (0x58, cli),
        (0x78, sei),
        (0xD8, cld),
        (0xF8, sed),
        (0xB8, clv),
    ],
)
def test_flag_control_opcodes_are_in_opcode_table(opcode, instruction):
    """Objective: each official flag-control opcode maps to the right function."""
    assert opcodes.OPCODE_TABLE[opcode] is instruction


@pytest.mark.parametrize("instruction", [clc, sec, cli, sei, cld, sed, clv])
def test_flag_control_instruction_signatures_take_only_cpu(instruction):
    """Objective: implied instructions do not need operand arguments."""
    assert list(inspect.signature(instruction).parameters) == ["cpu"]


@pytest.mark.parametrize(
    ("opcode", "initial_p", "expected_flag", "flag_mask"),
    [
        (0x18, CARRY_FLAG, False, CARRY_FLAG),
        (0x38, 0x00, True, CARRY_FLAG),
        (0x58, INTERRUPT_DISABLE_FLAG, False, INTERRUPT_DISABLE_FLAG),
        (0x78, 0x00, True, INTERRUPT_DISABLE_FLAG),
        (0xD8, DECIMAL_FLAG, False, DECIMAL_FLAG),
        (0xF8, 0x00, True, DECIMAL_FLAG),
        (0xB8, OVERFLOW_FLAG, False, OVERFLOW_FLAG),
    ],
)
def test_flag_control_opcodes_change_their_target_flag(
    opcode,
    initial_p,
    expected_flag,
    flag_mask,
):
    """Objective: executing each opcode changes exactly its intended flag."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, opcode)

    cpu.reset()
    cpu.p = initial_p
    cpu.step()

    assert bool(cpu.p & flag_mask) is expected_flag


def test_flag_control_opcodes_do_not_fetch_operand_bytes():
    """
    Objective:
    Flag-control opcodes are one byte long.

    The byte after the opcode is the next instruction, not an operand.
    """
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x38)  # SEC
    rom.write(0x0001, 0x99)

    cpu.reset()
    cpu.p = 0x00
    cpu.step()

    assert cpu.flags.get_carry_flag() is True
    assert cpu.pc == 0x8001
