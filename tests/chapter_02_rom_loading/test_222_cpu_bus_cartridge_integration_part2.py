"""
Read cartridge PRG ROM through CpuBus, part 2.

Prerequisite:
Lesson 221's cartridge field, `__post_init__`, and mapper factory wiring must be
complete before changing the read path here.

File to update:
    emulator/bus/cpu_bus.py

Symbol to update:
    emulator.bus.cpu_bus.CpuBus.read

What this part implements:
    - CpuBus routes CPU reads in $8000-$FFFF to mapper.read_prg(addr) when a
      cartridge-backed mapper exists
    - CpuBus keeps the old program_rom=FakeROM path working
    - CpuBus fails loudly if no PRG source is attached

Why this step exists:
The CPU sees cartridge program ROM at CPU addresses:

    $8000-$FFFF

But cartridge PRG ROM bytes are stored from offset 0. The mapper owns that
translation. CpuBus should only decide that addresses in $8000-$FFFF belong to
the cartridge PRG area, then delegate to the mapper.

Correct cartridge path:

    CpuBus.read($8000)
        -> mapper.read_prg($8000)
        -> Mapper000 translates to PRG offset $0000

Important difference from the old FakeROM path:

    program_rom.read(addr - $8000)

uses an offset because FakeROM is a simple testing device, not a mapper.

    mapper.read_prg(addr)

uses the full CPU address because mappers implement CPU-address translation.

Common mistake:
Do not call mapper.read_prg(addr - 0x8000). That would pass an offset to code
that expects a CPU address in $8000-$FFFF.

Suggested implementation:

    def read(self, addr: int) -> int:
        # Read from CPU Bus.
        if 0x0 <= addr <= 0x1FFF:
            return self.ram.read(addr & 0x07FF)
        if 0x8000 <= addr <= 0xFFFF:
            if self.mapper is not None:
                return self.mapper.read_prg(addr)
            if self.program_rom is not None:
                return self.program_rom.read(addr - 0x8000)
            raise ValueError("No program ROM or cartridge attached")

        raise ValueError(f"Unsupported CPU bus read: {addr:04X}")

Rationale and invariants:
CpuBus owns address-range routing while Mapper000.read_prg owns NROM address
translation. Internal RAM mirroring remains unchanged. Cartridge reads receive
the full CPU address; the legacy MemoryDevice receives a zero-based offset; and
a configured source is required throughout the inclusive $8000-$FFFF range.
The mapper path takes priority only because part 1 forbids both sources from
being configured, so there is never an ambiguous valid construction.

Another common misconception is to copy Mapper000's 16KB modulo rule into
CpuBus. The $C000 mirror assertion is evidence that delegation works, not a new
bus responsibility.

Out of scope:
    1. PPU register reads at $2000-$3FFF belong to Chapter 3.
    2. PRG and mapper writes are not added here.
    3. PPU/CHR routing, timing, and later behavior must not be anticipated.
"""

import pytest

from emulator.bus.cpu_bus import CpuBus
from emulator.cartridge.cartridge import Cartridge
from emulator.cartridge.mapper000 import CHR_ROM_SIZE, NROM_128_SIZE
from emulator.memory.fake_rom import FakeROM


def make_cartridge_with_prg(prg_rom: bytes) -> Cartridge:
    """Create a Mapper000-compatible cartridge with test PRG data."""
    return Cartridge(
        prg_rom=prg_rom,
        chr_rom=bytes([0x00]) * CHR_ROM_SIZE,
        mapper_number=0,
    )


def test_cpu_bus_reads_cartridge_prg_at_8000_through_mapper():
    """
    Objective:
    With a cartridge attached, CpuBus.read($8000) should return the first PRG ROM
    byte through Mapper000.
    """
    prg_rom = bytes([0xA9]) + bytes([0x00]) * (NROM_128_SIZE - 1)
    bus = CpuBus(cartridge=make_cartridge_with_prg(prg_rom))

    assert bus.read(0x8000) == 0xA9


def test_cpu_bus_reads_cartridge_prg_mirror_through_mapper():
    """
    Objective:
    For a 16KB Mapper000 cartridge, $C000 should mirror $8000.

    Why this proves delegation:
    CpuBus should not know this mirroring rule. Mapper000 knows it. If this test
    passes through bus.read($C000), the bus is successfully delegating cartridge
    PRG reads to the mapper.
    """
    prg_rom = bytes([0xEA]) + bytes([0x00]) * (NROM_128_SIZE - 1)
    bus = CpuBus(cartridge=make_cartridge_with_prg(prg_rom))

    assert bus.read(0xC000) == 0xEA


def test_cpu_bus_preserves_old_program_rom_path():
    """
    Objective:
    Existing CPU tutorial tests using program_rom=FakeROM should keep working.

    Why:
    FakeROM is writable and convenient for instruction-level CPU tests. The new
    cartridge path should be additive, not a breaking replacement.
    """
    rom = FakeROM()
    rom.write(0x0000, 0xA9)
    bus = CpuBus(program_rom=rom)

    assert bus.read(0x8000) == 0xA9


def test_cpu_bus_fails_when_prg_area_has_no_source():
    """
    Objective:
    Reading $8000-$FFFF without program_rom or cartridge should fail loudly.

    Why:
    Returning 0 or random data would hide configuration mistakes. A missing PRG
    source means the emulator is not wired correctly.
    """
    bus = CpuBus()

    with pytest.raises(ValueError):
        bus.read(0x8000)
