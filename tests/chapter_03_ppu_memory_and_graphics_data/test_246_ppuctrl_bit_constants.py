"""
Define PPUCTRL ($2000) bit constants.

Reference:
    https://www.nesdev.org/wiki/PPU_registers#PPUCTRL

File to update:
    emulator/ppu/ppu.py

Constants to add:
    CTRL_BASE_NAMETABLE_MASK
    CTRL_VRAM_INCREMENT_BY_32
    CTRL_SPRITE_PATTERN_TABLE
    CTRL_BACKGROUND_PATTERN_TABLE
    CTRL_SPRITE_SIZE_8X16
    CTRL_MASTER_SLAVE_SELECT
    CTRL_NMI_ENABLE

Why this step exists:
PPUCTRL is the CPU-writable control register at $2000. It is one byte, and each
bit or bit-field controls a different PPU behavior.

The bit layout is commonly written as:

    VPHB SINN

Meaning:
    V = NMI enable at VBlank
    P = master/slave select, mostly unused on normal NES
    H = sprite size, 8x8 or 8x16
    B = background pattern table address
    S = sprite pattern table address
    I = PPUDATA VRAM address increment, +1 or +32
    NN = base nametable select, two-bit field

Important scope:
This test only requires named constants. Most behavior controlled by these bits
will be implemented later when rendering, VBlank/NMI, and sprites exist.

Already implemented behavior:
    CTRL_VRAM_INCREMENT_BY_32 controls whether PPUDATA increments vram_addr by
    1 or 32.

Suggested implementation pseudocode:

    # PPUCTRL ($2000) bits: VPHB SINN
    CTRL_BASE_NAMETABLE_MASK = 0b0000_0011
    CTRL_VRAM_INCREMENT_BY_32 = 1 << 2
    CTRL_SPRITE_PATTERN_TABLE = 1 << 3
    CTRL_BACKGROUND_PATTERN_TABLE = 1 << 4
    CTRL_SPRITE_SIZE_8X16 = 1 << 5
    CTRL_MASTER_SLAVE_SELECT = 1 << 6
    CTRL_NMI_ENABLE = 1 << 7

Out of scope:
    - NMI generation
    - sprite size behavior
    - pattern table rendering behavior
    - base nametable behavior
    - master/slave EXT pin behavior
"""

from emulator.ppu.ppu import (
    CTRL_BACKGROUND_PATTERN_TABLE,
    CTRL_BASE_NAMETABLE_MASK,
    CTRL_MASTER_SLAVE_SELECT,
    CTRL_NMI_ENABLE,
    CTRL_SPRITE_PATTERN_TABLE,
    CTRL_SPRITE_SIZE_8X16,
    CTRL_VRAM_INCREMENT_BY_32,
)


def test_ppuctrl_bit_constants_match_vphb_sinn_layout():
    """
    Objective:
    Name every PPUCTRL bit or bit-field using the VPHB SINN layout.
    """
    assert CTRL_BASE_NAMETABLE_MASK == 0b0000_0011
    assert CTRL_VRAM_INCREMENT_BY_32 == 1 << 2
    assert CTRL_SPRITE_PATTERN_TABLE == 1 << 3
    assert CTRL_BACKGROUND_PATTERN_TABLE == 1 << 4
    assert CTRL_SPRITE_SIZE_8X16 == 1 << 5
    assert CTRL_MASTER_SLAVE_SELECT == 1 << 6
    assert CTRL_NMI_ENABLE == 1 << 7


def test_ppuctrl_base_nametable_is_two_bit_field():
    """
    Objective:
    Base nametable selection uses bits 0-1, not a single boolean flag.

    Values:
        0 -> $2000
        1 -> $2400
        2 -> $2800
        3 -> $2C00

    We only define the mask now. Behavior comes later.
    """
    assert 0b0000_0000 & CTRL_BASE_NAMETABLE_MASK == 0
    assert 0b0000_0001 & CTRL_BASE_NAMETABLE_MASK == 1
    assert 0b0000_0010 & CTRL_BASE_NAMETABLE_MASK == 2
    assert 0b0000_0011 & CTRL_BASE_NAMETABLE_MASK == 3


def test_ppuctrl_single_bit_flags_do_not_overlap():
    """
    Objective:
    Each single-bit PPUCTRL flag should occupy its own bit.

    Why:
    If constants overlap, checking one feature could accidentally detect another.
    """
    flags = [
        CTRL_VRAM_INCREMENT_BY_32,
        CTRL_SPRITE_PATTERN_TABLE,
        CTRL_BACKGROUND_PATTERN_TABLE,
        CTRL_SPRITE_SIZE_8X16,
        CTRL_MASTER_SLAVE_SELECT,
        CTRL_NMI_ENABLE,
    ]

    combined = 0
    for flag in flags:
        assert combined & flag == 0
        combined |= flag
