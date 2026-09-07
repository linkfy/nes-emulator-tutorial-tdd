"""Lesson 136: add EOR zero-page opcode ``0x45``.

Why this step exists:
EOR needs a compact memory form that interprets its operand as a zero-page
address, reads that location, and applies the common exclusive-OR behavior.

In this step, ``or_e`` and EOR immediate already exist.  Add exactly the
following to ``emulator/cpu/opcodes.py``:

    def eor_zero_page(cpu: CPU):
        addr = zero_page(cpu)
        value = cpu.bus.read(addr)
        or_e(cpu, value)

    OPCODE_TABLE = {
        ...
        0x45: eor_zero_page,
    }

``emulator/cpu/addressing_modes.py::zero_page`` fetches the one-byte address;
the handler performs the separate data read and passes that value to
``instructions.or_e``.  A and Z/N may change; Carry/Overflow, memory, X, and Y
remain invariant; opcode plus operand advances PC two bytes.

Misconception: ``$nn`` is an address in page zero, not the literal XOR value.
Out of scope: indexed and wider EOR modes (137-142) and BIT (143-145).
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


def test_eor_zero_page_handler_exists_and_is_in_opcode_table():
    """Objective: create eor_zero_page(cpu) and add 0x45 to OPCODE_TABLE."""
    assert hasattr(opcodes, "eor_zero_page")
    assert callable(opcodes.eor_zero_page)
    assert list(inspect.signature(opcodes.eor_zero_page).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x45] is opcodes.eor_zero_page


def test_opcode_45_eor_zero_page_reads_memory_value_and_updates_a():
    """Objective: 45 10 means EOR value at RAM[$0010]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x45)
    rom.write(0x0001, 0x10)
    bus.write(0x0010, 0x0F)

    cpu.reset()
    cpu.a = 0xF0
    cpu.step()

    assert cpu.a == 0xFF
    assert cpu.pc == 0x8002
