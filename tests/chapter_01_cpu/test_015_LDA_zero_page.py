"""
Test 015 — Add zero-page LDA ($A5).

Files to update:
    emulator/cpu/addressing_modes.py
    emulator/cpu/cpu.py

Locations:
    addressing_modes.absolute, changed from returning a value to an address
    addressing_modes.zero_page
    CPU.step, updated $AD branch and new $A5 branch

Why this step exists:
Zero-page addressing encodes an address using one operand byte. This lesson also
establishes the reusable rule that memory addressing modes return addresses; opcode
code performs the final bus read before calling the instruction.

Complete example implementation:

    # emulator/cpu/addressing_modes.py
    def absolute(cpu) -> int:
        return cpu.fetch_word()


    def zero_page(cpu) -> int:
        return cpu.fetch_byte()


    # emulator/cpu/cpu.py
    from emulator.cpu.addressing_modes import zero_page
    from emulator.cpu.instructions import lda


    class CPU:
        def step(self) -> None:
            opcode = self.fetch_byte()

            if opcode == 0xA5:
                address = zero_page(self)
                value = self.bus.read(address)
                lda(self, value)
                return

            if opcode == 0xAD:
                address = absolute(self)
                value = self.bus.read(address)
                lda(self, value)
                return

Important invariants:
    - zero_page consumes exactly one operand byte
    - zero_page and absolute now return addresses
    - CPU.step performs the final bus read
    - lda remains responsible for A and Z/N

Common misconception:
The operand $10 means address $0010, not a value of $10 and not an address relative to
the current program counter.

Out of scope:
    - opcode-table dispatch, introduced in Test 016
    - indexed zero-page wrapping
    - cycle timing
"""
import inspect

from emulator.cpu import addressing_modes
from emulator.bus.cpu_bus import CpuBus
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


def test_zero_page_addressing_mode_exists():
    """
    Objective:
    Create in addressing_modes.py:
        def zero_page(cpu):
            ...

    What it does:
    - Read the next byte from the CPU bus.
    - Return that byte as an address in page $00.

    Example:
    A5 10 means LDA $10.
    zero_page(cpu) must return address 0x0010.
    """
    assert hasattr(addressing_modes, "zero_page")
    assert callable(addressing_modes.zero_page)
    assert list(inspect.signature(addressing_modes.zero_page).parameters) == ["cpu"]


def test_zero_page_addressing_mode_returns_address_from_page_zero():
    """
    Objective:
    zero_page(cpu) must fetch one byte and return it as an address.

    Example:
    PC points to 0x10.
    The function returns address 0x0010.
    """
    cpu, _, rom = make_cpu_with_rom()

    cpu.reset()
    rom.write(0x0000, 0x10)

    addr = addressing_modes.zero_page(cpu)

    assert addr == 0x0010
    assert cpu.pc == 0x8001


def test_opcode_A5_lda_zero_page_loads_value_into_register_a():
    """
    Objective:
    Implement opcode 0xA5 as LDA Zero Page.

    What CPU.step() should do:
    - Read opcode 0xA5.
    - Use zero_page(cpu) to get the address.
    - Read the value from that address.
    - Use lda(cpu, value) to load register A.

    Example:
    A5 10 means LDA $10.
    If RAM $0010 contains 0x42, register A becomes 0x42.
    """
    cpu, bus, rom = make_cpu_with_rom()

    rom.write(0x0000, 0xA5)
    rom.write(0x0001, 0x10)
    bus.write(0x0010, 0x42)

    cpu.reset()
    cpu.step()

    assert cpu.a == 0x42
    assert cpu.pc == 0x8002


def test_opcode_A5_lda_zero_page_updates_zero_flag():
    """
    Objective:
    LDA Zero Page must update the Zero flag.

    If the loaded value is 0x00, Zero flag is set.
    """
    cpu, bus, rom = make_cpu_with_rom()

    rom.write(0x0000, 0xA5)
    rom.write(0x0001, 0x10)
    bus.write(0x0010, 0x00)

    cpu.reset()
    cpu.step()

    assert cpu.a == 0x00
    assert (cpu.p & ZERO_FLAG) != 0


def test_opcode_A5_lda_zero_page_updates_negative_flag():
    """
    Objective:
    LDA Zero Page must update the Negative flag.

    If the loaded value has bit 7 active, Negative flag is set.
    """
    cpu, bus, rom = make_cpu_with_rom()

    rom.write(0x0000, 0xA5)
    rom.write(0x0001, 0x10)
    bus.write(0x0010, 0x80)

    cpu.reset()
    cpu.step()

    assert cpu.a == 0x80
    assert (cpu.p & NEGATIVE_FLAG) != 0
