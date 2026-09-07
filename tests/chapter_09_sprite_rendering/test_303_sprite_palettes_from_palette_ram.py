"""
Build sprite palettes from PPU palette RAM bytes.

File to update:
    emulator/rendering/palette_ram.py

Why this step exists:
Before rendering sprite pixels, we need to convert sprite palette RAM bytes into
RGB palettes. Sprite palette RAM lives in the PPU palette address range:

    $3F10-$3F1F

This helper receives those 16 bytes and returns four RGB sprite palettes.

References:
    https://www.nesdev.org/wiki/PPU_palettes#Palette_RAM

Important terminology:

    CHR color index
        The 2-bit pixel value decoded from CHR tile data: 0, 1, 2, or 3.

    PPU palette RAM byte
        A runtime NES color index, usually $00-$3F.

    RGB color
        The emulator's display color tuple from NES_PALETTE_RGB.

Sprite palette shape:

    palette 0 uses bytes 0, 1, 2, 3
    palette 1 uses bytes 4, 5, 6, 7
    palette 2 uses bytes 8, 9, 10, 11
    palette 3 uses bytes 12, 13, 14, 15

Suggested implementation example:

    SpritePalettes = list[list[RGBColor]]


    def build_sprite_palettes_from_palette_ram(palette_ram: bytes) -> SpritePalettes:
        if len(palette_ram) != PALETTE_RAM_SIZE:
            raise ValueError(f"Sprite palette RAM must be {PALETTE_RAM_SIZE} bytes")

        sprite_palettes = []

        for palette_id in range(TOTAL_PALETTES):
            base = palette_id * COLORS_PER_PALETTE

            palette = [
                get_nes_rgb_color(palette_ram[base]),
                get_nes_rgb_color(palette_ram[base + 1]),
                get_nes_rgb_color(palette_ram[base + 2]),
                get_nes_rgb_color(palette_ram[base + 3]),
            ]

            sprite_palettes.append(palette)

        return sprite_palettes

Important sprite transparency rule:
Sprite CHR color index 0 is transparent during rendering. This helper does not
apply transparency. It only converts palette RAM bytes to RGB colors. The later
sprite renderer will decide:

    if sprite_color_index == 0:
        skip drawing this pixel

Common misconception:

    "Sprite palette entry 0 should be removed from the palette helper."

No. Keep four entries. The renderer needs stable indexing 0..3, even though index
0 means transparent when drawing sprite pixels.

Out of scope:
    - rendering sprite pixels
    - applying transparency
    - sprite priority
    - sprite flipping
    - sprite 0 hit
    - sprite overflow
    - pygame
"""

from pathlib import Path

import pytest

from emulator.rendering.nes_palette import get_nes_rgb_color
from emulator.rendering.palette_ram import (
    COLORS_PER_PALETTE,
    PALETTE_RAM_SIZE,
    TOTAL_PALETTES,
    build_background_palettes_from_palette_ram,
    build_sprite_palettes_from_palette_ram,
)


def test_build_sprite_palettes_requires_exactly_16_bytes():
    """
    Objective:
    Sprite palette RAM input is the 16-byte range $3F10-$3F1F.
    """
    with pytest.raises(ValueError, match="Sprite palette RAM must be 16 bytes"):
        build_sprite_palettes_from_palette_ram(bytes([0x00] * 15))

    with pytest.raises(ValueError, match="Sprite palette RAM must be 16 bytes"):
        build_sprite_palettes_from_palette_ram(bytes([0x00] * 17))


def test_build_sprite_palettes_returns_four_palettes_with_four_colors_each():
    """
    Objective:
    The helper returns four sprite palettes, each with four RGB colors.
    """
    palette_ram = bytes(range(PALETTE_RAM_SIZE))

    palettes = build_sprite_palettes_from_palette_ram(palette_ram)

    assert len(palettes) == TOTAL_PALETTES

    for palette in palettes:
        assert len(palette) == COLORS_PER_PALETTE
        for color in palette:
            assert isinstance(color, tuple)
            assert len(color) == 3


def test_build_sprite_palettes_groups_bytes_into_palette_zero():
    """
    Objective:
    Sprite palette 0 uses input bytes 0..3.
    """
    palette_ram = bytes(range(16))

    palettes = build_sprite_palettes_from_palette_ram(palette_ram)

    assert palettes[0] == [
        get_nes_rgb_color(0),
        get_nes_rgb_color(1),
        get_nes_rgb_color(2),
        get_nes_rgb_color(3),
    ]


def test_build_sprite_palettes_groups_all_four_palettes():
    """
    Objective:
    Each palette uses its own four-byte group.
    """
    palette_ram = bytes(range(16))

    palettes = build_sprite_palettes_from_palette_ram(palette_ram)

    assert palettes[1] == [
        get_nes_rgb_color(4),
        get_nes_rgb_color(5),
        get_nes_rgb_color(6),
        get_nes_rgb_color(7),
    ]
    assert palettes[2] == [
        get_nes_rgb_color(8),
        get_nes_rgb_color(9),
        get_nes_rgb_color(10),
        get_nes_rgb_color(11),
    ]
    assert palettes[3] == [
        get_nes_rgb_color(12),
        get_nes_rgb_color(13),
        get_nes_rgb_color(14),
        get_nes_rgb_color(15),
    ]


def test_sprite_palette_helper_keeps_entry_zero_for_later_transparency_decision():
    """
    Objective:
    Sprite palette entry 0 remains present. Transparency is applied later by the
    sprite renderer when CHR color index 0 is encountered.
    """
    palette_ram = bytes([0x21, 0x22, 0x23, 0x24] + [0x00] * 12)

    palettes = build_sprite_palettes_from_palette_ram(palette_ram)

    assert palettes[0][0] == get_nes_rgb_color(0x21)
    assert len(palettes[0]) == 4


def test_sprite_palettes_are_different_from_background_shared_backdrop_rule():
    """
    Objective:
    Background palettes use a shared backdrop color from byte 0. Sprite palettes
    keep their own grouped entry 0 values for stable indexing, even though sprite
    color index 0 is transparent during rendering.
    """
    palette_ram = bytes(
        [
            0x01, 0x02, 0x03, 0x04,
            0x11, 0x12, 0x13, 0x14,
            0x21, 0x22, 0x23, 0x24,
            0x31, 0x32, 0x33, 0x34,
        ]
    )

    background_palettes = build_background_palettes_from_palette_ram(palette_ram)
    sprite_palettes = build_sprite_palettes_from_palette_ram(palette_ram)

    assert background_palettes[1][0] == get_nes_rgb_color(0x01)
    assert sprite_palettes[1][0] == get_nes_rgb_color(0x11)


def test_sprite_palette_helper_accepts_bytearray_input_at_runtime():
    """
    Objective:
    PPU memory is mutable, so the helper should work with bytearray as well as
    bytes at runtime.
    """
    palette_ram = bytearray(range(16))

    palettes = build_sprite_palettes_from_palette_ram(palette_ram)

    assert palettes[3][3] == get_nes_rgb_color(15)


def test_sprite_palette_helper_does_not_import_pygame_or_render_sprites():
    """
    Objective:
    Palette construction is pure data conversion, not frontend or sprite drawing.
    """
    source = Path("emulator/rendering/palette_ram.py").read_text()

    assert "import pygame" not in source
    assert "draw_sprite" not in source
    assert "render_sprite" not in source
