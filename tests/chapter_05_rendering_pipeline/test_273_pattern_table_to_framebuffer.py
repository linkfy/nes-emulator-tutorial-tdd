"""
Render a pattern table debug grid into a framebuffer.

File to create:
    emulator/rendering/pattern_table_renderer.py

Why this step exists:
The emulator already has pure CHR helpers:

    decode_pattern_table(pattern_table_bytes)
        -> 256 decoded 8x8 tiles of color indexes

    build_pattern_table_debug_grid(decoded_tiles)
        -> 128x128 color-index debug grid

And the rendering pipeline now has:

    color_index_grid_to_framebuffer(grid, palette)
        -> RGB Framebuffer

This step composes those pieces into one pure helper:

    pattern_table bytes + RGB palette -> 128x128 Framebuffer

What is a pattern table debug framebuffer?
A pattern table contains 256 tiles. Each tile is 8x8 pixels. For debugging, we
arrange those tiles as:

    16 tiles across * 8 pixels = 128 pixels wide
    16 tiles down   * 8 pixels = 128 pixels high

Suggested implementation example:

    from emulator.ppu.chr_decoder import (
        build_pattern_table_debug_grid,
        decode_pattern_table,
    )
    from emulator.rendering.color_index_renderer import color_index_grid_to_framebuffer
    from emulator.rendering.framebuffer import Framebuffer, RGBColor


    def pattern_table_to_framebuffer(
        pattern_table_bytes: bytes,
        palette: list[RGBColor],
    ) -> Framebuffer:
        decoded_tiles = decode_pattern_table(pattern_table_bytes)
        grid = build_pattern_table_debug_grid(decoded_tiles)
        return color_index_grid_to_framebuffer(grid, palette)

Architecture rule:
This renderer should compose existing pure functions. Do not duplicate CHR decode
logic here.

Important fixture rule:
Use synthetic CHR bytes only. Do not use commercial ROM CHR data in this test.

Out of scope:
    - pygame display
    - writing image files
    - nametable rendering
    - palette RAM lookup
    - sprite rendering
"""

from pathlib import Path

import pytest

from emulator.ppu.chr_decoder import PATTERN_TABLE_SIZE
from emulator.rendering.framebuffer import Framebuffer
from emulator.rendering.pattern_table_renderer import pattern_table_to_framebuffer


def make_empty_pattern_table() -> bytearray:
    """Create one synthetic 4096-byte pattern table."""
    return bytearray(PATTERN_TABLE_SIZE)


def test_pattern_table_renderer_file_exists():
    """
    Objective:
    Keep pattern-table rendering separate from framebuffer storage and generic
    color-index conversion.
    """
    assert Path("emulator/rendering/pattern_table_renderer.py").exists()


def test_pattern_table_to_framebuffer_function_exists():
    """
    Objective:
    Expose one pure helper for CHR pattern-table debug rendering.
    """
    assert callable(pattern_table_to_framebuffer)


def test_empty_pattern_table_renders_128_by_128_framebuffer():
    """
    Objective:
    A full 4096-byte pattern table renders to the standard 128x128 debug grid.
    """
    pattern_table = bytes(make_empty_pattern_table())
    palette = [
        (0, 0, 0),
        (85, 85, 85),
        (170, 170, 170),
        (255, 255, 255),
    ]

    framebuffer = pattern_table_to_framebuffer(pattern_table, palette)

    assert isinstance(framebuffer, Framebuffer)
    assert framebuffer.width == 128
    assert framebuffer.height == 128
    assert len(framebuffer.pixels) == 128 * 128


def test_empty_pattern_table_uses_palette_color_zero_for_all_pixels():
    """
    Objective:
    If all CHR bitplanes are zero, every decoded pixel has color index 0, so the
    framebuffer should use palette[0] everywhere.
    """
    pattern_table = bytes(make_empty_pattern_table())
    palette = [
        (1, 2, 3),
        (85, 85, 85),
        (170, 170, 170),
        (255, 255, 255),
    ]

    framebuffer = pattern_table_to_framebuffer(pattern_table, palette)

    assert framebuffer.get_pixel(0, 0) == (1, 2, 3)
    assert framebuffer.get_pixel(127, 127) == (1, 2, 3)


def test_first_tile_pixels_map_chr_color_indexes_to_palette_rgb_values():
    """
    Objective:
    A synthetic first tile should decode into color indexes and then map through
    the supplied RGB palette.

    CHR tile encoding reminder:
        bytes 0-7   = low bitplane for rows 0-7
        bytes 8-15  = high bitplane for rows 0-7

    For row 0:
        low  = 0b01010101
        high = 0b00110011

    Decoded pixels from left to right:
        0, 1, 2, 3, 0, 1, 2, 3
    """
    pattern_table = make_empty_pattern_table()

    # First tile, row 0 only.
    pattern_table[0] = 0b0101_0101
    pattern_table[8] = 0b0011_0011

    palette = [
        (0, 0, 0),
        (10, 10, 10),
        (20, 20, 20),
        (30, 30, 30),
    ]

    framebuffer = pattern_table_to_framebuffer(bytes(pattern_table), palette)

    assert [framebuffer.get_pixel(x, 0) for x in range(8)] == [
        (0, 0, 0),
        (10, 10, 10),
        (20, 20, 20),
        (30, 30, 30),
        (0, 0, 0),
        (10, 10, 10),
        (20, 20, 20),
        (30, 30, 30),
    ]


def test_second_tile_appears_eight_pixels_to_the_right_in_debug_framebuffer():
    """
    Objective:
    The pattern-table debug grid preserves the existing 16-tiles-per-row layout.

    Tile 0 starts at x=0.
    Tile 1 starts at x=8.
    """
    pattern_table = make_empty_pattern_table()

    # Tile 1 starts at byte offset 16. Set row 0 to all color index 3.
    tile_1_offset = 16
    pattern_table[tile_1_offset + 0] = 0xFF
    pattern_table[tile_1_offset + 8] = 0xFF

    palette = [
        (0, 0, 0),
        (10, 10, 10),
        (20, 20, 20),
        (30, 30, 30),
    ]

    framebuffer = pattern_table_to_framebuffer(bytes(pattern_table), palette)

    assert framebuffer.get_pixel(0, 0) == (0, 0, 0)
    assert framebuffer.get_pixel(7, 0) == (0, 0, 0)
    assert framebuffer.get_pixel(8, 0) == (30, 30, 30)
    assert framebuffer.get_pixel(15, 0) == (30, 30, 30)


def test_pattern_table_to_framebuffer_rejects_wrong_pattern_table_size():
    """
    Objective:
    Invalid pattern-table size should be rejected by the underlying CHR decoder.
    """
    palette = [
        (0, 0, 0),
        (10, 10, 10),
        (20, 20, 20),
        (30, 30, 30),
    ]

    with pytest.raises(ValueError, match="Pattern table must be 4096 bytes"):
        pattern_table_to_framebuffer(bytes([0x00] * 16), palette)
