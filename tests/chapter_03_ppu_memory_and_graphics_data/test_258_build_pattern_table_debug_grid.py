"""
Implement a pattern table debug grid.

Reference:
    https://www.nesdev.org/wiki/PPU_pattern_tables

File to update:
    emulator/ppu/chr_decoder.py

Function to implement:
    build_pattern_table_debug_grid(decoded_tiles: PatternTable) -> PatternTableDebugGrid

Constants to add:
    PATTERN_TABLE_TILES_PER_ROW = 16
    CHR_TILE_WIDTH = 8
    CHR_TILE_HEIGHT = 8
    PATTERN_TABLE_DEBUG_GRID_SIZE = 128

What this step does:
Previous tests decoded one pattern table into 256 separate 8x8 tiles. This step
arranges those tiles into one 128x128 grid of color indexes.

Layout:

    16 tiles across
    16 tiles down
    each tile is 8x8 pixels
    16 * 8 = 128 pixels

Examples:

    tile 0   -> top-left,     x=0,   y=0
    tile 1   -> right of it,  x=8,   y=0
    tile 16  -> next row,     x=0,   y=8
    tile 255 -> bottom-right, x=120, y=120

Suggested implementation example:

    def build_pattern_table_debug_grid(decoded_tiles: PatternTable) -> PatternTableDebugGrid:
        if len(decoded_tiles) != PATTERN_TABLE_TILE_COUNT:
            raise ValueError("Pattern table debug grid requires 256 decoded tiles")

        grid = [
            [0 for _ in range(PATTERN_TABLE_DEBUG_GRID_SIZE)]
            for _ in range(PATTERN_TABLE_DEBUG_GRID_SIZE)
        ]

        for tile_index, tile in enumerate(decoded_tiles):
            tile_x = (tile_index % PATTERN_TABLE_TILES_PER_ROW) * CHR_TILE_WIDTH
            tile_y = (tile_index // PATTERN_TABLE_TILES_PER_ROW) * CHR_TILE_HEIGHT

            for row in range(CHR_TILE_HEIGHT):
                for col in range(CHR_TILE_WIDTH):
                    grid[tile_y + row][tile_x + col] = tile[row][col]

        return grid

Synthetic data note:
This test uses a tiny synthetic pattern table generated inside the test file.

Out of scope:
    - file generation
    - image output
    - RGB/NES palette colors
    - nametable background rendering
    - PPU timing
"""

import pytest

from emulator.ppu.chr_decoder import (
    CHR_TILE_HEIGHT,
    CHR_TILE_SIZE,
    CHR_TILE_WIDTH,
    PATTERN_TABLE_DEBUG_GRID_SIZE,
    PATTERN_TABLE_SIZE,
    PATTERN_TABLE_TILE_COUNT,
    PATTERN_TABLE_TILES_PER_ROW,
    build_pattern_table_debug_grid,
    decode_pattern_table,
)


def blank_tile():
    """Create one decoded 8x8 tile filled with zero color indexes."""
    return [[0 for _ in range(CHR_TILE_WIDTH)] for _ in range(CHR_TILE_HEIGHT)]


def solid_tile(value: int):
    """Create one decoded 8x8 tile filled with one color index."""
    return [[value for _ in range(CHR_TILE_WIDTH)] for _ in range(CHR_TILE_HEIGHT)]


def make_decoded_tiles_with_tile(tile_index: int, tile):
    """Create 256 decoded tiles, replacing one tile at tile_index."""
    tiles = [blank_tile() for _ in range(PATTERN_TABLE_TILE_COUNT)]
    tiles[tile_index] = tile
    return tiles


def make_synthetic_pattern_table_bytes() -> bytes:
    """Create one deterministic 4096-byte pattern table with a few known tiles."""
    pattern_table = bytearray(PATTERN_TABLE_SIZE)

    # Tile 0 starts at byte 0. Row 0 decodes to:
    # low=1100_0011, high=1010_0101 -> [3, 1, 2, 0, 0, 2, 1, 3]
    pattern_table[0] = 0b1100_0011
    pattern_table[8] = 0b1010_0101

    # Tile 1 starts at byte 16. Row 0 decodes to:
    # low=0000_1111, high=0000_0000 -> [0, 0, 0, 0, 1, 1, 1, 1]
    tile_1_start = CHR_TILE_SIZE
    pattern_table[tile_1_start] = 0b0000_1111

    # Tile 16 starts the second tile row in the debug grid. Row 0 decodes to all 2s.
    tile_16_start = 16 * CHR_TILE_SIZE
    pattern_table[tile_16_start + 8] = 0b1111_1111

    return bytes(pattern_table)


def test_pattern_table_debug_grid_declares_layout_constants():
    """
    Objective:
    Name the debug grid layout: 16x16 tiles, each tile 8x8 pixels, total 128x128.
    """
    assert PATTERN_TABLE_TILES_PER_ROW == 16
    assert CHR_TILE_WIDTH == 8
    assert CHR_TILE_HEIGHT == 8
    assert PATTERN_TABLE_DEBUG_GRID_SIZE == 128


def test_build_pattern_table_debug_grid_rejects_non_256_tile_input():
    """
    Objective:
    A pattern table debug grid requires exactly 256 decoded tiles.
    """
    with pytest.raises(ValueError, match="256 decoded tiles"):
        build_pattern_table_debug_grid([blank_tile()] * (PATTERN_TABLE_TILE_COUNT - 1))


def test_build_pattern_table_debug_grid_returns_128_by_128_grid():
    """
    Objective:
    The debug grid should be 128 rows by 128 columns.
    """
    grid = build_pattern_table_debug_grid([blank_tile() for _ in range(PATTERN_TABLE_TILE_COUNT)])

    assert len(grid) == PATTERN_TABLE_DEBUG_GRID_SIZE
    assert all(len(row) == PATTERN_TABLE_DEBUG_GRID_SIZE for row in grid)


def test_tile_0_is_placed_at_top_left_of_debug_grid():
    """
    Objective:
    Tile 0 should occupy pixels x=0..7 and y=0..7.
    """
    tiles = make_decoded_tiles_with_tile(0, solid_tile(1))

    grid = build_pattern_table_debug_grid(tiles)

    assert grid[0][0:8] == [1] * 8
    assert grid[7][0:8] == [1] * 8
    assert grid[0][8] == 0


def test_tile_1_is_placed_to_the_right_of_tile_0():
    """
    Objective:
    Tile 1 should start at x=8, y=0.
    """
    tiles = make_decoded_tiles_with_tile(1, solid_tile(2))

    grid = build_pattern_table_debug_grid(tiles)

    assert grid[0][0:8] == [0] * 8
    assert grid[0][8:16] == [2] * 8


def test_tile_16_is_placed_at_start_of_second_tile_row():
    """
    Objective:
    Tile 16 should start the second tile row at x=0, y=8.
    """
    tiles = make_decoded_tiles_with_tile(16, solid_tile(3))

    grid = build_pattern_table_debug_grid(tiles)

    assert grid[0][0:8] == [0] * 8
    assert grid[8][0:8] == [3] * 8


def test_tile_255_is_placed_at_bottom_right_of_debug_grid():
    """
    Objective:
    Tile 255 should occupy the bottom-right 8x8 area.
    """
    tiles = make_decoded_tiles_with_tile(255, solid_tile(1))

    grid = build_pattern_table_debug_grid(tiles)

    assert grid[120][120:128] == [1] * 8
    assert grid[127][120:128] == [1] * 8
    assert grid[119][120] == 0


def test_synthetic_pattern_table_decodes_into_expected_debug_grid_pixels():
    """
    Objective:
    Use deterministic synthetic bytes to verify the complete path:

        bytes -> decoded tiles -> 128x128 debug grid

    This avoids depending on copyrighted CHR data from a commercial ROM.
    """
    pattern_table_bytes = make_synthetic_pattern_table_bytes()

    assert len(pattern_table_bytes) == PATTERN_TABLE_SIZE
    assert len(pattern_table_bytes) == PATTERN_TABLE_TILE_COUNT * CHR_TILE_SIZE

    decoded_tiles = decode_pattern_table(pattern_table_bytes)
    grid = build_pattern_table_debug_grid(decoded_tiles)

    # Tile 0, row 0: low=1100_0011 high=1010_0101.
    assert grid[0][0:8] == [3, 1, 2, 0, 0, 2, 1, 3]

    # Tile 1 starts at x=8. Its first row has low=0000_1111 high=0000_0000.
    assert grid[0][8:16] == [0, 0, 0, 0, 1, 1, 1, 1]

    # Tile 16 starts at x=0, y=8. Its first row is all color index 2.
    assert grid[8][0:8] == [2, 2, 2, 2, 2, 2, 2, 2]
