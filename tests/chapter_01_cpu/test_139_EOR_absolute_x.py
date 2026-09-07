"""Lesson 139: add EOR absolute,X opcode ``0x5D``.

Why this step exists:
Programs need EOR over full-address data indexed by X; this step connects that
effective-address form to the already-tested exclusive-OR semantics.

In this step, lesson 138 supplies unindexed absolute EOR.  Add exactly the
following to ``emulator/cpu/opcodes.py``:

    def eor_absolute_x(cpu: CPU):
        addr = absolute_x(cpu)
        value = cpu.bus.read(addr)
        or_e(cpu, value)

    OPCODE_TABLE = {
        ...
        0x5D: eor_absolute_x,
    }

``emulator/cpu/addressing_modes.py::absolute_x`` fetches the little-endian base
word and then adds X; this helper does not apply an additional
``& 0xFFFF`` mask.  The handler reads the indexed location and calls
``instructions.or_e``.  A and Z/N may change; Carry/Overflow, memory, X, and Y
remain invariant; PC advances three bytes.

Misconception: X indexes the decoded 16-bit address, not its low operand byte.
Out of scope: absolute,Y and indirect EOR (140-142) and BIT (143-145).
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


def test_eor_absolute_x_handler_exists_and_is_in_opcode_table():
    """Objective: create eor_absolute_x(cpu) and add 0x5D to OPCODE_TABLE."""
    assert hasattr(opcodes, "eor_absolute_x")
    assert callable(opcodes.eor_absolute_x)
    assert list(inspect.signature(opcodes.eor_absolute_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x5D] is opcodes.eor_absolute_x


def test_opcode_5D_eor_absolute_x_reads_indexed_memory_value():
    """Objective: 5D 00 02 with X=0x04 reads RAM[$0204]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x5D)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0204, 0x0F)

    cpu.reset()
    cpu.x = 0x04
    cpu.a = 0xF0
    cpu.step()

    assert cpu.a == 0xFF
    assert cpu.pc == 0x8003
