"""Lesson 123: add AND (indirect,X) opcode ``0x21``.

Why this step exists:
AND needs pre-indexed indirect access for pointer tables in zero page, while
pointer resolution remains an addressing concern rather than logical behavior.

In this step, after the earlier AND modes, add exactly the following to
``emulator/cpu/opcodes.py``:

    def and_indirect_x(cpu: CPU):
        addr = indirect_x(cpu)
        value = cpu.bus.read(addr)
        and_a(cpu, value)

    OPCODE_TABLE = {
        ...
        0x21: and_indirect_x,
    }

``emulator/cpu/addressing_modes.py::indirect_x`` fetches the operand, computes
``ptr = (base + cpu.x) & 0xFF``, and reads the little-endian pointer from
``ptr`` and ``(ptr + 1) & 0xFF``.  The handler reads that final address and
calls ``instructions.and_a``.  A and Z/N change; X, Carry/Overflow, pointer
bytes, and target memory are invariant; PC advances two bytes.

Misconception: (indirect,X) applies X before dereferencing, not to the final
16-bit address.  Out of scope: AND (indirect),Y (lesson 124) and all later
ORA/EOR/BIT work.
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


def test_and_indirect_x_handler_exists_and_is_in_opcode_table():
    """Objective: create and_indirect_x(cpu) and add 0x21 to OPCODE_TABLE."""
    assert hasattr(opcodes, "and_indirect_x")
    assert callable(opcodes.and_indirect_x)
    assert list(inspect.signature(opcodes.and_indirect_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x21] is opcodes.and_indirect_x


def test_opcode_21_and_indirect_x_reads_pointed_memory_value():
    """Objective: 21 20 with X=0x04 reads pointer at zero-page $24/$25."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x21)
    rom.write(0x0001, 0x20)
    bus.write(0x0024, 0x00)
    bus.write(0x0025, 0x02)
    bus.write(0x0200, 0x0F)

    cpu.reset()
    cpu.x = 0x04
    cpu.a = 0xF3
    cpu.step()

    assert cpu.a == 0x03
    assert cpu.pc == 0x8002
