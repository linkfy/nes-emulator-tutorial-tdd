"""
Test 048 - Add STY zero page,X ($94).

File to update:
    emulator/cpu/opcodes.py

Locations:
    opcodes imports of zero_page_x and sty
    opcodes.sty_zero_page_x
    opcodes.OPCODE_TABLE[$94]

Why this step exists:
This encoding combines STY's address-oriented instruction boundary with the existing
zero-page,X helper, including wraparound inside page $00.

Complete example implementation:

    # emulator/cpu/opcodes.py
    from emulator.cpu.addressing_modes import zero_page_x
    from emulator.cpu.instructions import sty


    def sty_zero_page_x(cpu: CPU):
        addr = zero_page_x(cpu)
        sty(cpu, addr)


    OPCODE_TABLE = {
        # Preserve existing entries.
        0x94: sty_zero_page_x,
    }

Important invariants:
    - $94 maps to sty_zero_page_x and consumes one operand byte
    - X indexes the operand and the effective address wraps to eight bits
    - the effective address, not its current contents, is passed to sty
    - Y and processor flags are unchanged by the store

Common misconception:
`$FF,X` with X equal to $01 stores at $0000, not $0100; zero-page indexing must not
escape page $00.

Out of scope:
    - absolute STY
    - changing zero_page_x
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


def test_sty_zero_page_x_handler_exists_and_is_in_opcode_table():
    """Objective: create sty_zero_page_x(cpu) and add 0x94 to OPCODE_TABLE."""
    assert hasattr(opcodes, "sty_zero_page_x")
    assert callable(opcodes.sty_zero_page_x)
    assert list(inspect.signature(opcodes.sty_zero_page_x).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x94] is opcodes.sty_zero_page_x


def test_opcode_94_sty_zero_page_x_stores_register_y():
    """Objective: 94 10 with X=0x03 stores Y into RAM[$0013]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x94)
    rom.write(0x0001, 0x10)

    cpu.reset()
    cpu.y = 0x42
    cpu.x = 0x03
    cpu.step()

    assert bus.read(0x0013) == 0x42
    assert cpu.pc == 0x8002


def test_opcode_94_sty_zero_page_x_wraps():
    """Objective: Zero Page,X wraps inside page $00."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x94)
    rom.write(0x0001, 0xFF)

    cpu.reset()
    cpu.y = 0x37
    cpu.x = 0x01
    cpu.step()

    assert bus.read(0x0000) == 0x37
    assert cpu.pc == 0x8002
