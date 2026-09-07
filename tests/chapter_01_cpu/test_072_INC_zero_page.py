"""Lesson 072: wire INC Zero Page (`0xE6`).

In this step, with `emulator/cpu/instructions.py:inc` from lesson 071 as a
prerequisite, add only the zero-page wiring in `emulator/cpu/opcodes.py`.

Why this step exists:
Opcode handlers translate instruction bytes into an effective
address. Reusing `addressing_modes.zero_page` preserves operand fetching and PC
movement while `instructions.inc` remains independent of addressing mode.

Suggested implementation in `emulator/cpu/opcodes.py`:

    from emulator.cpu.instructions import lda, sta, ldx, stx, ldy, sty, tax, txa, tay, tya, adc, sbc, inc

    def inc_zero_page(cpu: CPU):
        addr = zero_page(cpu)
        inc(cpu, addr)

Add this exact entry to the existing `OPCODE_TABLE`:

    0xE6: inc_zero_page,

The handler was inserted under `# ------ INC Opcodes`, and the mapping was
appended to `OPCODE_TABLE`.

Invariants: `zero_page(cpu)` consumes one operand byte, returns a page-zero
address, and advances PC once; the handler delegates one read-modify-write to
`inc`; `0xE6` maps to the function object; instruction length is two bytes; INC
still changes only memory and Z/N.

Misconception: the operand byte is an address, not the byte to increment. Do not
read it in the handler or duplicate INC arithmetic there.

Out of scope: `inc_zero_page_x`, `inc_absolute`, and `inc_absolute_x`, plus their
`0xF6`, `0xEE`, and `0xFE` mappings, are lessons 073-075.
"""
import inspect

from emulator.bus.cpu_bus import CpuBus
from emulator.cpu import opcodes
from emulator.cpu.cpu import CPU
from emulator.memory.fake_rom import FakeROM
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG


def make_cpu_with_rom():
    rom = FakeROM()
    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)
    bus = CpuBus(program_rom=rom)
    return CPU(bus), bus, rom


def test_inc_zero_page_handler_exists_and_is_in_opcode_table():
    """Objective: create inc_zero_page(cpu) and add 0xE6 to OPCODE_TABLE."""
    assert hasattr(opcodes, "inc_zero_page")
    assert callable(opcodes.inc_zero_page)
    assert list(inspect.signature(opcodes.inc_zero_page).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xE6] is opcodes.inc_zero_page


def test_opcode_E6_inc_zero_page_increments_memory():
    """Objective: E6 10 means INC $10, so RAM[$0010] is incremented."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xE6)
    rom.write(0x0001, 0x10)
    bus.write(0x0010, 0x41)

    cpu.reset()
    cpu.step()

    assert bus.read(0x0010) == 0x42
    assert cpu.pc == 0x8002


def test_opcode_E6_inc_zero_page_updates_zero_flag():
    """Objective: 0xFF + 1 becomes 0x00 and sets Zero flag."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xE6)
    rom.write(0x0001, 0x10)
    bus.write(0x0010, 0xFF)

    cpu.reset()
    cpu.step()

    assert bus.read(0x0010) == 0x00
    assert (cpu.p & ZERO_FLAG) != 0
    assert (cpu.p & NEGATIVE_FLAG) == 0


def test_opcode_E6_inc_zero_page_updates_negative_flag():
    """Objective: 0x7F + 1 becomes 0x80 and sets Negative flag."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xE6)
    rom.write(0x0001, 0x10)
    bus.write(0x0010, 0x7F)

    cpu.reset()
    cpu.step()

    assert bus.read(0x0010) == 0x80
    assert (cpu.p & NEGATIVE_FLAG) != 0
    assert (cpu.p & ZERO_FLAG) == 0
