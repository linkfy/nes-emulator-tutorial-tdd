"""Lesson 118: add AND zero-page opcode ``0x25``.

In this step, with ``and_a`` imported by lesson 117, add only the zero-page
handler and table entry in ``emulator/cpu/opcodes.py``.

Why this step exists:
AND must also consume values from memory; zero-page mode verifies that the
operand byte is treated as an address rather than as an immediate value.

Suggested implementation:

    def and_zero_page(cpu: CPU):
        addr = zero_page(cpu)
        value = cpu.bus.read(addr)
        and_a(cpu, value)

    OPCODE_TABLE = {
        ...
        0x25: and_zero_page,
    }

``addressing_modes.zero_page`` fetches the one-byte address; unlike immediate
mode, the handler must read the value at that address before calling
``instructions.and_a``.  ``25 10`` uses ``cpu.bus[$0010]``, changes A and
Z/N, preserves Carry/Overflow and memory, and advances PC two bytes.

Misconception: neither pass address ``0x10`` directly to ``and_a`` nor write
the result back to ``$0010``; AND is not a read/modify/write instruction.
Out of scope: zero-page,X and wider AND modes (lessons 119-124).
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


def test_and_zero_page_handler_exists_and_is_in_opcode_table():
    """Objective: create and_zero_page(cpu) and add 0x25 to OPCODE_TABLE."""
    assert hasattr(opcodes, "and_zero_page")
    assert callable(opcodes.and_zero_page)
    assert list(inspect.signature(opcodes.and_zero_page).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x25] is opcodes.and_zero_page


def test_opcode_25_and_zero_page_reads_memory_value_and_updates_a():
    """Objective: 25 10 means AND value at RAM[$0010]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x25)
    rom.write(0x0001, 0x10)
    bus.write(0x0010, 0x0F)

    cpu.reset()
    cpu.a = 0xF3
    cpu.step()

    assert cpu.a == 0x03
    assert cpu.pc == 0x8002
