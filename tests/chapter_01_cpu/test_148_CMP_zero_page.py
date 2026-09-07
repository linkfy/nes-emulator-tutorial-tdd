"""Lesson 148: add CMP zero-page opcode ``0xC5``.

Why this step exists:
CMP must compare A with memory as well as literals; this form resolves a compact
zero-page address and passes the fetched byte to the common comparison logic.

In this step, lessons 146-147 already provide CMP semantics, import, and
immediate wiring.  Add exactly the following to ``emulator/cpu/opcodes.py``:

    def cmp_zero_page(cpu: CPU):
        addr = zero_page(cpu)
        value = cpu.bus.read(addr)
        cmp(cpu, value)

    OPCODE_TABLE = {
        ...
        0xC5: cmp_zero_page,
    }

The operand names a zero-page location; its bus value, not the address byte,
is compared with A.  C/Z/N may change; A, Overflow, X, Y, and memory remain
invariant; PC advances two bytes.

Misconception: ``C5 10`` compares against ``RAM[$0010]``, not literal
``$10``.  Out of scope: indexed zero page is lesson 149 and wider/indirect CMP
modes are lessons 150-154.
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


def test_cmp_zero_page_handler_exists_and_is_in_opcode_table():
    """Objective: create cmp_zero_page(cpu) and add 0xC5 to OPCODE_TABLE."""
    assert hasattr(opcodes, "cmp_zero_page")
    assert callable(opcodes.cmp_zero_page)
    assert list(inspect.signature(opcodes.cmp_zero_page).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xC5] is opcodes.cmp_zero_page


def test_opcode_C5_cmp_zero_page_reads_memory_value_and_compares():
    """Objective: C5 10 means compare A with RAM[$0010]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xC5)
    rom.write(0x0001, 0x10)
    bus.write(0x0010, 0x10)

    cpu.reset()
    cpu.a = 0x20
    cpu.step()

    assert cpu.a == 0x20
    assert (cpu.p & CARRY_FLAG) != 0
    assert cpu.pc == 0x8002
