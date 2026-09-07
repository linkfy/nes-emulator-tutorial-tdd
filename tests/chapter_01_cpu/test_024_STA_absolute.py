"""
Test 024 — Add absolute STA ($8D).

File to update:
    emulator/cpu/opcodes.py

Locations:
    opcodes.sta_absolute
    opcodes.OPCODE_TABLE[$8D]

Why this step exists:
STA now needs a full 16-bit destination. The lesson reuses `absolute` and `sta` to
demonstrate that changing operand width belongs in addressing, not in the store
instruction itself.

Complete example implementation:

    # emulator/cpu/opcodes.py
    def sta_absolute(cpu) -> None:
        address = absolute(cpu)
        sta(cpu, address)


    OPCODE_TABLE = {
        # Preserve existing entries.
        0x8D: sta_absolute,
    }

Important invariants:
    - absolute consumes low byte then high byte
    - the resulting 16-bit address is passed directly to sta
    - $8D advances PC by three bytes including the opcode
    - storing A leaves Zero and Negative unchanged

Common misconception:
The two operand bytes encode one little-endian destination address; they are not two
values to write and must not be read as big-endian.

Out of scope:
    - indexed absolute STA opcodes
    - changes to absolute or sta
    - cycle timing
"""
import inspect

from emulator.bus.cpu_bus import CpuBus
from emulator.cpu import opcodes
from emulator.cpu.cpu import CPU
from emulator.memory.fake_rom import FakeROM
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG


def make_cpu_with_rom():
    rom = FakeROM()
    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)
    bus = CpuBus(program_rom=rom)
    return CPU(bus), bus, rom


def test_sta_absolute_handler_exists_and_is_in_opcode_table():
    """
    Objective:
    Create in opcodes.py:
        def sta_absolute(cpu):
            addr = absolute(cpu)
            sta(cpu, addr)

    Then add:
        0x8D: sta_absolute
    """
    assert hasattr(opcodes, "sta_absolute")
    assert callable(opcodes.sta_absolute)
    assert list(inspect.signature(opcodes.sta_absolute).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x8D] is opcodes.sta_absolute


def test_opcode_8D_sta_absolute_stores_register_a():
    """
    Objective:
    8D 00 02 means STA $0200.
    Store register A into RAM $0200.
    """
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x8D)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)

    cpu.reset()
    cpu.a = 0x42
    cpu.step()

    assert bus.read(0x0200) == 0x42
    assert cpu.pc == 0x8003


def test_opcode_8D_sta_absolute_does_not_change_flags():
    """
    Objective:
    STA Absolute stores A but does not update flags.
    """
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x8D)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)

    cpu.reset()
    cpu.a = 0x00
    cpu.p = NEGATIVE_FLAG
    cpu.step()

    assert bus.read(0x0200) == 0x00
    assert (cpu.p & ZERO_FLAG) == 0
    assert (cpu.p & NEGATIVE_FLAG) != 0
