"""
Test 021 — Add indirect-indexed LDA ($B1, written `(d),Y`).

Files to update:
    emulator/cpu/addressing_modes.py
    emulator/cpu/opcodes.py

Locations:
    addressing_modes.indirect_y
    opcodes import of indirect_y
    opcodes.lda_indirect_y
    opcodes.OPCODE_TABLE[$B1]

Why this step exists:
Test 020 indexed the zero-page pointer with X before dereferencing it. This mode
instead reads an unindexed zero-page pointer and adds Y to the assembled 16-bit base
address, completing LDA's two indirect indexed forms.

Complete example implementation:

    # emulator/cpu/addressing_modes.py
    def indirect_y(cpu) -> int:
        pointer = cpu.fetch_byte()
        low = cpu.bus.read(pointer)
        high = cpu.bus.read((pointer + 1) & 0xFF)
        return (low | (high << 8)) + cpu.y


    # emulator/cpu/opcodes.py
    from emulator.cpu.addressing_modes import indirect_y


    def lda_indirect_y(cpu) -> None:
        address = indirect_y(cpu)
        value = cpu.bus.read(address)
        lda(cpu, value)


    OPCODE_TABLE = {
        # Preserve existing entries.
        0xB1: lda_indirect_y,
    }

Important invariants:
    - exactly one operand byte is fetched
    - the pointer high-byte read wraps from zero-page $FF to $00
    - Y is added after the little-endian pointer is assembled
    - the handler reads the final address and delegates A and Z/N updates to lda

Common misconception:
`(d),Y` does not add Y to the operand before reading the pointer; that would confuse
it with Test 020's `(d,X)` ordering.

Out of scope:
    - STA and its opcode handlers
    - page-cross cycle penalties
    - a shared abstraction for the two indirect indexed modes
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


def test_indirect_y_addressing_mode_exists():
    """
    Objective:
    Create in addressing_modes.py:
        def indirect_y(cpu):
            ...

    What it does:
    - Read the next byte from the CPU bus.
    - Use that byte as a zero page pointer.
    - Read two bytes from zero page.
    - Build the base 16-bit address.
    - Add register Y to that base address.
    - Return the final address.

    Implementation example:
        def indirect_y(cpu):
            ptr = cpu.fetch_byte()
            low = cpu.bus.read(ptr)
            high = cpu.bus.read((ptr + 1) & 0xFF)

            return (low | (high << 8)) + cpu.y

    Example:
    B1 20 means LDA ($20),Y.
    RAM[$0020] and RAM[$0021] contain the base address.
    Then Y is added to that base address.

    Common mistake:
    Do not add Y before reading the pointer.
    For (d),Y, read the pointer first, then add Y.
    """
    assert hasattr(addressing_modes, "indirect_y")
    assert callable(addressing_modes.indirect_y)
    assert list(inspect.signature(addressing_modes.indirect_y).parameters) == ["cpu"]


def test_indirect_y_addressing_mode_reads_pointer_then_adds_y():
    """
    Objective:
    indirect_y(cpu) must read a zero page pointer first, then add cpu.y.

    Example:
    PC points to 0x20.
    Y is 0x04.

    RAM[$0020] = 0x00  # low byte
    RAM[$0021] = 0x12  # high byte

    Base address is 0x1200.
    Final address is 0x1204.
    """
    cpu, bus, rom = make_cpu_with_rom()

    cpu.reset()
    cpu.y = 0x04
    rom.write(0x0000, 0x20)
    bus.write(0x0020, 0x00)
    bus.write(0x0021, 0x12)

    addr = addressing_modes.indirect_y(cpu)

    assert addr == 0x1204
    assert cpu.pc == 0x8001


def test_indirect_y_addressing_mode_uses_y_not_x():
    """
    Objective:
    indirect_y(cpu) must use register Y, not register X.

    This test catches a common copy-paste mistake from indirect_x(cpu).

    Example:
    Base address is 0x1200.
    X is 0x01.
    Y is 0x04.
    Final address must be 0x1204.
    """
    cpu, bus, rom = make_cpu_with_rom()

    cpu.reset()
    cpu.x = 0x01
    cpu.y = 0x04
    rom.write(0x0000, 0x20)
    bus.write(0x0020, 0x00)
    bus.write(0x0021, 0x12)

    addr = addressing_modes.indirect_y(cpu)

    assert addr == 0x1204
    assert cpu.pc == 0x8001


def test_indirect_y_addressing_mode_wraps_high_byte_read_inside_zero_page():
    """
    Objective:
    If the pointer is 0xFF, the high byte must be read from 0x00.

    This is a zero page rule.

    Example:
    Pointer is 0xFF.
    Y is 0x04.

    RAM[$00FF] = 0x00  # low byte
    RAM[$0000] = 0x80  # high byte

    Base address is 0x8000.
    Final address is 0x8004.
    """
    cpu, bus, rom = make_cpu_with_rom()

    cpu.reset()
    cpu.y = 0x04
    rom.write(0x0000, 0xFF)
    bus.write(0x00FF, 0x00)
    bus.write(0x0000, 0x80)

    addr = addressing_modes.indirect_y(cpu)

    assert addr == 0x8004
    assert cpu.pc == 0x8001


def test_indirect_y_addressing_mode_can_cross_page_boundary():
    """
    Objective:
    Indirect,Y can cross a page boundary after adding Y.

    Example:
    Base address is 0x12FF.
    Y is 0x01.
    Final address is 0x1300.

    Note:
    Later, page crossing can affect CPU cycles.
    For now, this test only checks the final address behavior.
    """
    cpu, bus, rom = make_cpu_with_rom()

    cpu.reset()
    cpu.y = 0x01
    rom.write(0x0000, 0x20)
    bus.write(0x0020, 0xFF)
    bus.write(0x0021, 0x12)

    addr = addressing_modes.indirect_y(cpu)

    assert addr == 0x1300
    assert cpu.pc == 0x8001


def test_lda_indirect_y_opcode_handler_exists_and_is_in_opcode_table():
    """
    Objective:
    Create in opcodes.py:
        def lda_indirect_y(cpu):
            addr = indirect_y(cpu)
            value = cpu.bus.read(addr)
            lda(cpu, value)

    Then add opcode 0xB1 to OPCODE_TABLE:
        OPCODE_TABLE = {
            ...
            0xB1: lda_indirect_y,
            ...
        }

    Why:
    0xB1 means LDA (Indirect),Y, written as LDA ($nn),Y.
    """
    assert hasattr(opcodes, "lda_indirect_y")
    assert callable(opcodes.lda_indirect_y)
    assert list(inspect.signature(opcodes.lda_indirect_y).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xB1] is opcodes.lda_indirect_y


def test_opcode_B1_lda_indirect_y_loads_value_into_register_a():
    """
    Objective:
    Implement opcode 0xB1 as LDA (Indirect),Y.

    What the opcode handler should do:
    - Use indirect_y(cpu) to get the final address.
    - Read the value from that final address.
    - Use lda(cpu, value) to load register A.

    Example:
    B1 20 means LDA ($20),Y.
    If RAM[$0020-$0021] points to $1200,
    and Y is 0x04, the final address is $1204.
    If RAM[$1204] contains 0x42, register A becomes 0x42.
    """
    cpu, bus, rom = make_cpu_with_rom()

    rom.write(0x0000, 0xB1)
    rom.write(0x0001, 0x20)
    bus.write(0x0020, 0x00)
    bus.write(0x0021, 0x12)
    bus.write(0x1204, 0x42)

    cpu.reset()
    cpu.y = 0x04
    cpu.step()

    assert cpu.a == 0x42
    assert cpu.pc == 0x8002


def test_opcode_B1_lda_indirect_y_wraps_high_byte_read():
    """
    Objective:
    LDA (Indirect),Y must wrap the high byte read inside zero page.

    Example:
    B1 FF means LDA ($FF),Y.
    RAM[$00FF] = 0x00.
    RAM[$0000] = 0x80.
    Base address is $8000.
    If Y is 0x04, final address is $8004.
    If RAM[$8004] contains 0x37, register A becomes 0x37.
    """
    cpu, bus, rom = make_cpu_with_rom()

    rom.write(0x0000, 0xB1)
    rom.write(0x0001, 0xFF)
    bus.write(0x00FF, 0x00)
    bus.write(0x0000, 0x80)
    rom.write(0x0004, 0x37)

    cpu.reset()
    cpu.y = 0x04
    cpu.step()

    assert cpu.a == 0x37
    assert cpu.pc == 0x8002


def test_opcode_B1_lda_indirect_y_updates_zero_flag():
    """
    Objective:
    LDA (Indirect),Y must update the Zero flag.

    If the loaded value is 0x00, Zero flag is set.
    """
    cpu, bus, rom = make_cpu_with_rom()

    rom.write(0x0000, 0xB1)
    rom.write(0x0001, 0x20)
    bus.write(0x0020, 0x00)
    bus.write(0x0021, 0x12)
    bus.write(0x1204, 0x00)

    cpu.reset()
    cpu.y = 0x04
    cpu.step()

    assert cpu.a == 0x00
    assert (cpu.p & ZERO_FLAG) != 0


def test_opcode_B1_lda_indirect_y_updates_negative_flag():
    """
    Objective:
    LDA (Indirect),Y must update the Negative flag.

    If the loaded value has bit 7 active, Negative flag is set.
    """
    cpu, bus, rom = make_cpu_with_rom()

    rom.write(0x0000, 0xB1)
    rom.write(0x0001, 0x20)
    bus.write(0x0020, 0x00)
    bus.write(0x0021, 0x12)
    bus.write(0x1204, 0x80)

    cpu.reset()
    cpu.y = 0x04
    cpu.step()

    assert cpu.a == 0x80
    assert (cpu.p & NEGATIVE_FLAG) != 0
