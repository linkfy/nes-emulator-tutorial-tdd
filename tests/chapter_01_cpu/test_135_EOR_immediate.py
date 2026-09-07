"""Lesson 135: expose EOR immediate opcode ``0x49``.

Why this step exists:
The immediate form makes EOR executable with a literal operand and establishes
the opcode-layer delegation to the shared exclusive-OR primitive.

In this step, after lesson 134 introduces ``or_e``, add ``or_e`` to the
instruction import and add the following in ``emulator/cpu/opcodes.py``:

    def eor_immediate(cpu: CPU):
        or_e(cpu, immediate(cpu))

    OPCODE_TABLE = {
        ...
        0x49: eor_immediate,
    }

``emulator/cpu/addressing_modes.py::immediate`` calls ``CPU.fetch_byte`` and
returns the operand value while advancing PC.  No second bus read is needed by
the handler.  ``instructions.or_e`` writes A and updates Z/N; Carry/Overflow,
memory, X, and Y remain invariant, and opcode plus operand advances PC twice.

Misconception: immediate mode supplies a value, not an address to dereference.
Out of scope: all memory-addressed EOR handlers (lessons 136-142) and BIT
(143-145).
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


def test_eor_immediate_handler_exists_and_is_in_opcode_table():
    """Objective: create eor_immediate(cpu) and add 0x49 to OPCODE_TABLE."""
    assert hasattr(opcodes, "eor_immediate")
    assert callable(opcodes.eor_immediate)
    assert list(inspect.signature(opcodes.eor_immediate).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x49] is opcodes.eor_immediate


def test_opcode_49_eor_immediate_updates_accumulator():
    """Objective: 49 0F means EOR #$0F, so A becomes A ^ 0x0F."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x49)
    rom.write(0x0001, 0x0F)

    cpu.reset()
    cpu.a = 0xF0
    cpu.step()

    assert cpu.a == 0xFF
    assert cpu.pc == 0x8002


def test_opcode_49_eor_immediate_updates_zero_flag():
    """Objective: equal operands produce result 0 and set Zero flag."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x49)
    rom.write(0x0001, 0xAA)

    cpu.reset()
    cpu.a = 0xAA
    cpu.step()

    assert cpu.a == 0x00
    assert (cpu.p & ZERO_FLAG) != 0
    assert (cpu.p & NEGATIVE_FLAG) == 0


def test_opcode_49_eor_immediate_updates_negative_flag():
    """Objective: result bit 7 sets Negative flag."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x49)
    rom.write(0x0001, 0x81)

    cpu.reset()
    cpu.a = 0x01
    cpu.step()

    assert cpu.a == 0x80
    assert (cpu.p & NEGATIVE_FLAG) != 0
    assert (cpu.p & ZERO_FLAG) == 0
