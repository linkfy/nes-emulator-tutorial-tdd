"""Lesson 147: add CMP immediate opcode ``0xC9``.

Why this step exists:
The immediate form first exposes CMP through CPU execution, comparing A with a
literal byte while leaving all comparison flag logic in the shared primitive.

In this step, lesson 146 already adds ``cmp``.  As CMP's first opcode lesson,
add its import and exactly the following handler/table entry in
``emulator/cpu/opcodes.py``:

    from emulator.cpu.instructions import (..., cmp)

    def cmp_immediate(cpu: CPU):
        cmp(cpu, immediate(cpu))

    OPCODE_TABLE = {
        ...
        0xC9: cmp_immediate,
    }

``addressing_modes.immediate`` returns the fetched operand value directly, so
there is no data-memory read.  C/Z/N may change; A, Overflow, X, Y, and memory
are invariant; opcode plus operand advances PC two bytes.

Misconception: immediate CMP does not treat its operand as an address or store
the subtraction.  Out of scope: CMP memory modes are lessons 148-154; CPX and
CPY remain later lessons.
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


def test_cmp_immediate_handler_exists_and_is_in_opcode_table():
    """Objective: create cmp_immediate(cpu) and add 0xC9 to OPCODE_TABLE."""
    assert hasattr(opcodes, "cmp_immediate")
    assert callable(opcodes.cmp_immediate)
    assert list(inspect.signature(opcodes.cmp_immediate).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xC9] is opcodes.cmp_immediate


def test_opcode_C9_cmp_immediate_compares_a_with_value():
    """Objective: C9 10 means compare A with 0x10."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xC9)
    rom.write(0x0001, 0x10)

    cpu.reset()
    cpu.a = 0x20
    cpu.step()

    assert cpu.a == 0x20
    assert (cpu.p & CARRY_FLAG) != 0
    assert cpu.pc == 0x8002


def test_opcode_C9_cmp_immediate_sets_zero_when_equal():
    """Objective: equal values set Zero and Carry."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xC9)
    rom.write(0x0001, 0x10)

    cpu.reset()
    cpu.a = 0x10
    cpu.step()

    assert (cpu.p & ZERO_FLAG) != 0
    assert (cpu.p & CARRY_FLAG) != 0


def test_opcode_C9_cmp_immediate_sets_negative_when_wrapped_result_has_bit_7():
    """Objective: A=0x01 compared with 0x02 gives wrapped result 0xFF."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xC9)
    rom.write(0x0001, 0x02)

    cpu.reset()
    cpu.a = 0x01
    cpu.step()

    assert (cpu.p & CARRY_FLAG) == 0
    assert (cpu.p & NEGATIVE_FLAG) != 0
