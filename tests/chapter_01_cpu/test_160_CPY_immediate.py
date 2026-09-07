"""Lesson 160: expose CPY immediate as opcode ``0xC0``.

Why this step exists:
Immediate CPY exposes Y comparison through CPU execution using a literal byte
without an additional data-memory read.

In this step, after lesson 159 creates the instruction, make these additions
in ``emulator/cpu/opcodes.py``:

    from emulator.cpu.instructions import (..., cpy)

    def cpy_immediate(cpu: CPU):
        cpy(cpu, immediate(cpu))

    OPCODE_TABLE = {
        ...
        0xC0: cpy_immediate,
    }

``emulator/cpu/addressing_modes.py::immediate`` returns ``CPU.fetch_byte()``
as the value.  CPY changes only C/Z/N; Y, memory, and Overflow remain
invariant, and opcode plus operand advances PC two bytes.

Misconception: immediate mode does not identify a bus address, and CPY does
not store the subtraction in Y.  Out of scope: CPY zero-page and absolute
(lessons 161-162).
"""
import inspect

from emulator.bus.cpu_bus import CpuBus
from emulator.cpu import opcodes
from emulator.cpu.cpu import CPU
from emulator.memory.fake_rom import FakeROM
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG


CARRY_FLAG = 1 << 0


def make_cpu_with_rom():
    rom = FakeROM()
    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)
    bus = CpuBus(program_rom=rom)
    return CPU(bus), bus, rom


def test_cpy_immediate_handler_exists_and_is_in_opcode_table():
    """Objective: create cpy_immediate(cpu) and add 0xC0 to OPCODE_TABLE."""
    assert hasattr(opcodes, "cpy_immediate")
    assert callable(opcodes.cpy_immediate)
    assert list(inspect.signature(opcodes.cpy_immediate).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xC0] is opcodes.cpy_immediate


def test_opcode_C0_cpy_immediate_compares_y_with_value():
    """Objective: C0 10 means compare Y with 0x10."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xC0)
    rom.write(0x0001, 0x10)

    cpu.reset()
    cpu.y = 0x20
    cpu.step()

    assert cpu.y == 0x20
    assert (cpu.p & CARRY_FLAG) != 0
    assert cpu.pc == 0x8002


def test_opcode_C0_cpy_immediate_sets_zero_when_equal():
    """Objective: equal values set Zero and Carry."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xC0)
    rom.write(0x0001, 0x10)

    cpu.reset()
    cpu.y = 0x10
    cpu.step()

    assert (cpu.p & ZERO_FLAG) != 0
    assert (cpu.p & CARRY_FLAG) != 0


def test_opcode_C0_cpy_immediate_sets_negative_when_wrapped_result_has_bit_7():
    """Objective: Y=0x01 compared with 0x02 gives wrapped result 0xFF."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xC0)
    rom.write(0x0001, 0x02)

    cpu.reset()
    cpu.y = 0x01
    cpu.step()

    assert (cpu.p & CARRY_FLAG) == 0
    assert (cpu.p & NEGATIVE_FLAG) != 0
