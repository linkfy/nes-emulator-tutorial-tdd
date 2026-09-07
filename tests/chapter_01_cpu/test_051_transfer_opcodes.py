"""
Test 051 - Register the four transfer instructions as implied opcodes.

File to update:
    emulator/cpu/opcodes.py

Symbols to update:
    the instruction import and OPCODE_TABLE

Why this step exists:
The transfer operations from test 050 already have the same one-argument shape
that `CPU.step` expects from an opcode-table entry. Implied instructions have no
operand to decode, so an intermediate opcode handler would add no behavior.

Complete example implementation:

    # emulator/cpu/opcodes.py
    from emulator.cpu.instructions import (
        lda, sta, ldx, stx, ldy, sty, tax, txa, tay, tya,
    )

    OPCODE_TABLE = {
        # ...the existing load/store entries...
        0xAA: tax,
        0x8A: txa,
        0xA8: tay,
        0x98: tya,
    }

Important invariants:
    - each opcode maps directly to its instruction function
    - `CPU.step` consumes only the opcode, leaving PC advanced by one byte
    - the transfer and Zero/Negative behavior remains in the instruction layer

Common misconception:
Do not create `tax_implied`-style wrappers or fetch an operand; these four
instructions use implied addressing and already match the dispatch contract.

Out of scope:
    - the FlagsHandler refactor introduced in test 052
    - ADC and its opcode handlers
    - cycle accounting
"""

from emulator.bus.cpu_bus import CpuBus
from emulator.cpu import instructions, opcodes
from emulator.cpu.cpu import CPU
from emulator.memory.fake_rom import FakeROM


def make_cpu_with_rom():
    rom = FakeROM()
    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)
    bus = CpuBus(program_rom=rom)
    return CPU(bus), bus, rom


def test_transfer_opcodes_are_in_opcode_table():
    """
    Objective:
    Add these entries to OPCODE_TABLE:

        0xAA: tax,
        0x8A: txa,
        0xA8: tay,
        0x98: tya,

    Why:
    These instructions use implied addressing.
    CPU.step() fetches only the opcode, then calls the instruction.
    """
    assert opcodes.OPCODE_TABLE[0xAA] is instructions.tax
    assert opcodes.OPCODE_TABLE[0x8A] is instructions.txa
    assert opcodes.OPCODE_TABLE[0xA8] is instructions.tay
    assert opcodes.OPCODE_TABLE[0x98] is instructions.tya


def test_opcode_AA_tax_transfers_a_to_x():
    """Objective: AA means TAX. It copies A into X."""
    cpu, _, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xAA)

    cpu.reset()
    cpu.a = 0x42
    cpu.step()

    assert cpu.x == 0x42
    assert cpu.pc == 0x8001


def test_opcode_8A_txa_transfers_x_to_a():
    """Objective: 8A means TXA. It copies X into A."""
    cpu, _, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x8A)

    cpu.reset()
    cpu.x = 0x42
    cpu.step()

    assert cpu.a == 0x42
    assert cpu.pc == 0x8001


def test_opcode_A8_tay_transfers_a_to_y():
    """Objective: A8 means TAY. It copies A into Y."""
    cpu, _, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xA8)

    cpu.reset()
    cpu.a = 0x42
    cpu.step()

    assert cpu.y == 0x42
    assert cpu.pc == 0x8001


def test_opcode_98_tya_transfers_y_to_a():
    """Objective: 98 means TYA. It copies Y into A."""
    cpu, _, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x98)

    cpu.reset()
    cpu.y = 0x42
    cpu.step()

    assert cpu.a == 0x42
    assert cpu.pc == 0x8001
