"""
Lesson 214: add
`emulator/cartridge/ines.py::parse_ines_header`.

Why this step exists:
The parser validates the fixed envelope before converting bytes 4-7 into the
immutable `INesHeader` introduced in lesson 213. It depends on the constants
from lesson 212 and the dataclass from lesson 213.

Suggested implementation:

    def parse_ines_header(data: bytes) -> INesHeader:
        if len(data) < INES_HEADER_SIZE:
            raise ValueError("iNES data is too short")
        if data[0:4] != INES_MAGIC:
            raise ValueError("Invalid iNES header")

        prg_rom_banks = data[4]
        chr_rom_banks = data[5]
        flags_6 = data[6]
        flags_7 = data[7]
        has_trainer = (flags_6 & 0b0000_0100) != 0
        mapper_number = (flags_6 >> 4) | (flags_7 & 0xF0)
        return INesHeader(
            prg_rom_banks,
            chr_rom_banks,
            mapper_number,
            has_trainer,
            flags_6,
            flags_7,
        )

Invariants: reject short input before indexing it; require `b"NES\x1A"`; use
flags 6's upper nibble as mapper bits 0-3 and flags 7's upper nibble as bits 4-7;
preserve both raw flags. A common mistake is multiplying bytes 4 and 5 here:
they remain bank counts.

Out of scope for this step:
    1. Lesson 215 groups a parsed header with ROM sections.
    2. Lesson 216 extracts and validates declared PRG/CHR payload bytes.
"""

import importlib

import pytest


def make_header_bytes(
    prg_banks=1,
    chr_banks=1,
    flags_6=0x00,
    flags_7=0x00,
):
    header = bytearray(16)
    header[0:4] = b"NES\x1A"
    header[4] = prg_banks
    header[5] = chr_banks
    header[6] = flags_6
    header[7] = flags_7
    return bytes(header)


def test_parse_ines_header_function_exists():
    """Objective: expose parse_ines_header(data)."""
    ines = importlib.import_module("emulator.cartridge.ines")

    assert hasattr(ines, "parse_ines_header")
    assert callable(ines.parse_ines_header)


def test_parse_ines_header_rejects_data_shorter_than_header():
    """
    Objective:
    A valid iNES file needs at least the 16-byte header.
    """
    ines = importlib.import_module("emulator.cartridge.ines")

    with pytest.raises(ValueError, match="iNES data is too short"):
        ines.parse_ines_header(b"NES")


def test_parse_ines_header_rejects_invalid_magic_bytes():
    """
    Objective:
    The first four bytes must be b"NES\\x1A".
    """
    ines = importlib.import_module("emulator.cartridge.ines")
    data = bytearray(make_header_bytes())
    data[0:4] = b"BAD!"

    with pytest.raises(ValueError, match="Invalid iNES header"):
        ines.parse_ines_header(bytes(data))


def test_parse_ines_header_returns_expected_values():
    """
    Objective:
    Convert raw header bytes into an INesHeader object.

    Example:
        byte 4 = 2 means two 16KB PRG banks
        byte 5 = 1 means one 8KB CHR bank
    """
    ines = importlib.import_module("emulator.cartridge.ines")
    data = make_header_bytes(prg_banks=2, chr_banks=1, flags_6=0x00, flags_7=0x00)

    header = ines.parse_ines_header(data)

    assert header == ines.INesHeader(
        prg_rom_banks=2,
        chr_rom_banks=1,
        mapper_number=0,
        has_trainer=False,
        flags_6=0x00,
        flags_7=0x00,
    )


def test_parse_ines_header_detects_trainer_bit():
    """
    Objective:
    Bit 2 of flags_6 tells us whether a 512-byte trainer exists.
    """
    ines = importlib.import_module("emulator.cartridge.ines")
    data = make_header_bytes(flags_6=0b0000_0100)

    header = ines.parse_ines_header(data)

    assert header.has_trainer is True


def test_parse_ines_header_calculates_mapper_number_from_flags_6_and_7():
    """
    Objective:
    Mapper number combines upper nibble of flags_6 and upper nibble of flags_7.

    Example:
        flags_6 = 0x20 -> lower mapper nibble = 0x02
        flags_7 = 0x40 -> upper mapper nibble = 0x40
        mapper_number = 0x42
    """
    ines = importlib.import_module("emulator.cartridge.ines")
    data = make_header_bytes(flags_6=0x20, flags_7=0x40)

    header = ines.parse_ines_header(data)

    assert header.mapper_number == 0x42
    assert header.flags_6 == 0x20
    assert header.flags_7 == 0x40
