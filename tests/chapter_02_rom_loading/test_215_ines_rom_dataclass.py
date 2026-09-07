"""
Lesson 215: add
`emulator/cartridge/ines.py::INesRom`.

Why this step exists:
This immutable parser result keeps the interpreted header and extracted program
and graphics sections together so `parse_ines_rom` need not return loose values.
It builds on the header model and parser from lessons 213-214.

Suggested implementation after `parse_ines_header`:

    @dataclass(frozen=True)
    class INesRom:
        header: INesHeader
        prg_rom: bytes
        chr_rom: bytes

Invariants: the field order is `header`, `prg_rom`, `chr_rom`; both payloads are
`bytes`; and the dataclass is frozen because it describes file contents. Do not
confuse this format-level result with the emulator-facing `Cartridge`.

Out of scope for this step:
    1. Lesson 216 calculates offsets, skips trainers, and validates payload size.
    2. Lesson 217 introduces the emulator-facing `Cartridge`.
    3. Lessons 218-219 implement mapper address translation.
"""

import dataclasses
import importlib


def test_ines_rom_class_exists_and_is_frozen_dataclass():
    """
    Objective:
    Create INesRom as a frozen dataclass.

    Why frozen:
    Parsed ROM sections are facts extracted from the file. They should not be
    mutated by the parser result object.
    """
    ines = importlib.import_module("emulator.cartridge.ines")

    assert hasattr(ines, "INesRom")
    assert dataclasses.is_dataclass(ines.INesRom)
    assert ines.INesRom.__dataclass_params__.frozen is True


def test_ines_rom_has_required_fields_in_order():
    """Objective: INesRom stores header, PRG ROM, and CHR ROM."""
    ines = importlib.import_module("emulator.cartridge.ines")

    assert list(ines.INesRom.__dataclass_fields__) == [
        "header",
        "prg_rom",
        "chr_rom",
    ]


def test_ines_rom_can_store_header_prg_and_chr_bytes():
    """
    Objective:
    INesRom should group parsed metadata with extracted ROM byte sections.
    """
    ines = importlib.import_module("emulator.cartridge.ines")
    header = ines.INesHeader(1, 1, 0, False, 0x00, 0x00)

    rom = ines.INesRom(
        header=header,
        prg_rom=bytes([0xA9, 0x42]),
        chr_rom=bytes([0x00, 0x01]),
    )

    assert rom.header is header
    assert rom.prg_rom == bytes([0xA9, 0x42])
    assert rom.chr_rom == bytes([0x00, 0x01])
