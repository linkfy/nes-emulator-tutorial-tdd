"""
Lesson 219: add
`emulator/cartridge/mapper000.py::Mapper000.read_chr`.

Why this step exists:
This stabilizes access to NROM's 8 KiB graphics payload before a PPU bus exists.
Lesson 218's PRG mapping and `Mapper000` structure are prerequisites.

Complete example implementation after this lesson:

    from dataclasses import dataclass

    PRG_ROM_START = 0x8000
    PRG_ROM_END = 0xFFFF
    NROM_128_SIZE = 16 * 1024
    NROM_256_SIZE = 32 * 1024
    CHR_ROM_START = 0x0000
    CHR_ROM_END = 0x1FFF
    CHR_ROM_SIZE = 8 * 1024


    @dataclass(frozen=True)
    class Mapper000:
        prg_rom: bytes
        chr_rom: bytes

        def read_prg(self, addr: int) -> int:
            if not (PRG_ROM_START <= addr <= PRG_ROM_END):
                raise ValueError(
                    f"Address out of PRG ROM range: {addr:04X}"
                )
            if len(self.prg_rom) == NROM_128_SIZE:
                offset = (addr - PRG_ROM_START) % NROM_128_SIZE
            elif len(self.prg_rom) == NROM_256_SIZE:
                offset = addr - PRG_ROM_START
            else:
                raise ValueError(
                    "Mapper000 supports only 16KB or 32KB PRG ROM"
                )
            return self.prg_rom[offset]

        def read_chr(self, addr: int) -> int:
            if not (CHR_ROM_START <= addr <= CHR_ROM_END):
                raise ValueError(
                    f"Address out of CHR ROM range: {addr:04X}"
                )
            if len(self.chr_rom) != CHR_ROM_SIZE:
                raise ValueError("Mapper000 expects 8KB CHR ROM")
            offset = addr - CHR_ROM_START
            return self.chr_rom[offset]

Invariants: accept only PPU $0000-$1FFF, require exactly 8 KiB CHR ROM, and map
endpoints to offsets 0 and 8191 without changing lesson 218's PRG behavior. Do
not confuse this PPU-side range with CPU PRG $8000-$FFFF.

Out of scope for this step:
    1. Lesson 220 creates mappers from cartridge metadata.
    2. PPU/PpuBus wiring and writable CHR RAM come later.
    3. Mapper writes, nametable mirroring, and bank switching come later.
"""

import pytest

from emulator.cartridge.mapper000 import (
    CHR_ROM_END,
    CHR_ROM_SIZE,
    CHR_ROM_START,
    Mapper000,
    NROM_128_SIZE,
)


def make_mapper_with_chr(chr_rom: bytes) -> Mapper000:
    prg_rom = bytes([0x00]) * NROM_128_SIZE
    return Mapper000(prg_rom=prg_rom, chr_rom=chr_rom)


def test_mapper000_chr_constants_exist():
    """
    Objective:
    Define constants for the PPU CHR ROM address range.

    These are PPU-side addresses, not CPU-side addresses.
    """
    assert CHR_ROM_START == 0x0000
    assert CHR_ROM_END == 0x1FFF
    assert CHR_ROM_SIZE == 8 * 1024


def test_mapper000_stores_chr_rom_bytes():
    """
    Objective:
    Mapper000 stores CHR ROM bytes next to PRG ROM bytes.

    We are not using the PPU yet, but the mapper now has the data the PPU will
    eventually need.
    """
    chr_rom = bytes([0xAA]) * CHR_ROM_SIZE
    mapper = make_mapper_with_chr(chr_rom)

    assert mapper.chr_rom == chr_rom


def test_mapper000_read_chr_reads_first_pattern_table_byte():
    """
    Objective:
    PPU address $0000 maps to CHR ROM offset 0.
    """
    chr_rom = bytes([0xAB]) + bytes([0x00]) * (CHR_ROM_SIZE - 1)
    mapper = make_mapper_with_chr(chr_rom)

    assert mapper.read_chr(0x0000) == 0xAB


def test_mapper000_read_chr_reads_last_pattern_table_byte():
    """
    Objective:
    PPU address $1FFF maps to CHR ROM offset 8191.
    """
    chr_rom = bytes([0x00]) * (CHR_ROM_SIZE - 1) + bytes([0xEF])
    mapper = make_mapper_with_chr(chr_rom)

    assert mapper.read_chr(0x1FFF) == 0xEF


def test_mapper000_read_chr_rejects_addresses_outside_chr_range():
    """
    Objective:
    read_chr should only answer PPU pattern-table addresses $0000-$1FFF.
    """
    chr_rom = bytes([0x00]) * CHR_ROM_SIZE
    mapper = make_mapper_with_chr(chr_rom)

    with pytest.raises(ValueError, match="Address out of CHR ROM range"):
        mapper.read_chr(0x2000)


def test_mapper000_read_chr_rejects_wrong_chr_rom_size():
    """
    Objective:
    For this stage, Mapper000 expects exactly 8KB of CHR ROM.

    Later, cartridges with zero CHR ROM banks may use CHR RAM instead, but that
    is a future feature and should not be hidden in this first implementation.
    """
    mapper = make_mapper_with_chr(bytes([0x00]) * 123)

    with pytest.raises(ValueError, match="Mapper000 expects 8KB CHR ROM"):
        mapper.read_chr(0x0000)
