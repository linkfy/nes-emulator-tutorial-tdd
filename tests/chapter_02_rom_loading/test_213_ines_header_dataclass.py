"""
Lesson 213: add
`emulator/cartridge/ines.py::INesHeader`.

Why this step exists:
The object gives names to immutable metadata from the first 16 bytes and retains
raw flags for later format features instead of making downstream code reparse
the source bytes. Lesson 212's layout constants are the prerequisite vocabulary
for the header represented here.

Suggested implementation after lesson 212's constants:

    from dataclasses import dataclass


    @dataclass(frozen=True)
    class INesHeader:
        prg_rom_banks: int
        chr_rom_banks: int
        mapper_number: int
        has_trainer: bool
        flags_6: int
        flags_7: int

Invariants: field order is exact, and the dataclass is frozen because parsed
metadata is a fact about the file. `prg_rom_banks` and `chr_rom_banks` remain
counts, not byte lengths. Do not discard `flags_6`/`flags_7` after deriving the
trainer and mapper values.

Out of scope for this step:
    1. Lesson 214 parses and validates the header bytes.
    2. Lessons 215-216 represent and extract the ROM sections.
    3. Mapper behavior and interpretation of mirroring bits come later.
"""

import dataclasses
import importlib


def test_ines_header_class_exists_and_is_frozen_dataclass():
    """
    Objective:
    Create INesHeader as a frozen dataclass.

    Why frozen:
    Parsed header data is a fact about the file. It should not change during
    emulation.
    """
    ines = importlib.import_module("emulator.cartridge.ines")

    assert hasattr(ines, "INesHeader")
    assert dataclasses.is_dataclass(ines.INesHeader)
    assert ines.INesHeader.__dataclass_params__.frozen is True


def test_ines_header_has_required_fields_in_order():
    """
    Objective:
    Store all header fields needed by the next parser steps.
    """
    ines = importlib.import_module("emulator.cartridge.ines")

    assert list(ines.INesHeader.__dataclass_fields__) == [
        "prg_rom_banks",
        "chr_rom_banks",
        "mapper_number",
        "has_trainer",
        "flags_6",
        "flags_7",
    ]


def test_ines_header_can_store_parsed_values():
    """
    Objective:
    INesHeader should be a small container for parsed header values.
    """
    ines = importlib.import_module("emulator.cartridge.ines")

    header = ines.INesHeader(
        prg_rom_banks=1,
        chr_rom_banks=1,
        mapper_number=0,
        has_trainer=False,
        flags_6=0x00,
        flags_7=0x00,
    )

    assert header.prg_rom_banks == 1
    assert header.chr_rom_banks == 1
    assert header.mapper_number == 0
    assert header.has_trainer is False
    assert header.flags_6 == 0x00
    assert header.flags_7 == 0x00
