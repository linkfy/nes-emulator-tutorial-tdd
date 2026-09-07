"""
Test 020 — Add indexed-indirect LDA ($A1, written `(d,X)`).

Files to update:
    emulator/cpu/addressing_modes.py
    emulator/cpu/opcodes.py

Locations:
    addressing_modes.indirect_x
    opcodes.lda_indirect_x
    opcodes.OPCODE_TABLE[$A1]

Why this step exists:
Indexed-indirect addressing uses the operand plus X to select a two-byte pointer in
zero page. The pointer then supplies the final 16-bit address of the LDA value.

Complete example implementation:

    # emulator/cpu/addressing_modes.py
    def indirect_x(cpu) -> int:
        operand = cpu.fetch_byte()
        pointer = (operand + cpu.x) & 0xFF

        low = cpu.bus.read(pointer)
        high = cpu.bus.read((pointer + 1) & 0xFF)

        return low | (high << 8)


    # emulator/cpu/opcodes.py
    from emulator.cpu.addressing_modes import indirect_x


    def lda_indirect_x(cpu) -> None:
        address = indirect_x(cpu)
        lda(cpu, cpu.bus.read(address))


    OPCODE_TABLE = {
        # Preserve existing entries.
        0xA1: lda_indirect_x,
    }

Address timeline for `A1 20` with X=$04:
    fetch operand $20
        -> pointer location $24
        -> read low byte from $0024
        -> read high byte from $0025
        -> assemble final address
        -> read value for LDA

Important invariants:
    - X is added before reading the pointer
    - pointer selection wraps within zero page
    - the high-byte read from pointer $FF wraps to $00

Common misconception:
Do not add X to the final 16-bit address. That is a different addressing mechanism;
`(d,X)` indexes the zero-page pointer location.

Out of scope:
    - indirect,Y, introduced in Test 021
    - page-cross cycle penalties
    - JMP's distinct indirect behavior
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


def test_indirect_x_addressing_mode_exists():
    """
    Objective:
    Create in addressing_modes.py:
        def indirect_x(cpu):
            ...

    What it does:
    - Read the next byte from the CPU bus.
    - Add register X to that byte.
    - Keep the pointer inside page $00.
    - Read two bytes from zero page.
    - Build and return the final 16-bit address.

    Implementation example:
        def indirect_x(cpu):
            base = cpu.fetch_byte()
            ptr = (base + cpu.x) & 0xFF

            low = cpu.bus.read(ptr)
            high = cpu.bus.read((ptr + 1) & 0xFF)

            return low | (high << 8)

    Example:
    A1 20 means LDA ($20,X).
    If X is 0x04, the pointer is at $0024.
    RAM[$0024] and RAM[$0025] contain the final address.

    Common mistake:
    Do not use fetch_word() here.
    This addressing mode reads only one operand byte.

    Another common mistake:
    Do not add X to the final 16-bit address.
    X is added before reading the pointer from zero page.
    """
    assert hasattr(addressing_modes, "indirect_x")
    assert callable(addressing_modes.indirect_x)
    assert list(inspect.signature(addressing_modes.indirect_x).parameters) == ["cpu"]


def test_indirect_x_addressing_mode_reads_final_address_from_zero_page_pointer():
    """
    Objective:
    indirect_x(cpu) must use X to select a zero page pointer.

    Example:
    PC points to 0x20.
    X is 0x04.
    Pointer address is 0x24.

    RAM[$0024] = 0x00  # low byte
    RAM[$0025] = 0x12  # high byte

    The function returns address 0x1200.
    """
    cpu, bus, rom = make_cpu_with_rom()

    cpu.reset()
    cpu.x = 0x04
    rom.write(0x0000, 0x20)
    bus.write(0x0024, 0x00)
    bus.write(0x0025, 0x12)

    addr = addressing_modes.indirect_x(cpu)

    assert addr == 0x1200
    assert cpu.pc == 0x8001


def test_indirect_x_addressing_mode_wraps_pointer_inside_zero_page():
    """
    Objective:
    The pointer location must wrap inside page $00.

    Example:
    Base is 0xFF.
    X is 0x02.
    Pointer address is (0xFF + 0x02) & 0xFF = 0x01.

    RAM[$0001] = 0x34  # low byte
    RAM[$0002] = 0x12  # high byte

    The function returns address 0x1234.
    """
    cpu, bus, rom = make_cpu_with_rom()

    cpu.reset()
    cpu.x = 0x02
    rom.write(0x0000, 0xFF)
    bus.write(0x0001, 0x34)
    bus.write(0x0002, 0x12)

    addr = addressing_modes.indirect_x(cpu)

    assert addr == 0x1234
    assert cpu.pc == 0x8001


def test_indirect_x_addressing_mode_wraps_high_byte_read_inside_zero_page():
    """
    Objective:
    If the pointer address is 0xFF, the high byte must be read from 0x00.

    This is a zero page rule.

    Example:
    Base is 0xFE.
    X is 0x01.
    Pointer address is 0xFF.

    RAM[$00FF] = 0x00  # low byte
    RAM[$0000] = 0x80  # high byte

    The function returns address 0x8000.
    """
    cpu, bus, rom = make_cpu_with_rom()

    cpu.reset()
    cpu.x = 0x01
    rom.write(0x0000, 0xFE)
    bus.write(0x00FF, 0x00)
    bus.write(0x0000, 0x80)

    addr = addressing_modes.indirect_x(cpu)

    assert addr == 0x8000
    assert cpu.pc == 0x8001


def test_lda_indirect_x_opcode_handler_exists_and_is_in_opcode_table():
    """
    Objective:
    Create in opcodes.py:
        def lda_indirect_x(cpu):
            addr = indirect_x(cpu)
            value = cpu.bus.read(addr)
            lda(cpu, value)

    Then add opcode 0xA1 to OPCODE_TABLE:
        OPCODE_TABLE = {
            ...
            0xA1: lda_indirect_x,
            ...
        }

    Why:
    0xA1 means LDA (Indirect,X), written as LDA ($nn,X).
    """
    assert hasattr(opcodes, "lda_indirect_x")
    assert callable(opcodes.lda_indirect_x)
    assert list(inspect.signature(opcodes.lda_indirect_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xA1] is opcodes.lda_indirect_x


def test_opcode_A1_lda_indirect_x_loads_value_into_register_a():
    """
    Objective:
    Implement opcode 0xA1 as LDA (Indirect,X).

    What the opcode handler should do:
    - Use indirect_x(cpu) to get the final address.
    - Read the value from that final address.
    - Use lda(cpu, value) to load register A.

    Example:
    A1 20 means LDA ($20,X).
    If X is 0x04, the zero page pointer is at $0024.
    If RAM[$0024-$0025] points to $1200,
    and RAM[$1200] contains 0x42, register A becomes 0x42.
    """
    cpu, bus, rom = make_cpu_with_rom()

    rom.write(0x0000, 0xA1)
    rom.write(0x0001, 0x20)
    bus.write(0x0024, 0x00)
    bus.write(0x0025, 0x12)
    bus.write(0x1200, 0x42)

    cpu.reset()
    cpu.x = 0x04
    cpu.step()

    assert cpu.a == 0x42
    assert cpu.pc == 0x8002


def test_opcode_A1_lda_indirect_x_uses_wrapped_zero_page_pointer():
    """
    Objective:
    LDA (Indirect,X) must wrap the zero page pointer.

    Example:
    A1 FF means LDA ($FF,X).
    If X is 0x02, the pointer address is $0001.
    If RAM[$0001-$0002] points to $1234,
    and RAM[$1234] contains 0x37, register A becomes 0x37.
    """
    cpu, bus, rom = make_cpu_with_rom()

    rom.write(0x0000, 0xA1)
    rom.write(0x0001, 0xFF)
    bus.write(0x0001, 0x34)
    bus.write(0x0002, 0x12)
    bus.write(0x1234, 0x37)

    cpu.reset()
    cpu.x = 0x02
    cpu.step()

    assert cpu.a == 0x37
    assert cpu.pc == 0x8002


def test_opcode_A1_lda_indirect_x_updates_zero_flag():
    """
    Objective:
    LDA (Indirect,X) must update the Zero flag.

    If the loaded value is 0x00, Zero flag is set.
    """
    cpu, bus, rom = make_cpu_with_rom()

    rom.write(0x0000, 0xA1)
    rom.write(0x0001, 0x20)
    bus.write(0x0024, 0x00)
    bus.write(0x0025, 0x12)
    bus.write(0x1200, 0x00)

    cpu.reset()
    cpu.x = 0x04
    cpu.step()

    assert cpu.a == 0x00
    assert (cpu.p & ZERO_FLAG) != 0


def test_opcode_A1_lda_indirect_x_updates_negative_flag():
    """
    Objective:
    LDA (Indirect,X) must update the Negative flag.

    If the loaded value has bit 7 active, Negative flag is set.
    """
    cpu, bus, rom = make_cpu_with_rom()

    rom.write(0x0000, 0xA1)
    rom.write(0x0001, 0x20)
    bus.write(0x0024, 0x00)
    bus.write(0x0025, 0x12)
    bus.write(0x1200, 0x80)

    cpu.reset()
    cpu.x = 0x04
    cpu.step()

    assert cpu.a == 0x80
    assert (cpu.p & NEGATIVE_FLAG) != 0
