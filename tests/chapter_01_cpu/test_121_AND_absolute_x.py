"""Lesson 121: add AND absolute,X opcode ``0x3D``.

Why this step exists:
Programs need AND over table-like memory addressed by a full base plus X; this
step connects that effective-address calculation to the shared AND behavior.

In this step, with AND semantics and the unindexed absolute handler already
present, add exactly this incremental code to ``emulator/cpu/opcodes.py``:

    def and_absolute_x(cpu: CPU):
        addr = absolute_x(cpu)
        value = cpu.bus.read(addr)
        and_a(cpu, value)

    OPCODE_TABLE = {
        ...
        0x3D: and_absolute_x,
    }

``emulator/cpu/addressing_modes.py::absolute_x`` fetches the little-endian
base word, then adds ``cpu.x``.  The handler reads the resolved address and
passes its value to ``instructions.and_a``.  A and Z/N change; X,
Carry/Overflow, and memory are invariant; opcode plus word advances PC three
bytes.

Misconception: X indexes the decoded address, not either operand byte or the
loaded value.  Out of scope: AND absolute,Y and indirect modes (lessons
122-124), plus ORA/EOR/BIT work in lessons 125-145.
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


def test_and_absolute_x_handler_exists_and_is_in_opcode_table():
    """Objective: create and_absolute_x(cpu) and add 0x3D to OPCODE_TABLE."""
    assert hasattr(opcodes, "and_absolute_x")
    assert callable(opcodes.and_absolute_x)
    assert list(inspect.signature(opcodes.and_absolute_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x3D] is opcodes.and_absolute_x


def test_opcode_3D_and_absolute_x_reads_indexed_memory_value():
    """Objective: 3D 00 02 with X=0x04 reads RAM[$0204]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x3D)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0204, 0x0F)

    cpu.reset()
    cpu.x = 0x04
    cpu.a = 0xF3
    cpu.step()

    assert cpu.a == 0x03
    assert cpu.pc == 0x8003
