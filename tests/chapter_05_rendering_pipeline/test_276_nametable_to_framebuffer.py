"""
Render a simplified nametable background into framebuffer data.

Reference:
    https://www.nesdev.org/wiki/PPU_nametables

File to create:
    emulator/rendering/nametable_renderer.py

Why this step exists:
Pattern tables contain tile graphics, but they do not describe the background
layout. Nametables provide that layout.

What is a nametable?
A nametable is PPU memory that stores which background tile appears at each tile
cell on the screen.

Minimal example:

    nametable[0] = 5

This means:

    top-left 8x8 background cell uses pattern table tile #5

Important distinction:

    pattern table = tile graphics dictionary
    nametable     = tile layout/map
    palette       = colors used by tile pixels

Simplified rendering model for this step:

    nametable tile ID
        -> decoded_tiles[tile_id]
        -> tile pixel color index 0-3
        -> same shared 4-color palette[color_index]
        -> framebuffer pixel

Real NES nametable memory:

    960 bytes tile IDs
    64 bytes attribute table

This step intentionally uses only the 960 visible tile bytes and one shared
4-color palette for all tiles. Attribute-table palette selection is a later step.

Important simplification:
This first nametable renderer is a basic starting point. Every tile uses the same
4-color palette. Later tests add an attribute-aware renderer where different
screen regions can choose different background palettes.

Screen size from nametable geometry:

    32 tiles across * 8 pixels = 256 pixels
    30 tiles down   * 8 pixels = 240 pixels

Suggested implementation example:

    from emulator.ppu.chr_decoder import (
        CHR_TILE_HEIGHT,
        CHR_TILE_WIDTH,
        decode_pattern_table,
    )
    from emulator.rendering.framebuffer import Framebuffer, RGBColor

    NAMETABLE_ROWS = 30
    NAMETABLE_TILES_PER_ROW = 32
    NAMETABLE_SIZE = NAMETABLE_TILES_PER_ROW * NAMETABLE_ROWS

    BACKGROUND_WIDTH = NAMETABLE_TILES_PER_ROW * CHR_TILE_WIDTH
    BACKGROUND_HEIGHT = NAMETABLE_ROWS * CHR_TILE_HEIGHT


    def nametable_to_framebuffer(
        nametable_bytes: bytes,
        pattern_table_bytes: bytes,
        palette: list[RGBColor],
    ) -> Framebuffer:
        if len(nametable_bytes) != NAMETABLE_SIZE:
            raise ValueError("Nametable visible tile area must be 960 bytes")

        decoded_tiles = decode_pattern_table(pattern_table_bytes)

        framebuffer = Framebuffer(width=BACKGROUND_WIDTH, height=BACKGROUND_HEIGHT)

        for tile_y in range(NAMETABLE_ROWS):
            for tile_x in range(NAMETABLE_TILES_PER_ROW):
                nametable_index = tile_y * NAMETABLE_TILES_PER_ROW + tile_x
                tile_id = nametable_bytes[nametable_index]
                tile = decoded_tiles[tile_id]

                for row in range(CHR_TILE_HEIGHT):
                    for col in range(CHR_TILE_WIDTH):
                        # Basic starting point: every tile uses the same
                        # 4-color palette. A later renderer will use the
                        # attribute table to select different palettes.
                        color_index = tile[row][col]
                        rgb = palette[color_index]

                        pixel_x = tile_x * CHR_TILE_WIDTH + col
                        pixel_y = tile_y * CHR_TILE_HEIGHT + row
                        framebuffer.set_pixel(pixel_x, pixel_y, rgb)

        return framebuffer

Architecture rule:
Do not duplicate CHR decoding logic here. Reuse decode_pattern_table().

Out of scope:
    - attribute table decoding
    - per-tile palette selection
    - scrolling
    - nametable mirroring
    - reading directly from PPU bus
    - sprites
    - OAMDMA
    - pygame display
"""

from pathlib import Path

import pytest

from emulator.ppu.chr_decoder import PATTERN_TABLE_SIZE
from emulator.rendering.framebuffer import Framebuffer
from emulator.rendering.nametable_renderer import (
    BACKGROUND_HEIGHT,
    BACKGROUND_WIDTH,
    NAMETABLE_ROWS,
    NAMETABLE_SIZE,
    NAMETABLE_TILES_PER_ROW,
    nametable_to_framebuffer,
)


TEST_PALETTE = [
    (0, 0, 0),
    (10, 10, 10),
    (20, 20, 20),
    (30, 30, 30),
]


def make_empty_pattern_table() -> bytearray:
    """Create one synthetic 4096-byte pattern table."""
    return bytearray(PATTERN_TABLE_SIZE)


def make_empty_nametable() -> bytearray:
    """Create the visible 960-byte nametable tile-ID area."""
    return bytearray(NAMETABLE_SIZE)


def test_nametable_renderer_file_exists():
    """
    Objective:
    Keep nametable/background rendering separate from framebuffer storage and CHR
    decoding.
    """
    assert Path("emulator/rendering/nametable_renderer.py").exists()


def test_nametable_renderer_declares_geometry_constants():
    """
    Objective:
    Name the simplified visible nametable geometry.
    """
    assert NAMETABLE_TILES_PER_ROW == 32
    assert NAMETABLE_ROWS == 30
    assert NAMETABLE_SIZE == 960
    assert BACKGROUND_WIDTH == 256
    assert BACKGROUND_HEIGHT == 240


def test_nametable_to_framebuffer_function_exists():
    """
    Objective:
    Expose one pure helper for rendering a simplified background framebuffer.
    """
    assert callable(nametable_to_framebuffer)


def test_empty_nametable_and_empty_pattern_table_render_256_by_240_framebuffer():
    """
    Objective:
    A 32x30 tile layout renders to the NES visible background size: 256x240.
    """
    nametable = bytes(make_empty_nametable())
    pattern_table = bytes(make_empty_pattern_table())

    framebuffer = nametable_to_framebuffer(nametable, pattern_table, TEST_PALETTE)

    assert isinstance(framebuffer, Framebuffer)
    assert framebuffer.width == 256
    assert framebuffer.height == 240
    assert len(framebuffer.pixels) == 256 * 240


def test_empty_nametable_and_empty_pattern_table_use_palette_color_zero():
    """
    Objective:
    If every nametable byte is tile 0 and tile 0 is blank, every pixel should map
    to palette[0].
    """
    nametable = bytes(make_empty_nametable())
    pattern_table = bytes(make_empty_pattern_table())

    framebuffer = nametable_to_framebuffer(nametable, pattern_table, TEST_PALETTE)

    assert framebuffer.get_pixel(0, 0) == TEST_PALETTE[0]
    assert framebuffer.get_pixel(255, 239) == TEST_PALETTE[0]


def test_top_left_nametable_tile_id_selects_pattern_table_tile():
    """
    Objective:
    nametable[0] selects the pattern tile rendered at the top-left 8x8 pixel area.

    Example:
        nametable[0] = 1
        pattern tile #1 row 0 decodes to color index 3
        framebuffer pixels x=0..7, y=0 become palette[3]
    """
    nametable = make_empty_nametable()
    nametable[0] = 1

    pattern_table = make_empty_pattern_table()
    tile_1_offset = 16
    pattern_table[tile_1_offset + 0] = 0xFF
    pattern_table[tile_1_offset + 8] = 0xFF

    framebuffer = nametable_to_framebuffer(bytes(nametable), bytes(pattern_table), TEST_PALETTE)

    assert framebuffer.get_pixel(0, 0) == TEST_PALETTE[3]
    assert framebuffer.get_pixel(7, 0) == TEST_PALETTE[3]
    assert framebuffer.get_pixel(0, 1) == TEST_PALETTE[0]


def test_nametable_tile_at_x_one_starts_at_pixel_x_eight():
    """
    Objective:
    Tile coordinate (1, 0) starts at pixel x=8 because each tile is 8 pixels wide.
    """
    nametable = make_empty_nametable()
    nametable[1] = 2

    pattern_table = make_empty_pattern_table()
    tile_2_offset = 2 * 16
    pattern_table[tile_2_offset + 0] = 0xFF
    pattern_table[tile_2_offset + 8] = 0x00

    framebuffer = nametable_to_framebuffer(bytes(nametable), bytes(pattern_table), TEST_PALETTE)

    assert framebuffer.get_pixel(7, 0) == TEST_PALETTE[0]
    assert framebuffer.get_pixel(8, 0) == TEST_PALETTE[1]
    assert framebuffer.get_pixel(15, 0) == TEST_PALETTE[1]
    assert framebuffer.get_pixel(16, 0) == TEST_PALETTE[0]


def test_nametable_tile_on_second_row_starts_at_pixel_y_eight():
    """
    Objective:
    Tile coordinate (0, 1) starts at pixel y=8 because each tile is 8 pixels high.
    """
    nametable = make_empty_nametable()
    nametable[NAMETABLE_TILES_PER_ROW] = 3

    pattern_table = make_empty_pattern_table()
    tile_3_offset = 3 * 16
    pattern_table[tile_3_offset + 0] = 0x00
    pattern_table[tile_3_offset + 8] = 0xFF

    framebuffer = nametable_to_framebuffer(bytes(nametable), bytes(pattern_table), TEST_PALETTE)

    assert framebuffer.get_pixel(0, 7) == TEST_PALETTE[0]
    assert framebuffer.get_pixel(0, 8) == TEST_PALETTE[2]
    assert framebuffer.get_pixel(7, 8) == TEST_PALETTE[2]


def test_nametable_to_framebuffer_rejects_wrong_nametable_size():
    """
    Objective:
    The simplified renderer expects exactly 960 visible tile bytes.
    """
    pattern_table = bytes(make_empty_pattern_table())

    with pytest.raises(ValueError, match="Nametable visible tile area must be 960 bytes"):
        nametable_to_framebuffer(bytes([0x00] * 959), pattern_table, TEST_PALETTE)


def test_nametable_to_framebuffer_propagates_invalid_pattern_table_size_error():
    """
    Objective:
    Pattern table size validation remains owned by the CHR decoder.
    """
    nametable = bytes(make_empty_nametable())

    with pytest.raises(ValueError, match="Pattern table must be 4096 bytes"):
        nametable_to_framebuffer(nametable, bytes([0x00] * 16), TEST_PALETTE)
