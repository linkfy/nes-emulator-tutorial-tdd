"""Lesson 127: add ORA zero-page opcode ``0x05``.

Why this step exists:
ORA must distinguish a zero-page address operand from literal data, read the
addressed byte, and then apply the already-defined inclusive-OR behavior.

In this step, with ``or_a`` imported by lesson 126, the complete incremental
implementation in
``emulator/cpu/opcodes.py`` is:

    def ora_zero_page(cpu: CPU):
        addr = zero_page(cpu)
        value = cpu.bus.read(addr)
        or_a(cpu, value)

    OPCODE_TABLE = {
        ...
        0x05: ora_zero_page,
    }

``emulator/cpu/addressing_modes.py::zero_page`` fetches the one-byte address,
then the handler reads its value before calling ``instructions.or_a``.  A and
Z/N change; Carry/Overflow and memory remain invariant; ``05 10`` reads
``$0010`` and advances PC two bytes.

Misconception: pass the byte stored at ``$0010`` to ``or_a``, not address
``0x10``, and do not write the result back to memory.  Out of scope:
zero-page,X through indirect,Y ORA modes (lessons 128-133).
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


def test_ora_zero_page_handler_exists_and_is_in_opcode_table():
    """Objective: create ora_zero_page(cpu) and add 0x05 to OPCODE_TABLE."""
    assert hasattr(opcodes, "ora_zero_page")
    assert callable(opcodes.ora_zero_page)
    assert list(inspect.signature(opcodes.ora_zero_page).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x05] is opcodes.ora_zero_page


def test_opcode_05_ora_zero_page_reads_memory_value_and_updates_a():
    """Objective: 05 10 means ORA value at RAM[$0010]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x05)
    rom.write(0x0001, 0x10)
    bus.write(0x0010, 0x0F)

    cpu.reset()
    cpu.a = 0xF0
    cpu.step()

    assert cpu.a == 0xFF
    assert cpu.pc == 0x8002
