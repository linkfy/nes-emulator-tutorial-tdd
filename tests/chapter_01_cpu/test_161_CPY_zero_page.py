"""Lesson 161: add CPY zero-page opcode ``0xC4``.

Why this step exists:
Zero-page CPY interprets its operand as a compact memory address and compares
Y with the byte read there through the shared CPY primitive.

In this step, lessons 159-160 already provide ``instructions.cpy``, its opcode
import, and immediate CPY.  Add exactly the following to
``emulator/cpu/opcodes.py``:

    def cpy_zero_page(cpu: CPU):
        addr = zero_page(cpu)
        value = cpu.bus.read(addr)
        cpy(cpu, value)

    OPCODE_TABLE = {
        ...
        0xC4: cpy_zero_page,
    }

``emulator/cpu/addressing_modes.py::zero_page`` consumes the one-
byte operand as an address; the handler then reads that address and delegates
flag semantics to ``emulator/cpu/instructions.py::cpy``.

Invariants: Y and memory are unchanged; CPY updates only C/Z/N, and opcode plus
operand advances PC by two bytes.  Misconception: the operand is not the value
compared with Y; it identifies the zero-page byte containing that value.

Out of scope: CPY absolute ``0xCC`` is lesson 162.  CMP/CPX and CPY immediate
belong to lessons 146-160.
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


def test_cpy_zero_page_handler_exists_and_is_in_opcode_table():
    """Objective: create cpy_zero_page(cpu) and add 0xC4 to OPCODE_TABLE."""
    assert hasattr(opcodes, "cpy_zero_page")
    assert callable(opcodes.cpy_zero_page)
    assert list(inspect.signature(opcodes.cpy_zero_page).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xC4] is opcodes.cpy_zero_page


def test_opcode_C4_cpy_zero_page_reads_memory_value_and_compares():
    """Objective: C4 10 means compare Y with RAM[$0010]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xC4)
    rom.write(0x0001, 0x10)
    bus.write(0x0010, 0x10)

    cpu.reset()
    cpu.y = 0x20
    cpu.step()

    assert cpu.y == 0x20
    assert (cpu.p & CARRY_FLAG) != 0
    assert cpu.pc == 0x8002
