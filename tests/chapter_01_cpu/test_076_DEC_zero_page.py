"""Lesson 076: add DEC and wire Zero Page (`0xC6`).

In this step, add `emulator/cpu/instructions.py:dec` and the zero-page
import, handler, and table wiring in `emulator/cpu/opcodes.py`. Unlike INC,
there is no separate DEC primitive step.

Why this step exists:
Establish one memory decrement primitive, then expose its first
addressing mode. Later DEC handlers need only resolve an effective address.

Suggested implementation in `emulator/cpu/instructions.py`, after
`inc`:

    def dec(cpu: CPU, address: int):
        value = cpu.bus.read(address)
        result = value - 1
        result_8 = result & 0xFF

        # Set flags
        cpu.flags.set_negative_flag((result_8 & 0b1000_0000) != 0)
        cpu.flags.set_zero_flag(result_8 == 0)

        # Set value on address
        cpu.bus.write(address, result_8)

Complete lesson-076 wiring in `emulator/cpu/opcodes.py`:

    from emulator.cpu.instructions import lda, sta, ldx, stx, ldy, sty, tax, txa, tay, tya, adc, sbc, inc, dec

    def dec_zero_page(cpu: CPU):
        addr = zero_page(cpu)
        dec(cpu, addr)

Add this exact entry to the existing `OPCODE_TABLE`:

    0xC6: dec_zero_page,

Invariants: DEC receives an address and accesses memory through the bus; masking
makes `$00 - 1 == $FF`; Zero and Negative reflect the stored byte; Carry,
Overflow, and A/X/Y are preserved; zero-page consumes one operand byte and the
whole instruction is two bytes.

Misconception: DEC is not SBC. It neither consumes nor updates Carry and it does
not operate on A; the zero-page operand names the memory location.

Out of scope: zero-page-X, absolute, and absolute-X DEC wiring belongs to
lessons 077-079.
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


def test_dec_zero_page_handler_exists_and_is_in_opcode_table():
    """Objective: create dec_zero_page(cpu) and add 0xC6 to OPCODE_TABLE."""
    assert hasattr(opcodes, "dec_zero_page")
    assert callable(opcodes.dec_zero_page)
    assert list(inspect.signature(opcodes.dec_zero_page).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xC6] is opcodes.dec_zero_page


def test_opcode_C6_dec_zero_page_decrements_memory():
    """Objective: C6 10 means DEC $10, so RAM[$0010] is decremented."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xC6)
    rom.write(0x0001, 0x10)
    bus.write(0x0010, 0x42)

    cpu.reset()
    cpu.step()

    assert bus.read(0x0010) == 0x41
    assert cpu.pc == 0x8002


def test_opcode_C6_dec_zero_page_updates_zero_flag():
    """Objective: 0x01 - 1 becomes 0x00 and sets Zero flag."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xC6)
    rom.write(0x0001, 0x10)
    bus.write(0x0010, 0x01)

    cpu.reset()
    cpu.step()

    assert bus.read(0x0010) == 0x00
    assert (cpu.p & ZERO_FLAG) != 0
    assert (cpu.p & NEGATIVE_FLAG) == 0


def test_opcode_C6_dec_zero_page_wraps_to_ff_and_sets_negative_flag():
    """Objective: 0x00 - 1 becomes 0xFF and sets Negative flag."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xC6)
    rom.write(0x0001, 0x10)
    bus.write(0x0010, 0x00)

    cpu.reset()
    cpu.step()

    assert bus.read(0x0010) == 0xFF
    assert (cpu.p & NEGATIVE_FLAG) != 0
    assert (cpu.p & ZERO_FLAG) == 0
