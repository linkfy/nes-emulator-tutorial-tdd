"""
Test 027 — Add indexed-indirect STA ($81, written `(d,X)`).

File to update:
    emulator/cpu/opcodes.py

Locations:
    opcodes.sta_indirect_x
    opcodes.OPCODE_TABLE[$81]

Why this step exists:
Test 020 established `(d,X)` pointer resolution for loads. This lesson reuses that
same final-address calculation as a store destination, keeping pointer mechanics out
of the `sta` instruction.

Complete example implementation:

    # emulator/cpu/opcodes.py
    def sta_indirect_x(cpu) -> None:
        address = indirect_x(cpu)
        sta(cpu, address)


    OPCODE_TABLE = {
        # Preserve existing entries.
        0x81: sta_indirect_x,
    }

Important invariants:
    - X indexes the zero-page pointer location before dereferencing
    - pointer selection and its high-byte read wrap within zero page
    - the pointer's 16-bit result is the write destination
    - $81 consumes one operand byte and does not update flags

Common misconception:
Do not add X to the final pointer value. In `(d,X)`, X chooses where the pointer is
read, and `sta` writes A to the address held by that pointer.

Out of scope:
    - changes to indirect_x or sta
    - indirect,Y STA
    - cycle timing
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


def test_sta_indirect_x_handler_exists_and_is_in_opcode_table():
    """
    Objective:
    Create sta_indirect_x(cpu) and add 0x81 to OPCODE_TABLE.
    """
    assert hasattr(opcodes, "sta_indirect_x")
    assert callable(opcodes.sta_indirect_x)
    assert list(inspect.signature(opcodes.sta_indirect_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x81] is opcodes.sta_indirect_x


def test_opcode_81_sta_indirect_x_stores_register_a():
    """
    Objective:
    81 20 means STA ($20,X).
    If X is 0x04, pointer is at $0024.
    If RAM[$0024-$0025] points to $0200, store A into $0200.
    """
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x81)
    rom.write(0x0001, 0x20)
    bus.write(0x0024, 0x00)
    bus.write(0x0025, 0x02)

    cpu.reset()
    cpu.a = 0x42
    cpu.x = 0x04
    cpu.step()

    assert bus.read(0x0200) == 0x42
    assert cpu.pc == 0x8002
