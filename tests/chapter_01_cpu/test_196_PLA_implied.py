"""Step 196: register implied PLA.

Prerequisite: step 195 added ``pla``. In this step, change only
``emulator/cpu/opcodes.py`` by importing ``pla`` and adding its ``OPCODE_TABLE``
entry.

Why this step exists:
PLA's input is the hardware stack selected by S. Opcode $68 has no
operand, so ``CPU.step()`` must dispatch directly to ``pla(cpu)``.

Suggested implementation::

    from emulator.cpu.instructions import pla

    OPCODE_TABLE = {
        # existing entries
        0x68: pla,
    }

Invariants: preserve existing mappings; map exactly $68 to ``pla``; use no
addressing-mode wrapper; consume only the opcode byte; retain step 195's Z/N
effects.

Misconception: program memory after $68 does not supply the pulled value; the
incremented stack address does.

Out of scope: ``pla`` behavior is step 195. PHP begins at step 197, and its
function and opcode mapping must not be introduced by this transition.
"""
import inspect

from emulator.bus.cpu_bus import CpuBus
from emulator.cpu import opcodes
from emulator.cpu.cpu import CPU
from emulator.cpu.instructions import pla
from emulator.memory.fake_rom import FakeROM


STACK_BASE = 0x0100


def make_cpu_with_rom():
    rom = FakeROM()
    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)
    bus = CpuBus(program_rom=rom)
    return CPU(bus), bus, rom


def test_pla_implied_is_in_opcode_table():
    """Objective: opcode 0x68 is the official PLA opcode."""
    assert opcodes.OPCODE_TABLE[0x68] is pla


def test_pla_instruction_signature_takes_only_cpu():
    """Objective: PLA is implied, so pla(cpu) does not need an operand argument."""
    assert list(inspect.signature(pla).parameters) == ["cpu"]


def test_opcode_68_pla_pulls_stack_value_into_accumulator():
    """Objective: executing opcode 0x68 pulls the next stack byte into A."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x68)

    cpu.reset()
    cpu.s = 0xFC
    bus.write(STACK_BASE | 0xFD, 0x42)
    cpu.step()

    assert cpu.a == 0x42
    assert cpu.s == 0xFD


def test_opcode_68_pla_updates_zero_and_negative_flags():
    """Objective: PLA opcode behavior includes Zero/Negative flag updates."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x68)

    cpu.reset()
    cpu.s = 0xFC
    bus.write(STACK_BASE | 0xFD, 0x80)
    cpu.step()

    assert cpu.a == 0x80
    assert cpu.flags.get_zero_flag() is False
    assert cpu.flags.get_negative_flag() is True


def test_opcode_68_pla_does_not_fetch_operand_bytes():
    """
    Objective:
    PLA is one byte long. The byte after PLA must not be consumed as an operand.

    The pulled value comes from the stack, not from program memory after 0x68.
    """
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x68)
    rom.write(0x0001, 0x99)

    cpu.reset()
    cpu.s = 0xFC
    bus.write(STACK_BASE | 0xFD, 0x55)
    cpu.step()

    assert cpu.a == 0x55
    assert cpu.pc == 0x8001


def test_opcode_68_pla_preserves_other_flags():
    """Objective: PLA updates Z/N but does not damage unrelated status flags."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x68)

    cpu.reset()
    cpu.s = 0xFC
    cpu.p = 0b0100_0001
    bus.write(STACK_BASE | 0xFD, 0x01)
    cpu.step()

    assert cpu.a == 0x01
    assert cpu.p & 0b0100_0001 == 0b0100_0001
    assert cpu.flags.get_zero_flag() is False
    assert cpu.flags.get_negative_flag() is False
