"""
Test 019 — Add absolute,Y LDA ($B9).

Files to update:
    emulator/cpu/addressing_modes.py
    emulator/cpu/opcodes.py

Locations:
    addressing_modes.absolute_y
    opcodes.lda_absolute_y
    opcodes.OPCODE_TABLE[$B9]

Why this step exists:
Absolute,Y has the same 16-bit addressing behavior as absolute,X but uses register Y.
Keeping separate helpers makes the selected index register explicit and testable.

Complete example implementation:

    # emulator/cpu/addressing_modes.py
    def absolute_y(cpu) -> int:
        base = cpu.fetch_word()
        return base + cpu.y


    # emulator/cpu/opcodes.py
    from emulator.cpu.addressing_modes import absolute_y


    def lda_absolute_y(cpu) -> None:
        address = absolute_y(cpu)
        lda(cpu, cpu.bus.read(address))


    OPCODE_TABLE = {
        # Preserve existing entries.
        0xB9: lda_absolute_y,
    }

Important invariants:
    - the helper uses Y, not X
    - two operand bytes are consumed before adding Y
    - page crossing preserves the full 16-bit result

Common misconception:
Copying absolute_x and forgetting to change `cpu.x` to `cpu.y` can pass tests where
both registers happen to contain the same value.

Out of scope:
    - page-cross cycle penalties
    - indirect indexed modes
    - generic indexed-address helpers
"""
import inspect

from emulator.bus.cpu_bus import CpuBus
from emulator.cpu import addressing_modes, opcodes
from emulator.cpu.cpu import CPU
from emulator.memory.fake_rom import FakeROM
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG


def make_cpu_with_rom():
    rom = FakeROM()

    # Reset Vector: start program at CPU address $8000.
    # In FakeROM this is offset $0000.
    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)

    bus = CpuBus(program_rom=rom)
    cpu = CPU(bus)

    return cpu, bus, rom


def test_absolute_y_addressing_mode_exists():
    """
    Objective:
    Create in addressing_modes.py:
        def absolute_y(cpu):
            ...

    What it does:
    - Read the next two bytes from the CPU bus.
    - The first byte is low.
    - The second byte is high.
    - Build the base 16-bit address.
    - Add register Y to that base address.
    - Return the final address.

    Example:
    If the next bytes are 00 12 and Y is 0x04,
    the base address is 0x1200.
    absolute_y(cpu) must return address 0x1204.
    """
    assert hasattr(addressing_modes, "absolute_y")
    assert callable(addressing_modes.absolute_y)
    assert list(inspect.signature(addressing_modes.absolute_y).parameters) == ["cpu"]


def test_absolute_y_addressing_mode_adds_y_to_base_address():
    """
    Objective:
    absolute_y(cpu) must read a 16-bit address and add cpu.y.

    Example:
    PC points to bytes 00 12.
    Y is 0x04.
    Base address is 0x1200.
    Final address is 0x1204.

    Formula:
        address = base + Y
    """
    cpu, _, rom = make_cpu_with_rom()

    cpu.reset()
    cpu.y = 0x04
    rom.write(0x0000, 0x00)
    rom.write(0x0001, 0x12)

    addr = addressing_modes.absolute_y(cpu)

    assert addr == 0x1204
    assert cpu.pc == 0x8002


def test_absolute_y_addressing_mode_uses_y_not_x():
    """
    Objective:
    absolute_y(cpu) must use register Y, not register X.

    This test catches a common copy-paste mistake from absolute_x(cpu).

    Example:
    Base address is 0x1200.
    X is 0x01.
    Y is 0x04.
    Final address must be 0x1204.
    """
    cpu, _, rom = make_cpu_with_rom()

    cpu.reset()
    cpu.x = 0x01
    cpu.y = 0x04
    rom.write(0x0000, 0x00)
    rom.write(0x0001, 0x12)

    addr = addressing_modes.absolute_y(cpu)

    assert addr == 0x1204
    assert cpu.pc == 0x8002


def test_absolute_y_addressing_mode_can_cross_page_boundary():
    """
    Objective:
    Absolute,Y uses a 16-bit address and can cross a page boundary.

    Example:
    Base address is 0x12FF.
    Y is 0x01.
    Final address is 0x1300.

    Note:
    Later, page crossing can affect CPU cycles.
    For now, this test only checks the final address behavior.
    """
    cpu, _, rom = make_cpu_with_rom()

    cpu.reset()
    cpu.y = 0x01
    rom.write(0x0000, 0xFF)
    rom.write(0x0001, 0x12)

    addr = addressing_modes.absolute_y(cpu)

    assert addr == 0x1300
    assert cpu.pc == 0x8002


def test_lda_absolute_y_opcode_handler_exists_and_is_in_opcode_table():
    """
    Objective:
    Create in opcodes.py:
        def lda_absolute_y(cpu):
            addr = absolute_y(cpu)
            value = cpu.bus.read(addr)
            lda(cpu, value)

    Then add opcode 0xB9 to OPCODE_TABLE:
        OPCODE_TABLE = {
            ...
            0xB9: lda_absolute_y,
            ...
        }

    Why:
    0xB9 means LDA Absolute,Y.
    """
    assert hasattr(opcodes, "lda_absolute_y")
    assert callable(opcodes.lda_absolute_y)
    assert list(inspect.signature(opcodes.lda_absolute_y).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xB9] is opcodes.lda_absolute_y


def test_opcode_B9_lda_absolute_y_loads_value_into_register_a():
    """
    Objective:
    Implement opcode 0xB9 as LDA Absolute,Y.

    What the opcode handler should do:
    - Use absolute_y(cpu) to get the final address.
    - Read the value from that address.
    - Use lda(cpu, value) to load register A.

    Example:
    B9 00 12 means LDA $1200,Y.
    If Y is 0x04, the final address is $1204.
    If RAM $1204 contains 0x42, register A becomes 0x42.
    """
    cpu, bus, rom = make_cpu_with_rom()

    rom.write(0x0000, 0xB9)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x12)
    bus.write(0x1204, 0x42)

    cpu.reset()
    cpu.y = 0x04
    cpu.step()

    assert cpu.a == 0x42
    assert cpu.pc == 0x8003


def test_opcode_B9_lda_absolute_y_can_cross_page_boundary():
    """
    Objective:
    LDA Absolute,Y must use the full 16-bit final address.

    Example:
    B9 FF 12 means LDA $12FF,Y.
    If Y is 0x01, the final address is $1300.
    If RAM $1300 contains 0x37, register A becomes 0x37.
    """
    cpu, bus, rom = make_cpu_with_rom()

    rom.write(0x0000, 0xB9)
    rom.write(0x0001, 0xFF)
    rom.write(0x0002, 0x12)
    bus.write(0x1300, 0x37)

    cpu.reset()
    cpu.y = 0x01
    cpu.step()

    assert cpu.a == 0x37
    assert cpu.pc == 0x8003


def test_opcode_B9_lda_absolute_y_updates_zero_flag():
    """
    Objective:
    LDA Absolute,Y must update the Zero flag.

    If the loaded value is 0x00, Zero flag is set.
    """
    cpu, bus, rom = make_cpu_with_rom()

    rom.write(0x0000, 0xB9)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x12)
    bus.write(0x1204, 0x00)

    cpu.reset()
    cpu.y = 0x04
    cpu.step()

    assert cpu.a == 0x00
    assert (cpu.p & ZERO_FLAG) != 0


def test_opcode_B9_lda_absolute_y_updates_negative_flag():
    """
    Objective:
    LDA Absolute,Y must update the Negative flag.

    If the loaded value has bit 7 active, Negative flag is set.
    """
    cpu, bus, rom = make_cpu_with_rom()

    rom.write(0x0000, 0xB9)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x12)
    bus.write(0x1204, 0x80)

    cpu.reset()
    cpu.y = 0x04
    cpu.step()

    assert cpu.a == 0x80
    assert (cpu.p & NEGATIVE_FLAG) != 0
