"""
Test 028 — Add indirect-indexed STA ($91, written `(d),Y`).

File to update:
    emulator/cpu/opcodes.py

Locations:
    opcodes.sta_indirect_y
    opcodes.OPCODE_TABLE[$91]

Why this step exists:
This completes the STA modes in this sequence by reusing Test 021's `indirect_y`
address resolution. The handler obtains the final Y-indexed destination and delegates
the write to `sta`.

Complete example implementation:

    # emulator/cpu/opcodes.py
    def sta_indirect_y(cpu) -> None:
        address = indirect_y(cpu)
        sta(cpu, address)


    OPCODE_TABLE = {
        # Preserve existing entries.
        0x91: sta_indirect_y,
    }

Important invariants:
    - the zero-page pointer is read before Y is added
    - the pointer high-byte read wraps from $00FF to $0000
    - Y indexes the assembled 16-bit destination
    - $91 stores A without changing flags

Common misconception:
`(d),Y` does not index the zero-page pointer location. Read the pointer at `d` first,
then add Y to the resulting address.

Out of scope:
    - changes to indirect_y or sta
    - page-cross cycle behavior
    - refactoring the STA handlers into a generic helper
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


def test_sta_indirect_y_handler_exists_and_is_in_opcode_table():
    """
    Objective:
    Create sta_indirect_y(cpu) and add 0x91 to OPCODE_TABLE.
    """
    assert hasattr(opcodes, "sta_indirect_y")
    assert callable(opcodes.sta_indirect_y)
    assert list(inspect.signature(opcodes.sta_indirect_y).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x91] is opcodes.sta_indirect_y


def test_opcode_91_sta_indirect_y_stores_register_a():
    """
    Objective:
    91 20 means STA ($20),Y.
    If RAM[$0020-$0021] points to $0200 and Y is 0x04,
    store A into RAM $0204.
    """
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x91)
    rom.write(0x0001, 0x20)
    bus.write(0x0020, 0x00)
    bus.write(0x0021, 0x02)

    cpu.reset()
    cpu.a = 0x42
    cpu.y = 0x04
    cpu.step()

    assert bus.read(0x0204) == 0x42
    assert cpu.pc == 0x8002
