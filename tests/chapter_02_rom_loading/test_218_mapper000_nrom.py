"""
Lesson 218: create
`emulator/cartridge/mapper000.py::Mapper000.read_prg` for NROM CPU mapping.

Why this step exists:
NROM-128 mirrors one 16 KiB bank across $8000-$FFFF; NROM-256 maps 32 KiB
directly. Keeping this translation in the mapper prevents Cartridge from becoming
hardware behavior. It uses the PRG and CHR payloads exposed by lesson 217.

Suggested implementation at this lesson boundary:

    from dataclasses import dataclass

    PRG_ROM_START = 0x8000
    PRG_ROM_END = 0xFFFF
    NROM_128_SIZE = 16 * 1024
    NROM_256_SIZE = 32 * 1024
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

Invariants: accept only CPU $8000-$FFFF and exactly 16 or 32 KiB PRG; mirror only
the 16 KiB case; retain PRG/CHR constructor order. A common mistake is indexing
`prg_rom` with the CPU address directly or implementing the translation on
Cartridge. `read_chr`, PPU routing, CHR RAM, writes, mirroring, and bank switching
are out of scope for this step.

Out of scope for this step:
    1. Lesson 219 adds `read_chr` for the PPU-side CHR range.
    2. Lesson 220 adds mapper selection.
    3. PPU routing, CHR RAM, writes, mirroring, and bank switching come later.
"""

import dataclasses
from pathlib import Path

import pytest

from emulator.cartridge.mapper000 import (
    CHR_ROM_SIZE,
    Mapper000,
    NROM_128_SIZE,
    NROM_256_SIZE,
    PRG_ROM_END,
    PRG_ROM_START,
)


def make_mapper(prg_rom: bytes) -> Mapper000:
    """Create Mapper000 with placeholder CHR ROM for PRG-focused tests."""
    chr_rom = bytes([0x00]) * CHR_ROM_SIZE
    return Mapper000(prg_rom=prg_rom, chr_rom=chr_rom)


def test_mapper000_file_and_constants_exist():
    """
    Step 1: define Mapper000 constants.

    Required constants:
        PRG_ROM_START = 0x8000
            First CPU address where cartridge PRG ROM is visible.

        PRG_ROM_END = 0xFFFF
            Last CPU address in the PRG ROM area.

        NROM_128_SIZE = 16 * 1024
            16KB PRG ROM case. This must be mirrored into $C000-$FFFF.

        NROM_256_SIZE = 32 * 1024
            32KB PRG ROM case. This maps directly across $8000-$FFFF.

    Why constants:
    Mapper code is address-heavy. Constants keep the mapping rules readable and
    prevent magic numbers from hiding the hardware model.
    """
    assert Path("emulator/cartridge/mapper000.py").exists()
    assert PRG_ROM_START == 0x8000
    assert PRG_ROM_END == 0xFFFF
    assert NROM_128_SIZE == 16 * 1024
    assert NROM_256_SIZE == 32 * 1024


def test_mapper000_class_exists_and_stores_prg_and_chr_rom():
    """
    Step 2: define Mapper000.

    Mapper000 should store PRG ROM and CHR ROM bytes.

    At this tutorial step, read_prg is the only behavior we need because the CPU
    bus will eventually ask the mapper how to read addresses $8000-$FFFF.

    CHR ROM is included now because the next test will add read_chr(addr) for
    future PPU pattern-table reads.

    Later tutorial steps may append optional mapper metadata while preserving these
    original fields and their constructor order.
    """
    assert dataclasses.is_dataclass(Mapper000)
    original_fields = ["prg_rom", "chr_rom"]
    field_names = list(Mapper000.__dataclass_fields__)

    assert field_names[: len(original_fields)] == original_fields
    assert hasattr(Mapper000, "read_prg")
    assert callable(Mapper000.read_prg)


def test_mapper000_16kb_prg_reads_lower_bank():
    """
    Objective:
    With 16KB PRG ROM, $8000 maps to PRG offset $0000.
    """
    prg_rom = bytes([0xAA]) + bytes([0x00]) * (NROM_128_SIZE - 1)
    mapper = make_mapper(prg_rom)

    assert mapper.read_prg(0x8000) == 0xAA


def test_mapper000_16kb_prg_mirrors_upper_bank():
    """
    Objective:
    With 16KB PRG ROM, $C000-$FFFF mirrors $8000-$BFFF.

    That means:
        $8000 and $C000 both map to PRG offset $0000.
    """
    prg_rom = bytes([0xAA]) + bytes([0x00]) * (NROM_128_SIZE - 1)
    mapper = make_mapper(prg_rom)

    assert mapper.read_prg(0x8000) == 0xAA
    assert mapper.read_prg(0xC000) == 0xAA


def test_mapper000_16kb_prg_reads_last_mirrored_byte():
    """
    Objective:
    With 16KB PRG ROM, $FFFF maps to PRG offset $3FFF.
    """
    prg_rom = bytes([0x00]) * (NROM_128_SIZE - 1) + bytes([0xEF])
    mapper = make_mapper(prg_rom)

    assert mapper.read_prg(0xBFFF) == 0xEF
    assert mapper.read_prg(0xFFFF) == 0xEF


def test_mapper000_32kb_prg_maps_directly():
    """
    Objective:
    With 32KB PRG ROM, $8000-$FFFF maps directly to offsets $0000-$7FFF.
    """
    prg_rom = bytearray(NROM_256_SIZE)
    prg_rom[0x0000] = 0x11
    prg_rom[0x4000] = 0x22
    prg_rom[0x7FFF] = 0x33
    mapper = make_mapper(bytes(prg_rom))

    assert mapper.read_prg(0x8000) == 0x11
    assert mapper.read_prg(0xC000) == 0x22
    assert mapper.read_prg(0xFFFF) == 0x33


def test_mapper000_rejects_addresses_outside_prg_rom_range():
    """
    Objective:
    Mapper000 should only answer CPU PRG ROM reads in $8000-$FFFF.
    """
    mapper = make_mapper(bytes([0x00]) * NROM_128_SIZE)

    with pytest.raises(ValueError, match="Address out of PRG ROM range"):
        mapper.read_prg(0x7FFF)


def test_mapper000_rejects_unsupported_prg_rom_size():
    """
    Objective:
    Mapper000 supports only NROM-128 and NROM-256 PRG sizes.
    """
    mapper = make_mapper(bytes([0x00]) * 123)

    with pytest.raises(ValueError, match="Mapper000 supports only 16KB or 32KB PRG ROM"):
        mapper.read_prg(0x8000)
