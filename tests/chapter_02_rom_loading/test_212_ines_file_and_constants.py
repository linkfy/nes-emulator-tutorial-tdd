"""
Lesson 212: define iNES layout constants in
`emulator/cartridge/ines.py`.

Why this step exists:
The iNES format belongs under `cartridge`, not generic memory, because these
values describe a cartridge file container. Defining the shared sizes first
gives the following parser lessons one consistent description of that layout.

Suggested implementation:

    INES_MAGIC = b"NES\x1A"
    INES_HEADER_SIZE = 16
    TRAINER_SIZE = 512
    PRG_ROM_BANK_SIZE = 16 * 1024
    CHR_ROM_BANK_SIZE = 8 * 1024

Invariants: magic is exactly four bytes; headers and trainers are fixed-size;
header bytes 4 and 5 count 16 KiB PRG and 8 KiB CHR banks, respectively. Do not
mistake bank counts for byte lengths or put these format constants in
`emulator/memory/rom.py`.

Out of scope for this step:
    1. Lesson 213 adds `INesHeader`.
    2. Lesson 214 adds `parse_ines_header`.
    3. Lessons 215-216 add `INesRom` and `parse_ines_rom`.
"""

import importlib
from pathlib import Path


def test_cartridge_folder_and_ines_file_exist():
    """
    Objective: place the iNES format constants in the cartridge package.
    """
    assert Path("emulator/cartridge").exists()
    assert Path("emulator/cartridge/ines.py").exists()


def test_ines_module_defines_file_format_constants():
    """
    Objective:
    Define the top-level iNES constants used by the parser.

    These constants describe the binary layout of a .nes file.
    """
    ines = importlib.import_module("emulator.cartridge.ines")

    assert ines.INES_MAGIC == b"NES\x1A"
    assert ines.INES_HEADER_SIZE == 16
    assert ines.TRAINER_SIZE == 512
    assert ines.PRG_ROM_BANK_SIZE == 16 * 1024
    assert ines.CHR_ROM_BANK_SIZE == 8 * 1024
