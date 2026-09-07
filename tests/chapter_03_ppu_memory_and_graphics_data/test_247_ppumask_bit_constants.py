"""
Define PPUMASK ($2001) bit constants.

Reference:
    https://www.nesdev.org/wiki/PPU_registers#PPUMASK

File to update:
    emulator/ppu/ppu.py

Constants to add:
    MASK_GRAYSCALE
    MASK_SHOW_BACKGROUND_LEFT_8
    MASK_SHOW_SPRITES_LEFT_8
    MASK_SHOW_BACKGROUND
    MASK_SHOW_SPRITES
    MASK_EMPHASIZE_RED
    MASK_EMPHASIZE_GREEN
    MASK_EMPHASIZE_BLUE

Why this step exists:
PPUMASK is the CPU-writable rendering mask register at $2001. It controls which
parts of rendering are visible and how colors are emphasized.

The bit layout is commonly written as:

    BGRs bMmG

Meaning:
    B = emphasize blue
    G = emphasize green
    R = emphasize red
    s = show sprites
    b = show background
    M = show sprites in leftmost 8 pixels
    m = show background in leftmost 8 pixels
    G = grayscale

Important scope:
This test only requires named constants. Rendering behavior will use these names
later. Do not implement actual grayscale, color emphasis, background rendering,
or sprite rendering in this step.

Suggested implementation pseudocode:

    # PPUMASK ($2001) bits: BGRs bMmG
    MASK_GRAYSCALE = 1 << 0
    MASK_SHOW_BACKGROUND_LEFT_8 = 1 << 1
    MASK_SHOW_SPRITES_LEFT_8 = 1 << 2
    MASK_SHOW_BACKGROUND = 1 << 3
    MASK_SHOW_SPRITES = 1 << 4
    MASK_EMPHASIZE_RED = 1 << 5
    MASK_EMPHASIZE_GREEN = 1 << 6
    MASK_EMPHASIZE_BLUE = 1 << 7

Common value:
    $1E == 0b0001_1110

This enables:
    - background left 8 pixels
    - sprites left 8 pixels
    - background rendering
    - sprite rendering

Out of scope:
    - actual pixel rendering
    - grayscale palette behavior
    - color emphasis behavior
    - left-edge clipping behavior
"""

from emulator.ppu.ppu import (
    MASK_EMPHASIZE_BLUE,
    MASK_EMPHASIZE_GREEN,
    MASK_EMPHASIZE_RED,
    MASK_GRAYSCALE,
    MASK_SHOW_BACKGROUND,
    MASK_SHOW_BACKGROUND_LEFT_8,
    MASK_SHOW_SPRITES,
    MASK_SHOW_SPRITES_LEFT_8,
)


def test_ppumask_bit_constants_match_bgrs_bmmg_layout():
    """
    Objective:
    Name every PPUMASK bit using the BGRs bMmG layout.
    """
    assert MASK_GRAYSCALE == 1 << 0
    assert MASK_SHOW_BACKGROUND_LEFT_8 == 1 << 1
    assert MASK_SHOW_SPRITES_LEFT_8 == 1 << 2
    assert MASK_SHOW_BACKGROUND == 1 << 3
    assert MASK_SHOW_SPRITES == 1 << 4
    assert MASK_EMPHASIZE_RED == 1 << 5
    assert MASK_EMPHASIZE_GREEN == 1 << 6
    assert MASK_EMPHASIZE_BLUE == 1 << 7


def test_ppumask_common_rendering_enable_value_1e_sets_expected_bits():
    """
    Objective:
    Show why $1E is commonly used in examples.

    $1E enables background/sprites and their left-edge visibility, but does not
    enable grayscale or color emphasis.
    """
    value = 0x1E

    assert value & MASK_SHOW_BACKGROUND_LEFT_8
    assert value & MASK_SHOW_SPRITES_LEFT_8
    assert value & MASK_SHOW_BACKGROUND
    assert value & MASK_SHOW_SPRITES

    assert not value & MASK_GRAYSCALE
    assert not value & MASK_EMPHASIZE_RED
    assert not value & MASK_EMPHASIZE_GREEN
    assert not value & MASK_EMPHASIZE_BLUE


def test_ppumask_flags_do_not_overlap():
    """
    Objective:
    Each PPUMASK flag should occupy its own bit.
    """
    flags = [
        MASK_GRAYSCALE,
        MASK_SHOW_BACKGROUND_LEFT_8,
        MASK_SHOW_SPRITES_LEFT_8,
        MASK_SHOW_BACKGROUND,
        MASK_SHOW_SPRITES,
        MASK_EMPHASIZE_RED,
        MASK_EMPHASIZE_GREEN,
        MASK_EMPHASIZE_BLUE,
    ]

    combined = 0
    for flag in flags:
        assert combined & flag == 0
        combined |= flag
