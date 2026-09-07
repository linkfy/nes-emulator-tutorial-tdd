"""
Route PpuBus CHR-area reads through the mapper.

File to update:
    emulator/bus/ppu_bus.py

Constants to add/use:
    CHR_START = 0x0000
    CHR_END = 0x1FFF

What is the CHR area?
The PPU address range $0000-$1FFF is the pattern table area. It contains tile
graphics bytes used later for background and sprite pixels.

Important NES fact:
This area often belongs to the cartridge, not internal VRAM.

    CHR ROM cartridge:
        PPU reads pattern bytes from cartridge CHR ROM.

    CHR RAM cartridge:
        PPU can write pattern bytes into cartridge CHR RAM.

Current scope:
For now, PpuBus must detect CHR-area addresses. Reads should use
mapper.read_chr(addr) when a mapper exists.

We intentionally do not lock down CHR write behavior in this test. A future step
may add mapper.write_chr(addr, value) for CHR RAM support, and this test should
not block that evolution.

Suggested read pseudocode:

    def read(self, addr: int) -> int:
        addr = addr & PPU_ADDRESS_MASK

        if CHR_START <= addr <= CHR_END:
            if self.mapper is not None:
                return self.mapper.read_chr(addr)
            return self.vram.read(addr)

        return self.vram.read(addr)

Possible current write pseudocode:

    def write(self, addr: int, value: int) -> None:
        addr = addr & PPU_ADDRESS_MASK

        if CHR_START <= addr <= CHR_END:
            if self.mapper is not None:
                raise ValueError("CHR writes are not supported yet")
            self.vram.write(addr, value)
            return

        self.vram.write(addr, value)

Possible future write pseudocode:

    if CHR_START <= addr <= CHR_END and self.mapper is not None:
        self.mapper.write_chr(addr, value)
        return

Future regions:
    $2000-$3EFF:
        currently backed by big VRAM, later nametable VRAM/mirroring

    $3F00-$3FFF:
        currently backed by big VRAM, later palette RAM/mirroring
"""

from emulator.bus.ppu_bus import CHR_END, CHR_START, PpuBus


class FakeMapper:
    """Small mapper test double for CHR read routing."""

    def read_prg(self, addr: int) -> int:
        return 0xEA

    def read_chr(self, addr: int) -> int:
        if addr == 0x0000:
            return 0x11
        if addr == 0x1FFF:
            return 0x22
        return 0x33


def test_ppu_bus_declares_chr_area_constants():
    """
    Objective:
    Name the PPU pattern-table / CHR address range.
    """
    assert CHR_START == 0x0000
    assert CHR_END == 0x1FFF


def test_ppu_bus_reads_chr_area_from_mapper_when_mapper_exists():
    """
    Objective:
    PPU $0000-$1FFF reads should go through mapper.read_chr when a mapper is
    attached.
    """
    bus = PpuBus(mapper=FakeMapper())

    assert bus.read(0x0000) == 0x11
    assert bus.read(0x1FFF) == 0x22


def test_ppu_bus_falls_back_to_vram_for_chr_area_when_no_mapper_exists():
    """
    Objective:
    Without a mapper, the temporary big VRAM backing store can still serve CHR
    area accesses.

    Why:
    This keeps early PPU memory tests simple before cartridge CHR routing is
    connected everywhere.
    """
    bus = PpuBus()
    bus.vram.write(0x0000, 0x44)

    assert bus.read(0x0000) == 0x44

