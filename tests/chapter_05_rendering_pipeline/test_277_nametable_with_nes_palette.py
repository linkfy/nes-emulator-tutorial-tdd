"""
Render a nametable framebuffer using the default NES RGB palette.

File to update:
    emulator/rendering/nametable_renderer.py

Why this step exists:
The generic nametable renderer supports custom palettes:

    nametable_to_framebuffer(nametable_bytes, pattern_table_bytes, palette)

That is useful for tests and debug palettes. Now that we have NES_PALETTE_RGB, we
add a default-palette helper:

    nametable_to_nes_framebuffer(nametable_bytes, pattern_table_bytes)

This mirrors the pattern-table helper from the previous rendering step.

What it should do:

    nametable_to_nes_framebuffer(nametable_bytes, pattern_table_bytes)
        -> nametable_to_framebuffer(
               nametable_bytes,
               pattern_table_bytes,
               NES_PALETTE_RGB,
           )

Suggested implementation example:

    from emulator.rendering.nes_palette import NES_PALETTE_RGB


    def nametable_to_nes_framebuffer(
        nametable_bytes: bytes,
        pattern_table_bytes: bytes,
    ) -> Framebuffer:
        return nametable_to_framebuffer(
            nametable_bytes,
            pattern_table_bytes,
            NES_PALETTE_RGB,
        )

Important simplification:
This still uses one shared palette for every tile. It does not decode the 64-byte
attribute table yet, and it does not read PPU palette RAM at $3F00-$3F1F yet.
This is useful as a debug/simple renderer. A later renderer will use the attribute
table to choose between different background palettes.

Important fixture rule:
Use synthetic nametable/CHR bytes only. Do not use commercial ROM data in this
test.

Out of scope:
    - attribute table palette selection
    - PPU palette RAM lookup
    - scrolling
    - sprites
    - OAMDMA
    - pygame display
"""

from emulator.ppu.chr_decoder import PATTERN_TABLE_SIZE
from emulator.rendering.framebuffer import Framebuffer
from emulator.rendering.nametable_renderer import (
    NAMETABLE_SIZE,
    nametable_to_framebuffer,
    nametable_to_nes_framebuffer,
)
from emulator.rendering.nes_palette import NES_PALETTE_RGB


def make_empty_pattern_table() -> bytearray:
    """Create one synthetic 4096-byte pattern table."""
    return bytearray(PATTERN_TABLE_SIZE)


def make_empty_nametable() -> bytearray:
    """Create the visible 960-byte nametable tile-ID area."""
    return bytearray(NAMETABLE_SIZE)


def test_nametable_to_nes_framebuffer_function_exists():
    """
    Objective:
    Expose an explicit helper for rendering simplified nametable output using the
    default NES RGB palette approximation.
    """
    assert callable(nametable_to_nes_framebuffer)


def test_nametable_to_nes_framebuffer_returns_256_by_240_framebuffer():
    """
    Objective:
    The default-palette helper keeps the standard visible NES background size.
    """
    nametable = bytes(make_empty_nametable())
    pattern_table = bytes(make_empty_pattern_table())

    framebuffer = nametable_to_nes_framebuffer(nametable, pattern_table)

    assert isinstance(framebuffer, Framebuffer)
    assert framebuffer.width == 256
    assert framebuffer.height == 240
    assert len(framebuffer.pixels) == 256 * 240


def test_empty_nametable_and_empty_pattern_table_use_nes_palette_color_zero():
    """
    Objective:
    Empty CHR bytes decode to color index 0. With the default helper, that index
    should map to NES_PALETTE_RGB[0].
    """
    nametable = bytes(make_empty_nametable())
    pattern_table = bytes(make_empty_pattern_table())

    framebuffer = nametable_to_nes_framebuffer(nametable, pattern_table)

    assert framebuffer.get_pixel(0, 0) == NES_PALETTE_RGB[0]
    assert framebuffer.get_pixel(255, 239) == NES_PALETTE_RGB[0]


def test_synthetic_top_left_tile_color_index_three_uses_nes_palette_color_three():
    """
    Objective:
    A nametable tile that decodes to color index 3 should become NES_PALETTE_RGB[3]
    in the framebuffer.

    Setup:
        nametable[0] = 1, so tile #1 appears at the top-left background cell.

        tile #1 row 0:
            low bitplane  = 0xFF
            high bitplane = 0xFF

        Each pixel on row 0 decodes to binary 11, color index 3.
    """
    nametable = make_empty_nametable()
    nametable[0] = 1

    pattern_table = make_empty_pattern_table()
    tile_1_offset = 16
    pattern_table[tile_1_offset + 0] = 0xFF
    pattern_table[tile_1_offset + 8] = 0xFF

    framebuffer = nametable_to_nes_framebuffer(bytes(nametable), bytes(pattern_table))

    assert framebuffer.get_pixel(0, 0) == NES_PALETTE_RGB[3]
    assert framebuffer.get_pixel(7, 0) == NES_PALETTE_RGB[3]
    assert framebuffer.get_pixel(0, 1) == NES_PALETTE_RGB[0]


def test_nes_palette_helper_matches_generic_renderer_with_nes_palette():
    """
    Objective:
    nametable_to_nes_framebuffer is a convenience wrapper, not a separate rendering
    algorithm.

    It should produce the same framebuffer as:
        nametable_to_framebuffer(nametable, pattern_table, NES_PALETTE_RGB)
    """
    nametable = make_empty_nametable()
    nametable[1] = 2

    pattern_table = make_empty_pattern_table()
    tile_2_offset = 2 * 16
    pattern_table[tile_2_offset + 0] = 0b0101_0101
    pattern_table[tile_2_offset + 8] = 0b0011_0011

    generic = nametable_to_framebuffer(
        bytes(nametable),
        bytes(pattern_table),
        NES_PALETTE_RGB,
    )
    default_nes = nametable_to_nes_framebuffer(bytes(nametable), bytes(pattern_table))

    assert default_nes.width == generic.width
    assert default_nes.height == generic.height
    assert default_nes.pixels == generic.pixels
