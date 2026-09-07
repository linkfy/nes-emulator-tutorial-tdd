"""Lesson 153: add CMP (indirect,X) opcode ``0xC1``.

Why this step exists:
The (indirect,X) form lets CMP use pre-indexed zero-page pointer tables while
leaving pointer resolution to the addressing helper.

In this step, after lessons 146-152, add exactly the following to
``emulator/cpu/opcodes.py``:

    def cmp_indirect_x(cpu: CPU):
        addr = indirect_x(cpu)
        value = cpu.bus.read(addr)
        cmp(cpu, value)

    OPCODE_TABLE = {
        ...
        0xC1: cmp_indirect_x,
    }

``emulator/cpu/addressing_modes.py::indirect_x`` fetches the operand, computes
``(base + X) & 0xFF``, and reads a little-endian pointer whose high-byte lookup
also wraps in zero page.  The handler then reads the pointed value.  Only
C/Z/N change; A, X, pointer bytes, target memory, and Overflow are invariant;
the opcode and operand advance PC two bytes.

Misconception: X is applied before dereferencing, not to the final 16-bit
address.  Out of scope: CMP (indirect),Y (154) and CPX/CPY (155-162).
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


def test_cmp_indirect_x_handler_exists_and_is_in_opcode_table():
    """Objective: create cmp_indirect_x(cpu) and add 0xC1 to OPCODE_TABLE."""
    assert hasattr(opcodes, "cmp_indirect_x")
    assert callable(opcodes.cmp_indirect_x)
    assert list(inspect.signature(opcodes.cmp_indirect_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xC1] is opcodes.cmp_indirect_x


def test_opcode_C1_cmp_indirect_x_reads_pointed_memory_value():
    """Objective: C1 20 with X=0x04 reads pointer at zero-page $24/$25."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xC1)
    rom.write(0x0001, 0x20)
    bus.write(0x0024, 0x00)
    bus.write(0x0025, 0x02)
    bus.write(0x0200, 0x10)

    cpu.reset()
    cpu.x = 0x04
    cpu.a = 0x20
    cpu.step()

    assert (cpu.p & CARRY_FLAG) != 0
    assert cpu.pc == 0x8002
