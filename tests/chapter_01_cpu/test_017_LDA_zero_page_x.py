"""
Test 017 — Add zero-page,X LDA ($B5).

Files to update:
    emulator/cpu/addressing_modes.py
    emulator/cpu/opcodes.py

Locations:
    addressing_modes.zero_page_x
    opcodes.lda_zero_page_x
    opcodes.OPCODE_TABLE[$B5]

Why this step exists:
Zero-page,X adds register X to an 8-bit base address. The addition wraps within page
$00 rather than carrying into page $01.

Complete example implementation:

    # emulator/cpu/addressing_modes.py
    def zero_page_x(cpu) -> int:
        base = cpu.fetch_byte()
        return (base + cpu.x) & 0xFF


    # emulator/cpu/opcodes.py
    from emulator.cpu.addressing_modes import zero_page_x


    def lda_zero_page_x(cpu) -> None:
        address = zero_page_x(cpu)
        lda(cpu, cpu.bus.read(address))


    OPCODE_TABLE = {
        # Preserve existing entries.
        0xB5: lda_zero_page_x,
    }

Important invariant:
    final_address = (operand + X) & 0xFF

Common misconception:
$FF + X=$01 produces $0000, not $0100. This wrapping rule is specific to zero-page
indexed addressing.

Out of scope:
    - absolute,X page crossing
    - zero-page,Y
    - cycle timing
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


def test_zero_page_x_addressing_mode_exists():
    """
    Objective:
    Create in addressing_modes.py:
        def zero_page_x(cpu):
            ...

    What it does:
    - Read the next byte from the CPU bus.
    - Add register X to that byte.
    - Keep the result inside page $00: address = (base + cpu.x) & 0xFF 
    - Return the final address.

    Example:
    If the next byte is 0x10 and X is 0x03,
    zero_page_x(cpu) must return address 0x0013.
    """
    assert hasattr(addressing_modes, "zero_page_x")
    assert callable(addressing_modes.zero_page_x)
    assert list(inspect.signature(addressing_modes.zero_page_x).parameters) == ["cpu"]


def test_zero_page_x_addressing_mode_adds_x_to_base_address():
    """
    Objective:
    zero_page_x(cpu) must add cpu.x to the base address.

    Example:
    PC points to 0x10.
    X is 0x03.
    The function returns address 0x0013.

    Formula:
        address = base + X
    """
    cpu, _, rom = make_cpu_with_rom()

    cpu.reset()
    cpu.x = 0x03
    rom.write(0x0000, 0x10)

    addr = addressing_modes.zero_page_x(cpu)

    assert addr == 0x0013
    assert cpu.pc == 0x8001


def test_zero_page_x_addressing_mode_wraps_inside_page_zero():
    """
    Objective:
    Zero Page,X must wrap inside page $00.

    This is the special rule:
    if the address goes past 0xFF, it returns to 0x00.

    Example:
    Base is 0xFF.
    X is 0x01.
    0xFF + 0x01 becomes 0x00, not 0x0100.

    Formula:
        address = (base + X) & 0xFF
    """
    cpu, _, rom = make_cpu_with_rom()

    cpu.reset()
    cpu.x = 0x01
    rom.write(0x0000, 0xFF)

    addr = addressing_modes.zero_page_x(cpu)

    assert addr == 0x0000
    assert cpu.pc == 0x8001


def test_lda_zero_page_x_opcode_handler_exists_and_is_in_opcode_table():
    """
    Objective:
    Create in opcodes.py:
        def lda_zero_page_x(cpu):
            addr = zero_page_x(cpu)
            value = cpu.bus.read(addr)
            lda(cpu, value)

    Then add opcode 0xB5 to OPCODE_TABLE:
        OPCODE_TABLE = {
            ...
            0xB5: lda_zero_page_x,
            ...
        }

    Why:
    0xB5 means LDA Zero Page,X.
    """
    assert hasattr(opcodes, "lda_zero_page_x")
    assert callable(opcodes.lda_zero_page_x)
    assert list(inspect.signature(opcodes.lda_zero_page_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xB5] is opcodes.lda_zero_page_x


def test_opcode_B5_lda_zero_page_x_loads_value_into_register_a():
    """
    Objective:
    Implement opcode 0xB5 as LDA Zero Page,X.

    What the opcode handler should do:
    - Use zero_page_x(cpu) to get the address.
    - Read the value from that address.
    - Use lda(cpu, value) to load register A.

    Example:
    B5 10 means LDA $10,X.
    If X is 0x03, the final address is $0013.
    If RAM $0013 contains 0x42, register A becomes 0x42.
    """
    cpu, bus, rom = make_cpu_with_rom()

    rom.write(0x0000, 0xB5)
    rom.write(0x0001, 0x10)
    bus.write(0x0013, 0x42)

    cpu.reset()
    cpu.x = 0x03
    cpu.step()

    assert cpu.a == 0x42
    assert cpu.pc == 0x8002


def test_opcode_B5_lda_zero_page_x_uses_wrapped_address():
    """
    Objective:
    LDA Zero Page,X must use the wrapped zero page address.

    Example:
    B5 FF means LDA $FF,X.
    If X is 0x01, the final address is $0000.
    If RAM $0000 contains 0x37, register A becomes 0x37.
    """
    cpu, bus, rom = make_cpu_with_rom()

    rom.write(0x0000, 0xB5)
    rom.write(0x0001, 0xFF)
    bus.write(0x0000, 0x37)

    cpu.reset()
    cpu.x = 0x01
    cpu.step()

    assert cpu.a == 0x37
    assert cpu.pc == 0x8002


def test_opcode_B5_lda_zero_page_x_updates_zero_flag():
    """
    Objective:
    LDA Zero Page,X must update the Zero flag.

    If the loaded value is 0x00, Zero flag is set.
    """
    cpu, bus, rom = make_cpu_with_rom()

    rom.write(0x0000, 0xB5)
    rom.write(0x0001, 0x10)
    bus.write(0x0013, 0x00)

    cpu.reset()
    cpu.x = 0x03
    cpu.step()

    assert cpu.a == 0x00
    assert (cpu.p & ZERO_FLAG) != 0


def test_opcode_B5_lda_zero_page_x_updates_negative_flag():
    """
    Objective:
    LDA Zero Page,X must update the Negative flag.

    If the loaded value has bit 7 active, Negative flag is set.
    """
    cpu, bus, rom = make_cpu_with_rom()

    rom.write(0x0000, 0xB5)
    rom.write(0x0001, 0x10)
    bus.write(0x0013, 0x80)

    cpu.reset()
    cpu.x = 0x03
    cpu.step()

    assert cpu.a == 0x80
    assert (cpu.p & NEGATIVE_FLAG) != 0
