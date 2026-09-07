"""
Test 064 - Add SBC Zero Page.

File to update:
    emulator/cpu/opcodes.py

Symbols to add/update:
    opcodes.sbc_zero_page and OPCODE_TABLE[0xE5]

Why this step exists:
This lesson adds the first memory-addressed SBC wrapper, reusing the established
zero-page address resolver and the core value-based `sbc` operation.

Complete example implementation:

    # emulator/cpu/opcodes.py
    def sbc_zero_page(cpu: CPU):
        addr = zero_page(cpu)
        value = cpu.bus.read(addr)
        sbc(cpu, value)

    OPCODE_TABLE = {
        # ... existing entries ...
        0xE5: sbc_zero_page,
    }

Important invariants:
    - `zero_page` fetches one operand and returns an address in page $00
    - the handler reads one byte from that address and passes the value to `sbc`
    - SBC's arithmetic and flag behavior remains centralized in `sbc`
    - executing the two-byte instruction advances PC by two bytes

Common misconception:
`zero_page` returns an address, not the byte to subtract; the handler must perform
the bus read before calling `sbc`.

Out of scope:
    - indexed, absolute, and indirect SBC wrappers
    - changes to zero-page addressing or SBC arithmetic
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


def test_sbc_zero_page_handler_exists_and_is_in_opcode_table():
    """Objective: create sbc_zero_page(cpu) and add 0xE5 to OPCODE_TABLE."""
    assert hasattr(opcodes, "sbc_zero_page")
    assert callable(opcodes.sbc_zero_page)
    assert list(inspect.signature(opcodes.sbc_zero_page).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0xE5] is opcodes.sbc_zero_page


def test_opcode_E5_sbc_zero_page_subtracts_value_from_memory():
    """Objective: E5 10 means SBC $10, so subtract RAM[$0010] from A."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0xE5)
    rom.write(0x0001, 0x10)
    bus.write(0x0010, 0x01)

    cpu.reset()
    cpu.a = 0x10
    cpu.flags.set_carry_flag(True)
    cpu.step()

    assert cpu.a == 0x0F
    assert cpu.pc == 0x8002
