"""Lesson 138: add EOR absolute opcode ``0x4D``.

Why this step exists:
Absolute EOR allows exclusive OR against any CPU memory location while keeping
little-endian address decoding outside the instruction primitive.

In this step, after the two zero-page forms, add exactly the following to
``emulator/cpu/opcodes.py``:

    def eor_absolute(cpu: CPU):
        addr = absolute(cpu)
        value = cpu.bus.read(addr)
        or_e(cpu, value)

    OPCODE_TABLE = {
        ...
        0x4D: eor_absolute,
    }

``emulator/cpu/addressing_modes.py::absolute`` uses ``CPU.fetch_word`` to
decode low byte then high byte.  The handler reads the resulting address and
delegates the XOR and Z/N flags to ``instructions.or_e``.  Carry/Overflow,
memory, X, and Y remain invariant; opcode plus word advances PC three bytes.

Misconception: the little-endian word is the location of the value, not the
value itself.  Out of scope: indexed/indirect EOR modes (139-142) and BIT
(143-145).
"""
import inspect

from emulator.bus.cpu_bus import CpuBus
from emulator.cpu import opcodes
from emulator.cpu.cpu import CPU
from emulator.memory.fake_rom import FakeROM


def make_cpu_with_rom():
    rom = FakeROM()
    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)
    bus = CpuBus(program_rom=rom)
    return CPU(bus), bus, rom


def test_eor_absolute_handler_exists_and_is_in_opcode_table():
    """Objective: create eor_absolute(cpu) and add 0x4D to OPCODE_TABLE."""
    assert hasattr(opcodes, "eor_absolute")
    assert callable(opcodes.eor_absolute)
    assert list(inspect.signature(opcodes.eor_absolute).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x4D] is opcodes.eor_absolute


def test_opcode_4D_eor_absolute_reads_memory_value():
    """Objective: 4D 00 02 means EOR value at RAM[$0200]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x4D)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0200, 0x0F)

    cpu.reset()
    cpu.a = 0xF0
    cpu.step()

    assert cpu.a == 0xFF
    assert cpu.pc == 0x8003
