"""
Test 025 — Add absolute,X STA ($9D).

File to update:
    emulator/cpu/opcodes.py

Locations:
    opcodes.sta_absolute_x
    opcodes.OPCODE_TABLE[$9D]

Why this step exists:
This applies the already-tested `absolute_x` address calculation to stores. The
opcode layer selects X indexing; `sta` remains independent of addressing mode.

Complete example implementation:

    # emulator/cpu/opcodes.py
    def sta_absolute_x(cpu) -> None:
        address = absolute_x(cpu)
        sta(cpu, address)


    OPCODE_TABLE = {
        # Preserve existing entries.
        0x9D: sta_absolute_x,
    }

Important invariants:
    - two operand bytes form the base address before X is added
    - the full indexed address is used; indexing is not zero-page wrapped
    - the handler stores A and consumes three instruction bytes
    - STA does not update flags

Common misconception:
Absolute,X does not mask the sum to eight bits. That wrapping rule belongs to
zero-page,X, not to `$hhhh,X`.

Out of scope:
    - absolute,Y and indirect STA opcodes
    - page-cross cycle behavior
    - changes to absolute_x or sta
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


def test_sta_absolute_x_handler_exists_and_is_in_opcode_table():
    """
    Objective:
    Create sta_absolute_x(cpu) and add 0x9D to OPCODE_TABLE.
    """
    assert hasattr(opcodes, "sta_absolute_x")
    assert callable(opcodes.sta_absolute_x)
    assert list(inspect.signature(opcodes.sta_absolute_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x9D] is opcodes.sta_absolute_x


def test_opcode_9D_sta_absolute_x_stores_register_a():
    """
    Objective:
    9D 00 02 means STA $0200,X.
    If X is 0x04, store A into RAM $0204.
    """
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x9D)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)

    cpu.reset()
    cpu.a = 0x42
    cpu.x = 0x04
    cpu.step()

    assert bus.read(0x0204) == 0x42
    assert cpu.pc == 0x8003
