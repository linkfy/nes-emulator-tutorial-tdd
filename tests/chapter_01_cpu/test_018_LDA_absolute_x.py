"""
Test 018 — Add absolute,X LDA ($BD).

Files to update:
    emulator/cpu/addressing_modes.py
    emulator/cpu/opcodes.py

Locations:
    addressing_modes.absolute_x
    opcodes.lda_absolute_x
    opcodes.OPCODE_TABLE[$BD]

Why this step exists:
Absolute,X adds X to a complete 16-bit base address. Unlike zero-page,X, the result
can cross from one 256-byte page into the next.

Complete example implementation:

    # emulator/cpu/addressing_modes.py
    def absolute_x(cpu) -> int:
        base = cpu.fetch_word()
        return base + cpu.x


    # emulator/cpu/opcodes.py
    from emulator.cpu.addressing_modes import absolute_x


    def lda_absolute_x(cpu) -> None:
        address = absolute_x(cpu)
        lda(cpu, cpu.bus.read(address))


    OPCODE_TABLE = {
        # Preserve existing entries.
        0xBD: lda_absolute_x,
    }

Important invariant:
$12FF + X=$01 becomes $1300; it does not wrap inside zero page.

Common misconception:
Crossing a page does not change the effective address calculation. Additional cycle
behavior is intentionally outside this lesson.

Out of scope:
    - page-cross cycle penalties
    - absolute,Y
    - indirect addressing
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


def test_absolute_x_addressing_mode_exists():
    """
    Objective:
    Create in addressing_modes.py:
        def absolute_x(cpu):
            ...

    What it does:
    - Read the next two bytes from the CPU bus.
    - The first byte is low.
    - The second byte is high.
    - Build the base 16-bit address.
    - Add register X to that base address.
    - Return the final address.

    Example:
    If the next bytes are 00 12 and X is 0x04,
    the base address is 0x1200.
    absolute_x(cpu) must return address 0x1204.
    """
    assert hasattr(addressing_modes, "absolute_x")
    assert callable(addressing_modes.absolute_x)
    assert list(inspect.signature(addressing_modes.absolute_x).parameters) == ["cpu"]


def test_absolute_x_addressing_mode_adds_x_to_base_address():
    """
    Objective:
    absolute_x(cpu) must read a 16-bit address and add cpu.x.

    Example:
    PC points to bytes 00 12.
    X is 0x04.
    Base address is 0x1200.
    Final address is 0x1204.

    Formula:
        address = base + X
    """
    cpu, _, rom = make_cpu_with_rom()

    cpu.reset()
    cpu.x = 0x04
    rom.write(0x0000, 0x00)
    rom.write(0x0001, 0x12)

    addr = addressing_modes.absolute_x(cpu)

    assert addr == 0x1204
    assert cpu.pc == 0x8002


def test_absolute_x_addressing_mode_does_not_wrap_inside_zero_page():
    """
    Objective:
    Absolute,X is different from Zero Page,X.

    Zero Page,X wraps inside 0x00-0xFF.
    Absolute,X uses a 16-bit address.

    Example:
    Base address is 0x12FF.
    X is 0x01.
    Final address is 0x1300, not 0x0000.
    """
    cpu, _, rom = make_cpu_with_rom()

    cpu.reset()
    cpu.x = 0x01
    rom.write(0x0000, 0xFF)
    rom.write(0x0001, 0x12)

    addr = addressing_modes.absolute_x(cpu)

    assert addr == 0x1300
    assert cpu.pc == 0x8002


def test_lda_absolute_x_opcode_handler_exists_and_is_in_opcode_table():
    """
    Objective:
    Create in opcodes.py:
        def lda_absolute_x(cpu):
            addr = absolute_x(cpu)
            value = cpu.bus.read(addr)
            lda(cpu, value)

    Then add opcode 0xBD to OPCODE_TABLE:
        OPCODE_TABLE = {
            ...
            0xBD: lda_absolute_x,
            ...
        }

    Why:
    0xBD means LDA Absolute,X.
    """
    assert hasattr(opcodes, "lda_absolute_x")
    assert callable(opcodes.lda_absolute_x)
    assert list(inspect.signature(opcodes.lda_absolute_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xBD] is opcodes.lda_absolute_x


def test_opcode_BD_lda_absolute_x_loads_value_into_register_a():
    """
    Objective:
    Implement opcode 0xBD as LDA Absolute,X.

    What the opcode handler should do:
    - Use absolute_x(cpu) to get the final address.
    - Read the value from that address.
    - Use lda(cpu, value) to load register A.

    Example:
    BD 00 12 means LDA $1200,X.
    If X is 0x04, the final address is $1204.
    If RAM $1204 contains 0x42, register A becomes 0x42.
    """
    cpu, bus, rom = make_cpu_with_rom()

    rom.write(0x0000, 0xBD)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x12)
    bus.write(0x1204, 0x42)

    cpu.reset()
    cpu.x = 0x04
    cpu.step()

    assert cpu.a == 0x42
    assert cpu.pc == 0x8003


def test_opcode_BD_lda_absolute_x_can_cross_page_boundary():
    """
    Objective:
    LDA Absolute,X must use the full 16-bit final address.

    Example:
    BD FF 12 means LDA $12FF,X.
    If X is 0x01, the final address is $1300.
    If RAM $1300 contains 0x37, register A becomes 0x37.

    Note:
    Later, page crossing can affect CPU cycles.
    For now, this test only checks the final address behavior.
    """
    cpu, bus, rom = make_cpu_with_rom()

    rom.write(0x0000, 0xBD)
    rom.write(0x0001, 0xFF)
    rom.write(0x0002, 0x12)
    bus.write(0x1300, 0x37)

    cpu.reset()
    cpu.x = 0x01
    cpu.step()

    assert cpu.a == 0x37
    assert cpu.pc == 0x8003


def test_opcode_BD_lda_absolute_x_updates_zero_flag():
    """
    Objective:
    LDA Absolute,X must update the Zero flag.

    If the loaded value is 0x00, Zero flag is set.
    """
    cpu, bus, rom = make_cpu_with_rom()

    rom.write(0x0000, 0xBD)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x12)
    bus.write(0x1204, 0x00)

    cpu.reset()
    cpu.x = 0x04
    cpu.step()

    assert cpu.a == 0x00
    assert (cpu.p & ZERO_FLAG) != 0


def test_opcode_BD_lda_absolute_x_updates_negative_flag():
    """
    Objective:
    LDA Absolute,X must update the Negative flag.

    If the loaded value has bit 7 active, Negative flag is set.
    """
    cpu, bus, rom = make_cpu_with_rom()

    rom.write(0x0000, 0xBD)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x12)
    bus.write(0x1204, 0x80)

    cpu.reset()
    cpu.x = 0x04
    cpu.step()

    assert cpu.a == 0x80
    assert (cpu.p & NEGATIVE_FLAG) != 0
