"""
Test 008 — Initialize CPU state from the reset vector.

File to update:
    emulator/cpu/cpu.py

Location:
    CPU.reset

Reference:
    https://www.nesdev.org/wiki/CPU_power_up_state

Why this step exists:
The CPU does not choose its program start address directly. On reset it reads a
little-endian 16-bit vector from CPU addresses $FFFC-$FFFD through CpuBus.

Complete example implementation:

    class CPU:
        # Keep the constructor and fetch helpers from Test 004.

        def reset(self) -> None:
            low = self.bus.read(0xFFFC)
            high = self.bus.read(0xFFFD)

            self.pc = low | (high << 8)
            self.s = 0xFD
            self.p = 0x04

Important invariants:
    - vector low byte comes from $FFFC
    - vector high byte comes from $FFFD
    - reset reads through the bus rather than indexing FakeROM directly

Minimal example:
FakeROM offsets $7FFC=$00 and $7FFD=$80 appear at CPU addresses $FFFC-$FFFD and set
PC to $8000. The next fetch therefore reads FakeROM offset $0000.

Common misconception:
Reset must not increment PC while reading the vector. It assigns PC from fixed bus
addresses; instruction fetching begins afterward.

Out of scope:
    - opcode dispatch
    - interrupt entry
    - cycle timing
"""

from emulator.bus.cpu_bus import CpuBus
from emulator.cpu.cpu import CPU
from emulator.memory.fake_rom import FakeROM



def test_cpu_reset_initializes_state():
    """
    For simplicity, this emulator models a power-on reset.
    According to NESdev, after power-up the stack pointer
    is initialized to 0xFD.

    https://www.nesdev.org/wiki/CPU_power_up_state
    - cpu.pc = ($FFFC) [Read internal ROM value]
    - cpu.s = 0xFD 
    - cpu.p = 0x04 
    """

    rom = FakeROM()

    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)

    bus = CpuBus(program_rom=rom)

    cpu = CPU(bus)
    

    cpu.reset()

    assert cpu.pc == 0x8000
    assert cpu.s == 0xFD
    assert cpu.p == 0x04


def test_cpu_fetch_first_opcode():
    """This should pass if everything is right"""

    rom = FakeROM()

    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)
    rom.write(0x0000, 0xA9)

    bus = CpuBus(program_rom=rom)
    cpu = CPU(bus)

    cpu.reset()

    opcode = cpu.fetch_byte()
    assert opcode == 0xA9
