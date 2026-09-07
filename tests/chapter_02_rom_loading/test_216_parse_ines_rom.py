"""
Lesson 216: add
`emulator/cartridge/ines.py::parse_ines_rom`.

Why this step exists:
This function turns header claims into clean PRG/CHR slices so later Cartridge
and mapper code never needs to understand iNES headers or trainer offsets. It
uses all of the format constants and parser models from lessons 212-215.

Suggested implementation:

    def parse_ines_rom(data: bytes) -> INesRom:
        header = parse_ines_header(data)
        prg_size = header.prg_rom_banks * PRG_ROM_BANK_SIZE
        chr_size = header.chr_rom_banks * CHR_ROM_BANK_SIZE
        prg_start = INES_HEADER_SIZE + (
            TRAINER_SIZE if header.has_trainer else 0
        )
        prg_end = prg_start + prg_size
        chr_start = prg_end
        chr_end = chr_start + chr_size
        if len(data) < chr_end:
            raise ValueError(
                "iNES data is too short for declared PRG/CHR ROM"
            )
        return INesRom(
            header=header,
            prg_rom=data[prg_start:prg_end],
            chr_rom=data[chr_start:chr_end],
        )

Invariants: sizes come from bank counts; PRG starts after the header and optional
512-byte trainer; CHR immediately follows PRG; and all declared bytes must exist
before slicing. Do not rely on forgiving short Python slices, which would accept
a truncated image silently.

Out of scope for this step:
    1. Extra trailing-byte policy and CHR RAM allocation are not introduced here.
    2. Lesson 217 constructs a `Cartridge` from this parser result.
    3. Lessons 218-220 add mapper behavior and mapper selection.
"""

import importlib

import pytest


def make_ines_data(
    prg_banks=1,
    chr_banks=1,
    flags_6=0x00,
    flags_7=0x00,
    trainer=None,
    prg_byte=0xAA,
    chr_byte=0xBB,
):
    ines = importlib.import_module("emulator.cartridge.ines")

    header = bytearray(16)
    header[0:4] = b"NES\x1A"
    header[4] = prg_banks
    header[5] = chr_banks
    header[6] = flags_6
    header[7] = flags_7

    prg = bytes([prg_byte]) * (prg_banks * ines.PRG_ROM_BANK_SIZE)
    chr_ = bytes([chr_byte]) * (chr_banks * ines.CHR_ROM_BANK_SIZE)

    if trainer is None:
        trainer = b""

    return bytes(header) + trainer + prg + chr_


def test_parse_ines_rom_function_exists():
    """Objective: expose parse_ines_rom(data)."""
    ines = importlib.import_module("emulator.cartridge.ines")

    assert hasattr(ines, "parse_ines_rom")
    assert callable(ines.parse_ines_rom)


def test_parse_ines_rom_extracts_prg_and_chr_sections():
    """
    Objective:
    Extract PRG ROM and CHR ROM according to header bank counts.
    """
    ines = importlib.import_module("emulator.cartridge.ines")
    data = make_ines_data(prg_banks=1, chr_banks=1, prg_byte=0xAA, chr_byte=0xBB)

    rom = ines.parse_ines_rom(data)

    assert rom.header.prg_rom_banks == 1
    assert rom.header.chr_rom_banks == 1
    assert len(rom.prg_rom) == ines.PRG_ROM_BANK_SIZE
    assert len(rom.chr_rom) == ines.CHR_ROM_BANK_SIZE
    assert rom.prg_rom == bytes([0xAA]) * ines.PRG_ROM_BANK_SIZE
    assert rom.chr_rom == bytes([0xBB]) * ines.CHR_ROM_BANK_SIZE


def test_parse_ines_rom_supports_multiple_prg_banks():
    """
    Objective:
    Header byte 4 is a PRG bank count. Two banks means 32KB of PRG ROM.
    """
    ines = importlib.import_module("emulator.cartridge.ines")
    data = make_ines_data(prg_banks=2, chr_banks=1)

    rom = ines.parse_ines_rom(data)

    assert len(rom.prg_rom) == 2 * ines.PRG_ROM_BANK_SIZE


def test_parse_ines_rom_skips_trainer_when_present():
    """
    Objective:
    If flags_6 bit 2 is set, skip the 512-byte trainer before PRG ROM.
    """
    ines = importlib.import_module("emulator.cartridge.ines")
    trainer = bytes([0xCC]) * ines.TRAINER_SIZE
    data = make_ines_data(
        flags_6=0b0000_0100,
        trainer=trainer,
        prg_byte=0xAA,
        chr_byte=0xBB,
    )

    rom = ines.parse_ines_rom(data)

    assert rom.header.has_trainer is True
    assert rom.prg_rom[0] == 0xAA
    assert rom.chr_rom[0] == 0xBB
    assert 0xCC not in rom.prg_rom[:16]


def test_parse_ines_rom_rejects_data_shorter_than_declared_sections():
    """
    Objective:
    If the header declares PRG/CHR bytes that are missing, reject the file.
    """
    ines = importlib.import_module("emulator.cartridge.ines")
    data = make_ines_data(prg_banks=1, chr_banks=1)
    truncated = data[:-1]

    with pytest.raises(ValueError, match="iNES data is too short for declared PRG/CHR ROM"):
        ines.parse_ines_rom(truncated)


def test_parse_ines_rom_returns_header_and_sections_together():
    """
    Objective:
    parse_ines_rom should return INesRom(header, prg_rom, chr_rom), not loose
    values.
    """
    ines = importlib.import_module("emulator.cartridge.ines")
    data = make_ines_data(prg_banks=1, chr_banks=1, flags_6=0x20, flags_7=0x40)

    rom = ines.parse_ines_rom(data)

    assert isinstance(rom, ines.INesRom)
    assert isinstance(rom.header, ines.INesHeader)
    assert rom.header.mapper_number == 0x42
