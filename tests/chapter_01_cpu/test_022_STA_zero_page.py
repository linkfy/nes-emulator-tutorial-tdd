"""
Test 022 — Add the STA instruction and zero-page opcode ($85).

Files to update:
    emulator/cpu/instructions.py
    emulator/cpu/opcodes.py

Locations:
    instructions.sta
    opcodes imports of sta and zero_page
    opcodes.sta_zero_page
    opcodes.OPCODE_TABLE[$85]

Why this step exists:
The load lessons passed values into `lda`. STA establishes the complementary write
boundary: an addressing mode supplies a destination address, while the instruction
writes A through the CPU bus without changing processor flags.

Complete example implementation:

    # emulator/cpu/instructions.py
    def sta(cpu, address: int) -> None:
        value = cpu.a
        cpu.bus.write(address, value)


    # emulator/cpu/opcodes.py
    from emulator.cpu.addressing_modes import zero_page
    from emulator.cpu.instructions import sta


    def sta_zero_page(cpu) -> None:
        address = zero_page(cpu)
        sta(cpu, address)


    OPCODE_TABLE = {
        # Preserve existing entries.
        0x85: sta_zero_page,
    }

Important invariants:
    - sta receives an address, not a value read from that address
    - the write goes through cpu.bus.write
    - $85 consumes one operand byte and stores A at $00nn
    - STA leaves Zero and Negative unchanged, including when A is $00 or has bit 7 set

Common misconception:
Do not copy an LDA handler's `cpu.bus.read(address)`: STA writes A to the resolved
address and does not derive flags from the stored byte.

Out of scope:
    - other STA addressing modes
    - adding new addressing-mode helpers
    - cycle timing and write-side hardware effects
"""
import inspect

from emulator.bus.cpu_bus import CpuBus
from emulator.cpu import instructions, opcodes
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


def test_sta_instruction_exists():
    """
    Objective:
    Create in instructions.py:
        def sta(cpu, address):
            ...

    What it does:
    - Read the value from register A.
    - Write that value into the given address.

    Implementation example:
        def sta(cpu, address):
            value = cpu.a
            cpu.bus.write(address, value)

    Important idea:
    LDA receives a value.
    STA receives an address.

    Example:
    If A is 0x42 and address is 0x0010,
    STA writes 0x42 into RAM address $0010.
    """
    assert hasattr(instructions, "sta")
    assert callable(instructions.sta)
    assert list(inspect.signature(instructions.sta).parameters) == ["cpu", "address"]


def test_sta_instruction_writes_register_a_to_address():
    """
    Objective:
    sta(cpu, address) must store register A into memory.

    Example:
    cpu.a is 0x42.
    address is 0x0010.
    After sta(cpu, 0x0010), RAM[$0010] contains 0x42.
    """
    cpu, bus, _ = make_cpu_with_rom()
    cpu.a = 0x42

    instructions.sta(cpu, 0x0010)

    assert bus.read(0x0010) == 0x42


def test_sta_instruction_does_not_change_zero_or_negative_flags():
    """
    Objective:
    STA must not update Zero or Negative flags.

    Unlike LDA, STA only writes memory.
    It does not change flags based on the stored value.
    """
    cpu, _, _ = make_cpu_with_rom()
    cpu.a = 0x00
    cpu.p = NEGATIVE_FLAG

    instructions.sta(cpu, 0x0010)

    assert (cpu.p & ZERO_FLAG) == 0
    assert (cpu.p & NEGATIVE_FLAG) != 0


def test_sta_zero_page_opcode_handler_exists_and_is_in_opcode_table():
    """
    Objective:
    Create in opcodes.py:
        def sta_zero_page(cpu):
            addr = zero_page(cpu)
            sta(cpu, addr)

    Then add opcode 0x85 to OPCODE_TABLE:
        OPCODE_TABLE = {
            ...
            0x85: sta_zero_page,
            ...
        }

    Why:
    0x85 means STA Zero Page.

    Example:
    85 10 means STA $10.
    Store register A into RAM address $0010.
    """
    assert hasattr(opcodes, "sta_zero_page")
    assert callable(opcodes.sta_zero_page)
    assert list(inspect.signature(opcodes.sta_zero_page).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x85] is opcodes.sta_zero_page


def test_opcode_85_sta_zero_page_stores_register_a_into_memory():
    """
    Objective:
    Implement opcode 0x85 as STA Zero Page.

    What the opcode handler should do:
    - Use zero_page(cpu) to get the target address.
    - Use sta(cpu, address) to store register A there.

    Example:
    85 10 means STA $10.
    If A is 0x42, RAM $0010 becomes 0x42.
    """
    cpu, bus, rom = make_cpu_with_rom()

    rom.write(0x0000, 0x85)
    rom.write(0x0001, 0x10)

    cpu.reset()
    cpu.a = 0x42
    cpu.step()

    assert bus.read(0x0010) == 0x42
    assert cpu.pc == 0x8002


def test_opcode_85_sta_zero_page_does_not_change_flags():
    """
    Objective:
    STA Zero Page must not change Zero or Negative flags.

    Example:
    If A is 0x00, STA stores 0x00 into memory.
    But it must not set the Zero flag.
    """
    cpu, bus, rom = make_cpu_with_rom()

    rom.write(0x0000, 0x85)
    rom.write(0x0001, 0x10)

    cpu.reset()
    cpu.a = 0x00
    cpu.p = NEGATIVE_FLAG
    cpu.step()

    assert bus.read(0x0010) == 0x00
    assert (cpu.p & ZERO_FLAG) == 0
    assert (cpu.p & NEGATIVE_FLAG) != 0
