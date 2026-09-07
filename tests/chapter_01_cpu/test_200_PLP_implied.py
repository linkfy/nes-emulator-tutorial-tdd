"""Step 200: register implied PLP.

Prerequisite: step 199 added ``plp``. In this step, change only
``emulator/cpu/opcodes.py`` by importing ``plp`` and adding its ``OPCODE_TABLE``
entry.

Why this step exists:
PLP obtains its value from the stack selected by S. Opcode $28 has
no operand and must dispatch directly to ``plp(cpu)``.

Suggested implementation::

    from emulator.cpu.instructions import plp

    OPCODE_TABLE = {
        # existing entries
        0x28: plp,
    }

Invariants: preserve all existing mappings; map exactly $28 to ``plp``; use no
addressing-mode wrapper; consume only the opcode byte; preserve step 199's
replace-and-mask semantics.

Misconception: the byte after $28 is the next instruction, not the status byte
to restore; status comes exclusively from the incremented stack slot.

Out of scope: PLP behavior is step 199. TXS/TSX belong to steps 201-204. Later
Break/ONE behavior must not be anticipated.
"""
import inspect

from emulator.bus.cpu_bus import CpuBus
from emulator.cpu import opcodes
from emulator.cpu.cpu import CPU
from emulator.cpu.instructions import plp
from emulator.memory.fake_rom import FakeROM


CARRY_FLAG = 1 << 0
BREAK_FLAG = 1 << 4
ONE_FLAG = 1 << 5
NEGATIVE_FLAG = 1 << 7
STACK_BASE = 0x0100


def make_cpu_with_rom():
    rom = FakeROM()
    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)
    bus = CpuBus(program_rom=rom)
    return CPU(bus), bus, rom


def test_plp_implied_is_in_opcode_table():
    """Objective: opcode 0x28 is the official PLP opcode."""
    assert opcodes.OPCODE_TABLE[0x28] is plp


def test_plp_instruction_signature_takes_only_cpu():
    """Objective: PLP is implied, so plp(cpu) does not need an operand argument."""
    assert list(inspect.signature(plp).parameters) == ["cpu"]


def test_opcode_28_plp_restores_processor_status_from_stack():
    """Objective: executing opcode 0x28 pulls saved status into cpu.p."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x28)

    cpu.reset()
    cpu.s = 0xFC
    bus.write(STACK_BASE | 0xFD, CARRY_FLAG | NEGATIVE_FLAG)
    cpu.step()

    assert cpu.p == (CARRY_FLAG | NEGATIVE_FLAG)
    assert cpu.s == 0xFD


def test_opcode_28_plp_masks_break_from_restored_status():
    """
    Objective:
    If the saved status byte has Break/ONE set, PLP does not keep those bits as
    persistent CPU state in this emulator model.
    """
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x28)

    cpu.reset()
    cpu.s = 0xFC
    bus.write(STACK_BASE | 0xFD, BREAK_FLAG | ONE_FLAG | CARRY_FLAG)
    cpu.step()

    assert cpu.p == CARRY_FLAG
    assert cpu.flags.get_break_flag() is False
    assert cpu.flags.get_one_flag() is False


def test_opcode_28_plp_does_not_fetch_operand_bytes():
    """
    Objective:
    PLP is one byte long. The byte after PLP must not be consumed as an operand.

    The restored status comes from the stack, not from program memory after 0x28.
    """
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x28)
    rom.write(0x0001, 0x99)

    cpu.reset()
    cpu.s = 0xFC
    bus.write(STACK_BASE | 0xFD, NEGATIVE_FLAG)
    cpu.step()

    assert cpu.p == NEGATIVE_FLAG
    assert cpu.pc == 0x8001


def test_opcode_28_plp_replaces_previous_status_not_merges_it():
    """Objective: PLP replaces cpu.p with the pulled status bits."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x28)

    cpu.reset()
    cpu.s = 0xFC
    cpu.p = NEGATIVE_FLAG
    bus.write(STACK_BASE | 0xFD, CARRY_FLAG)
    cpu.step()

    assert cpu.p == CARRY_FLAG
