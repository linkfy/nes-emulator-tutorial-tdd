"""
Test 007 — Map FakeROM into the CPU program-ROM address range.

File to update:
    emulator/bus/cpu_bus.py

Location:
    class CpuBus

Reference:
    https://en.wikibooks.org/wiki/NES_Programming/Memory_Map

Why this step exists:
CPU addresses $8000-$FFFF must fetch program bytes from local FakeROM offsets
$0000-$7FFF. The bus owns this translation; the memory device sees only local offsets.

Complete example implementation:

    from dataclasses import dataclass, field
    from typing import Optional

    from emulator.memory.memory_device import MemoryDevice
    from emulator.memory.ram import RAM


    @dataclass
    class CpuBus:
        program_rom: Optional[MemoryDevice] = None
        ram: RAM = field(default_factory=RAM)

        def read(self, addr: int) -> int:
            if 0x0000 <= addr <= 0x1FFF:
                return self.ram.read(addr & 0x07FF)

            if 0x8000 <= addr <= 0xFFFF:
                if self.program_rom is None:
                    raise ValueError("No program ROM attached")
                return self.program_rom.read(addr - 0x8000)

            raise ValueError(f"Unsupported CPU bus read: {addr:04X}")

        def write(self, addr: int, value: int) -> None:
            if 0x0000 <= addr <= 0x1FFF:
                self.ram.write(addr & 0x07FF, value)
                return

            raise ValueError(f"Unsupported CPU bus write: {addr:04X}")

Important invariant:
    rom_offset = cpu_address - 0x8000

Common misconception:
The reset-vector CPU address $FFFC is not FakeROM index $FFFC. After bus translation,
it is local index $7FFC.

Out of scope:
    - CPU reset
    - real cartridge parsing and mappers
    - writes to cartridge space
"""

from emulator.bus.cpu_bus import CpuBus
from emulator.memory.fake_rom import FakeROM
from emulator.memory.memory_device import MemoryDevice



def test_cpu_bus_contains_program_rom_parameter():
    rom = FakeROM()
    cpu_bus = CpuBus(program_rom=rom)

    assert hasattr(cpu_bus, "program_rom")
    assert isinstance(cpu_bus.program_rom, MemoryDevice)


def test_cpu_bus_reads_program_rom():
    """At this point 
    CPU addresses 0x8000-0xFFFF should map to
    ROM offsets 0x0000-0x7FFF (Total = 0x8000)

    https://en.wikibooks.org/wiki/NES_Programming/Memory_Map
    """

    rom = FakeROM()

    for offset in range(0x8000):
        rom.write(offset, offset & 0xFF)

    bus = CpuBus(program_rom=rom)

    for offset in range(0x8000):
        cpu_addr = 0x8000 + offset

        assert bus.read(cpu_addr) == (offset & 0xFF)
