"""Lesson 137: add EOR zero-page,X opcode ``0x55``.

Why this step exists:
This adds indexed zero-page EOR and verifies that X indexing wraps within the
page before the addressed value is combined with the accumulator.

In this step, following lesson 136, add exactly the following to
``emulator/cpu/opcodes.py``:

    def eor_zero_page_x(cpu: CPU):
        addr = zero_page_x(cpu)
        value = cpu.bus.read(addr)
        or_e(cpu, value)

    OPCODE_TABLE = {
        ...
        0x55: eor_zero_page_x,
    }

``emulator/cpu/addressing_modes.py::zero_page_x`` fetches the base and computes
``(base + cpu.x) & 0xFF`` before the handler reads data.  Thus indexing stays
inside page zero.  A and Z/N may change; Carry/Overflow, memory, X, and Y are
invariant; opcode plus operand advances PC two bytes.

Misconception: an overflow such as ``$FE + $03`` wraps to ``$01``, not
``$0101``.  Out of scope: absolute and indirect EOR modes (138-142) and BIT
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


def test_eor_zero_page_x_handler_exists_and_is_in_opcode_table():
    """Objective: create eor_zero_page_x(cpu) and add 0x55 to OPCODE_TABLE."""
    assert hasattr(opcodes, "eor_zero_page_x")
    assert callable(opcodes.eor_zero_page_x)
    assert list(inspect.signature(opcodes.eor_zero_page_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x55] is opcodes.eor_zero_page_x


def test_opcode_55_eor_zero_page_x_reads_indexed_memory_value():
    """Objective: 55 20 with X=0x04 reads RAM[$0024]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x55)
    rom.write(0x0001, 0x20)
    bus.write(0x0024, 0x0F)

    cpu.reset()
    cpu.x = 0x04
    cpu.a = 0xF0
    cpu.step()

    assert cpu.a == 0xFF
    assert cpu.pc == 0x8002


def test_opcode_55_eor_zero_page_x_wraps_zero_page_address():
    """Objective: base=0xFE and X=0x03 reads RAM[$0001]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x55)
    rom.write(0x0001, 0xFE)
    bus.write(0x0001, 0x0F)

    cpu.reset()
    cpu.x = 0x03
    cpu.a = 0xF0
    cpu.step()

    assert cpu.a == 0xFF
    assert cpu.pc == 0x8002
