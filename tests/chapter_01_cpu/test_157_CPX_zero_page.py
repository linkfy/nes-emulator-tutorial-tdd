"""Lesson 157: add CPX zero-page opcode ``0xE4``.

Why this step exists:
Zero-page CPX distinguishes a compact memory address from an immediate value
and passes the fetched byte to the existing comparison primitive.

In this step, with ``cpx`` and immediate mode already present, add to
``emulator/cpu/opcodes.py``:

    def cpx_zero_page(cpu: CPU):
        addr = zero_page(cpu)
        value = cpu.bus.read(addr)
        cpx(cpu, value)

    OPCODE_TABLE = {
        ...
        0xE4: cpx_zero_page,
    }

``emulator/cpu/addressing_modes.py::zero_page`` fetches the one-byte address;
the handler must read that address before calling ``instructions.cpx``.  Only
C/Z/N change; X and memory remain invariant, and opcode plus operand advances
PC two bytes.

Misconception: unlike immediate CPX, the operand byte names a memory location
rather than the compared value.  Out of scope: CPX absolute (158) and all CPY
work (159-162).
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


def test_cpx_zero_page_handler_exists_and_is_in_opcode_table():
    """Objective: create cpx_zero_page(cpu) and add 0xE4 to OPCODE_TABLE."""
    assert hasattr(opcodes, "cpx_zero_page")
    assert callable(opcodes.cpx_zero_page)
    assert list(inspect.signature(opcodes.cpx_zero_page).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xE4] is opcodes.cpx_zero_page


def test_opcode_E4_cpx_zero_page_reads_memory_value_and_compares():
    """Objective: E4 10 means compare X with RAM[$0010]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xE4)
    rom.write(0x0001, 0x10)
    bus.write(0x0010, 0x10)

    cpu.reset()
    cpu.x = 0x20
    cpu.step()

    assert cpu.x == 0x20
    assert (cpu.p & CARRY_FLAG) != 0
    assert cpu.pc == 0x8002
