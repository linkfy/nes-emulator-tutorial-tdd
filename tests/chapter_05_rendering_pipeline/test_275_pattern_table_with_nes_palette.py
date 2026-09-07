"""
Render a pattern table framebuffer using the default NES RGB palette.

File to update:
    emulator/rendering/pattern_table_renderer.py

Why this step exists:
The generic pattern table renderer already supports custom palettes:

    pattern_table_to_framebuffer(pattern_table_bytes, palette)

That is useful for tests and debug palettes. Now that we have a default NES RGB
palette approximation, we add a convenience helper:

    pattern_table_to_nes_framebuffer(pattern_table_bytes)

This helper keeps the default-palette path explicit without removing custom
palette support.

What it should do:

    pattern_table_to_nes_framebuffer(pattern_table_bytes)
        -> pattern_table_to_framebuffer(pattern_table_bytes, NES_PALETTE_RGB)

Suggested implementation example:

    from emulator.rendering.nes_palette import NES_PALETTE_RGB


    def pattern_table_to_nes_framebuffer(
        pattern_table_bytes: bytes,
    ) -> Framebuffer:
        return pattern_table_to_framebuffer(pattern_table_bytes, NES_PALETTE_RGB)

Why not make NES_PALETTE_RGB the default argument?
This would work:

    def pattern_table_to_framebuffer(pattern_table_bytes, palette=NES_PALETTE_RGB):
        ...

But a separate helper is clearer for the tutorial:

    pattern_table_to_framebuffer(..., palette)
        custom palette path

    pattern_table_to_nes_framebuffer(...)
        default NES palette path


Note: This test uses synthetic CHR bytes only. Do not use commercial ROM CHR data in this test.

Out of scope:
    - pygame display
    - writing image files
    - nametable/background rendering
    - PPU palette RAM lookup
    - PPUMASK emphasis colors
    - sprites
"""

from emulator.ppu.chr_decoder import PATTERN_TABLE_SIZE
from emulator.rendering.framebuffer import Framebuffer
from emulator.rendering.nes_palette import NES_PALETTE_RGB
from emulator.rendering.pattern_table_renderer import (
    pattern_table_to_framebuffer,
    pattern_table_to_nes_framebuffer,
)


def make_empty_pattern_table() -> bytearray:
    """Create one synthetic 4096-byte pattern table."""
    return bytearray(PATTERN_TABLE_SIZE)


def test_pattern_table_to_nes_framebuffer_function_exists():
    """
    Objective:
    Expose an explicit helper for rendering pattern-table debug output using the
    default NES RGB palette approximation.
    """
    assert callable(pattern_table_to_nes_framebuffer)


def test_pattern_table_to_nes_framebuffer_returns_128_by_128_framebuffer():
    """
    Objective:
    The default-palette helper keeps the same pattern-table debug dimensions.
    """
    pattern_table = bytes(make_empty_pattern_table())

    framebuffer = pattern_table_to_nes_framebuffer(pattern_table)

    assert isinstance(framebuffer, Framebuffer)
    assert framebuffer.width == 128
    assert framebuffer.height == 128
    assert len(framebuffer.pixels) == 128 * 128


def test_empty_pattern_table_uses_nes_palette_color_zero():
    """
    Objective:
    Empty CHR bytes decode to color index 0, so every framebuffer pixel should use
    NES_PALETTE_RGB[0].
    """
    pattern_table = bytes(make_empty_pattern_table())

    framebuffer = pattern_table_to_nes_framebuffer(pattern_table)

    assert framebuffer.get_pixel(0, 0) == NES_PALETTE_RGB[0]
    assert framebuffer.get_pixel(127, 127) == NES_PALETTE_RGB[0]


def test_synthetic_tile_color_index_three_uses_nes_palette_color_three():
    """
    Objective:
    A synthetic CHR tile that decodes to color index 3 should become
    NES_PALETTE_RGB[3] in the framebuffer.

    CHR tile encoding:
        low bitplane byte  = 0xFF
        high bitplane byte = 0xFF

    For each pixel:
        low bit  = 1
        high bit = 1
        color index = binary 11 = 3
    """
    pattern_table = make_empty_pattern_table()

    # First tile, row 0 only: all pixels become color index 3.
    pattern_table[0] = 0xFF
    pattern_table[8] = 0xFF

    framebuffer = pattern_table_to_nes_framebuffer(bytes(pattern_table))

    assert framebuffer.get_pixel(0, 0) == NES_PALETTE_RGB[3]
    assert framebuffer.get_pixel(7, 0) == NES_PALETTE_RGB[3]

    # Row 1 was left as zero bytes, so it still maps to color index 0.
    assert framebuffer.get_pixel(0, 1) == NES_PALETTE_RGB[0]


def test_nes_palette_helper_matches_generic_renderer_with_nes_palette():
    """
    Objective:
    pattern_table_to_nes_framebuffer is a convenience wrapper, not a separate
    rendering algorithm.

    It should produce the same pixels as:
        pattern_table_to_framebuffer(pattern_table, NES_PALETTE_RGB)
    """
    pattern_table = make_empty_pattern_table()

    # First tile, row 0: repeating 0, 1, 2, 3 pattern.
    pattern_table[0] = 0b0101_0101
    pattern_table[8] = 0b0011_0011

    generic = pattern_table_to_framebuffer(bytes(pattern_table), NES_PALETTE_RGB)
    default_nes = pattern_table_to_nes_framebuffer(bytes(pattern_table))

    assert default_nes.width == generic.width
    assert default_nes.height == generic.height
    assert default_nes.pixels == generic.pixels
