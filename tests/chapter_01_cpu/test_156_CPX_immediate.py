"""Lesson 156: expose CPX immediate as opcode ``0xE0``.

Why this step exists:
Immediate CPX first exposes the comparison through CPU execution with a
literal value and no data-memory lookup.

In this step, after lesson 155 creates the instruction, make these additions
in ``emulator/cpu/opcodes.py``:

    from emulator.cpu.instructions import (..., cpx)

    def cpx_immediate(cpu: CPU):
        cpx(cpu, immediate(cpu))

    OPCODE_TABLE = {
        ...
        0xE0: cpx_immediate,
    }

``emulator/cpu/addressing_modes.py::immediate`` returns ``CPU.fetch_byte()``
directly as the compared value.  CPX changes only C/Z/N; X, memory, and
Overflow remain invariant, and opcode plus operand advances PC two bytes.

Misconception: the immediate byte is a value, not an address requiring a bus
read.  Out of scope: CPX zero-page and absolute (157-158), and every CPY
symbol and opcode (159-162).
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


def test_cpx_immediate_handler_exists_and_is_in_opcode_table():
    """Objective: create cpx_immediate(cpu) and add 0xE0 to OPCODE_TABLE."""
    assert hasattr(opcodes, "cpx_immediate")
    assert callable(opcodes.cpx_immediate)
    assert list(inspect.signature(opcodes.cpx_immediate).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xE0] is opcodes.cpx_immediate


def test_opcode_E0_cpx_immediate_compares_x_with_value():
    """Objective: E0 10 means compare X with 0x10."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xE0)
    rom.write(0x0001, 0x10)

    cpu.reset()
    cpu.x = 0x20
    cpu.step()

    assert cpu.x == 0x20
    assert (cpu.p & CARRY_FLAG) != 0
    assert cpu.pc == 0x8002


def test_opcode_E0_cpx_immediate_sets_zero_when_equal():
    """Objective: equal values set Zero and Carry."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xE0)
    rom.write(0x0001, 0x10)

    cpu.reset()
    cpu.x = 0x10
    cpu.step()

    assert (cpu.p & ZERO_FLAG) != 0
    assert (cpu.p & CARRY_FLAG) != 0


def test_opcode_E0_cpx_immediate_sets_negative_when_wrapped_result_has_bit_7():
    """Objective: X=0x01 compared with 0x02 gives wrapped result 0xFF."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xE0)
    rom.write(0x0001, 0x02)

    cpu.reset()
    cpu.x = 0x01
    cpu.step()

    assert (cpu.p & CARRY_FLAG) == 0
    assert (cpu.p & NEGATIVE_FLAG) != 0
