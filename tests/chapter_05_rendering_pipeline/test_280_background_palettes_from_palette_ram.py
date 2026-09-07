"""
Build RGB background palettes from PPU palette RAM bytes.

Reference:
    https://www.nesdev.org/wiki/PPU_palettes#Palette_RAM

File to create:
    emulator/rendering/palette_ram.py

Why this step exists:
The attribute-aware nametable renderer expects four resolved RGB background
palettes:

    background_palettes[palette_id][color_index]

But real NES games do not store RGB colors in the nametable or attribute table.
They write NES color indexes into PPU palette RAM.

This helper converts:

    PPU palette RAM bytes -> RGB background palettes

What is PPU palette RAM?
PPU palette RAM is a small 32-byte area mapped at:

    $3F00-$3F1F

For this step we only use the first 16 bytes:

    $3F00-$3F0F = background palette area

Those bytes store NES color indexes $00-$3F, not RGB values.

Flow:

    palette RAM byte
        -> NES color index $00-$3F
        -> get_nes_rgb_color(index)
        -> RGB tuple

Backdrop / universal background color:
For background rendering, color index 0 uses the shared backdrop color at $3F00.
So every returned background palette uses the same first RGB color:

    background_palettes[0][0] == backdrop
    background_palettes[1][0] == backdrop
    background_palettes[2][0] == backdrop
    background_palettes[3][0] == backdrop

Background palette layout for $3F00-$3F0F:

    $3F00 -> backdrop / universal background color

    palette 0:
        entry 0 -> $3F00
        entry 1 -> $3F01
        entry 2 -> $3F02
        entry 3 -> $3F03

    palette 1:
        entry 0 -> $3F00
        entry 1 -> $3F05
        entry 2 -> $3F06
        entry 3 -> $3F07

    palette 2:
        entry 0 -> $3F00
        entry 1 -> $3F09
        entry 2 -> $3F0A
        entry 3 -> $3F0B

    palette 3:
        entry 0 -> $3F00
        entry 1 -> $3F0D
        entry 2 -> $3F0E
        entry 3 -> $3F0F

Notice:
    $3F04, $3F08, and $3F0C are not used as independent background color-0
    entries in this simplified helper. Color index 0 uses the shared backdrop.

Suggested implementation example:

    from emulator.rendering.framebuffer import RGBColor
    from emulator.rendering.nes_palette import get_nes_rgb_color

    PALETTE_RAM_SIZE = 16
    TOTAL_PALETTES = 4
    COLORS_PER_PALETTE = 4

    BackgroundPalettes = list[list[RGBColor]]


    def build_background_palettes_from_palette_ram(
        palette_ram: bytes,
    ) -> BackgroundPalettes:
        if len(palette_ram) != PALETTE_RAM_SIZE:
            raise ValueError(f"Background palette RAM must be {PALETTE_RAM_SIZE} bytes")

        backdrop_color = get_nes_rgb_color(palette_ram[0])
        background_palettes = []

        for palette_id in range(TOTAL_PALETTES):
            base = palette_id * COLORS_PER_PALETTE

            palette = [
                backdrop_color,
                get_nes_rgb_color(palette_ram[base + 1]),
                get_nes_rgb_color(palette_ram[base + 2]),
                get_nes_rgb_color(palette_ram[base + 3]),
            ]

            background_palettes.append(palette)

        return background_palettes

Out of scope:
    - sprite palettes
    - sprite transparency behavior
    - palette RAM mirroring
    - reading from PPU bus directly
    - PPUMASK emphasis colors
    - pygame display
"""

from pathlib import Path

import pytest

from emulator.rendering.nes_palette import get_nes_rgb_color
from emulator.rendering.palette_ram import (
    BackgroundPalettes,
    COLORS_PER_PALETTE,
    PALETTE_RAM_SIZE,
    TOTAL_PALETTES,
    build_background_palettes_from_palette_ram,
)


def make_background_palette_ram() -> bytes:
    """
    Create synthetic $3F00-$3F0F background palette RAM bytes.

    Values are NES color indexes, not RGB colors.
    """
    return bytes([
        0x0F, 0x01, 0x02, 0x03,
        0x04, 0x11, 0x12, 0x13,
        0x08, 0x21, 0x22, 0x23,
        0x0C, 0x31, 0x32, 0x33,
    ])


def test_palette_ram_file_exists():
    """
    Objective:
    Keep palette RAM conversion separate from nametable rendering and framebuffer
    storage.
    """
    assert Path("emulator/rendering/palette_ram.py").exists()


def test_palette_ram_declares_background_palette_constants():
    """
    Objective:
    Name the simplified background palette RAM shape used by this helper.
    """
    assert PALETTE_RAM_SIZE == 16
    assert TOTAL_PALETTES == 4
    assert COLORS_PER_PALETTE == 4


def test_background_palettes_type_alias_and_builder_exist():
    """
    Objective:
    Expose a builder that converts palette RAM bytes into four RGB palettes.
    """
    assert BackgroundPalettes == list[list[tuple[int, int, int]]]
    assert callable(build_background_palettes_from_palette_ram)


def test_build_background_palettes_requires_16_bytes():
    """
    Objective:
    This helper expects only the background palette RAM area $3F00-$3F0F.
    """
    with pytest.raises(ValueError, match="Background palette RAM must be 16 bytes"):
        build_background_palettes_from_palette_ram(bytes([0x00] * 15))


def test_build_background_palettes_returns_four_palettes_with_four_colors_each():
    """
    Objective:
    Convert 16 background palette RAM bytes into 4 RGB background palettes.
    """
    background_palettes = build_background_palettes_from_palette_ram(
        make_background_palette_ram()
    )

    assert len(background_palettes) == 4
    assert all(len(palette) == 4 for palette in background_palettes)


def test_all_background_palettes_share_backdrop_color_as_entry_zero():
    """
    Objective:
    For background rendering, color index 0 uses the shared backdrop color from
    palette RAM entry $3F00.
    """
    palette_ram = make_background_palette_ram()
    background_palettes = build_background_palettes_from_palette_ram(palette_ram)

    backdrop = get_nes_rgb_color(0x0F)

    assert background_palettes[0][0] == backdrop
    assert background_palettes[1][0] == backdrop
    assert background_palettes[2][0] == backdrop
    assert background_palettes[3][0] == backdrop


def test_palette_zero_uses_offsets_1_2_and_3_after_backdrop():
    """
    Objective:
    Background palette 0 uses $3F01-$3F03 for color indexes 1-3.
    """
    palette_ram = make_background_palette_ram()
    background_palettes = build_background_palettes_from_palette_ram(palette_ram)

    assert background_palettes[0] == [
        get_nes_rgb_color(0x0F),
        get_nes_rgb_color(0x01),
        get_nes_rgb_color(0x02),
        get_nes_rgb_color(0x03),
    ]


def test_palette_one_uses_offsets_5_6_and_7_after_backdrop():
    """
    Objective:
    Background palette 1 uses $3F05-$3F07 for color indexes 1-3. Offset $3F04 is
    not used as an independent background color-0 entry by this helper.
    """
    palette_ram = make_background_palette_ram()
    background_palettes = build_background_palettes_from_palette_ram(palette_ram)

    assert background_palettes[1] == [
        get_nes_rgb_color(0x0F),
        get_nes_rgb_color(0x11),
        get_nes_rgb_color(0x12),
        get_nes_rgb_color(0x13),
    ]


def test_palette_two_and_three_use_expected_palette_ram_offsets():
    """
    Objective:
    Background palettes 2 and 3 use offsets 9-11 and 13-15 respectively.
    """
    palette_ram = make_background_palette_ram()
    background_palettes = build_background_palettes_from_palette_ram(palette_ram)

    assert background_palettes[2] == [
        get_nes_rgb_color(0x0F),
        get_nes_rgb_color(0x21),
        get_nes_rgb_color(0x22),
        get_nes_rgb_color(0x23),
    ]
    assert background_palettes[3] == [
        get_nes_rgb_color(0x0F),
        get_nes_rgb_color(0x31),
        get_nes_rgb_color(0x32),
        get_nes_rgb_color(0x33),
    ]


def test_palette_ram_values_are_mapped_through_nes_rgb_lookup_with_masking():
    """
    Objective:
    Palette RAM stores NES color indexes. get_nes_rgb_color owns the $3F masking.

    Example:
        0x41 masks to 0x01.
    """
    palette_ram = bytes([
        0x40, 0x41, 0x42, 0x43,
        0x44, 0x45, 0x46, 0x47,
        0x48, 0x49, 0x4A, 0x4B,
        0x4C, 0x4D, 0x4E, 0x4F,
    ])

    background_palettes = build_background_palettes_from_palette_ram(palette_ram)

    assert background_palettes[0][0] == get_nes_rgb_color(0x00)
    assert background_palettes[0][1] == get_nes_rgb_color(0x01)
    assert background_palettes[3][3] == get_nes_rgb_color(0x0F)
