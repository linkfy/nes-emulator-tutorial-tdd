"""Lesson 149: add CMP zero-page,X opcode ``0xD5``.

Why this step exists:
Indexed zero-page CMP supports compact table lookups and confirms that X
addition wraps within zero page before the comparison value is read.

In this step, building only on lessons 146-148, add exactly the following to
``emulator/cpu/opcodes.py``:

    def cmp_zero_page_x(cpu: CPU):
        addr = zero_page_x(cpu)
        value = cpu.bus.read(addr)
        cmp(cpu, value)

    OPCODE_TABLE = {
        ...
        0xD5: cmp_zero_page_x,
    }

``addressing_modes.zero_page_x`` computes ``(operand + X) & 0xFF`` before the
bus read.  C/Z/N may change; A, Overflow, X, Y, and memory remain invariant;
opcode plus operand advances PC two bytes.

Misconception: indexing past ``$FF`` does not carry into page one; it wraps
within zero page.  Out of scope: absolute CMP starts in lesson 150, with its
indexed and indirect variants deferred to lessons 151-154.
"""
import inspect

from emulator.bus.cpu_bus import CpuBus
from emulator.cpu import opcodes
from emulator.cpu.cpu import CPU
from emulator.memory.fake_rom import FakeROM


CARRY_FLAG = 1 << 0


def make_cpu_with_rom():
    rom = FakeROM()
    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)
    bus = CpuBus(program_rom=rom)
    return CPU(bus), bus, rom


def test_cmp_zero_page_x_handler_exists_and_is_in_opcode_table():
    """Objective: create cmp_zero_page_x(cpu) and add 0xD5 to OPCODE_TABLE."""
    assert hasattr(opcodes, "cmp_zero_page_x")
    assert callable(opcodes.cmp_zero_page_x)
    assert list(inspect.signature(opcodes.cmp_zero_page_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xD5] is opcodes.cmp_zero_page_x


def test_opcode_D5_cmp_zero_page_x_reads_indexed_memory_value():
    """Objective: D5 20 with X=0x04 compares A with RAM[$0024]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xD5)
    rom.write(0x0001, 0x20)
    bus.write(0x0024, 0x10)

    cpu.reset()
    cpu.x = 0x04
    cpu.a = 0x20
    cpu.step()

    assert (cpu.p & CARRY_FLAG) != 0
    assert cpu.pc == 0x8002


def test_opcode_D5_cmp_zero_page_x_wraps_zero_page_address():
    """Objective: base=0xFE and X=0x03 reads RAM[$0001]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xD5)
    rom.write(0x0001, 0xFE)
    bus.write(0x0001, 0x10)

    cpu.reset()
    cpu.x = 0x03
    cpu.a = 0x20
    cpu.step()

    assert (cpu.p & CARRY_FLAG) != 0
    assert cpu.pc == 0x8002
