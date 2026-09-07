"""
Implement full pattern table decoding.

Reference:
    https://www.nesdev.org/wiki/PPU_pattern_tables

File to update:
    emulator/ppu/chr_decoder.py

Function to implement:
    decode_pattern_table(pattern_table_bytes: bytes) -> PatternTable

Constants to add:
    PATTERN_TABLE_SIZE = 0x1000
    CHR_TILE_SIZE = 16
    PATTERN_TABLE_TILE_COUNT = 256

What is a pattern table?
A pattern table is a block of CHR graphics data containing 256 tiles.

Basic math:

    one CHR tile      = 16 bytes
    one pattern table = 4096 bytes = $1000
    4096 / 16         = 256 tiles

The NES PPU has two pattern table address ranges:

    $0000-$0FFF -> pattern table 0
    $1000-$1FFF -> pattern table 1

This step only decodes one 4096-byte pattern table into 256 already-decoded
tiles. It does not draw an image yet.

Suggested implementation example:

    PATTERN_TABLE_SIZE = 0x1000
    CHR_TILE_SIZE = 16
    PATTERN_TABLE_TILE_COUNT = 256

    PatternTile = list[list[int]]
    PatternTable = list[PatternTile]

    def decode_pattern_table(pattern_table_bytes: bytes) -> PatternTable:
        if len(pattern_table_bytes) != PATTERN_TABLE_SIZE:
            raise ValueError("Pattern table must be 4096 bytes")

        tiles = []

        for tile_index in range(PATTERN_TABLE_TILE_COUNT):
            start = tile_index * CHR_TILE_SIZE
            end = start + CHR_TILE_SIZE
            tiles.append(decode_chr_tile(pattern_table_bytes[start:end]))

        return tiles

Out of scope:
    - arranging tiles into a 128x128 debug grid
    - PNG/image output
    - RGB/NES palette colors
    - nametable background rendering
    - PPU timing
"""

import pytest

from emulator.ppu.chr_decoder import (
    CHR_TILE_SIZE,
    PATTERN_TABLE_SIZE,
    PATTERN_TABLE_TILE_COUNT,
    decode_pattern_table,
)


def make_pattern_table_with_tile(tile_index: int, tile_bytes: bytes) -> bytes:
    """Create one pattern table with one custom 16-byte tile at tile_index."""
    assert len(tile_bytes) == CHR_TILE_SIZE

    data = bytearray(PATTERN_TABLE_SIZE)
    start = tile_index * CHR_TILE_SIZE
    data[start : start + CHR_TILE_SIZE] = tile_bytes
    return bytes(data)


def test_pattern_table_decoder_declares_size_constants():
    """
    Objective:
    Name the sizes used by pattern table decoding.
    """
    assert PATTERN_TABLE_SIZE == 0x1000
    assert CHR_TILE_SIZE == 16
    assert PATTERN_TABLE_TILE_COUNT == 256


def test_decode_pattern_table_rejects_input_that_is_not_4096_bytes():
    """
    Objective:
    A single pattern table must be exactly 4096 bytes.
    """
    with pytest.raises(ValueError, match="4096 bytes"):
        decode_pattern_table(bytes([0x00] * (PATTERN_TABLE_SIZE - 1)))


def test_decode_pattern_table_returns_256_tiles():
    """
    Objective:
    4096 bytes should decode into exactly 256 tiles.
    """
    tiles = decode_pattern_table(bytes([0x00] * PATTERN_TABLE_SIZE))

    assert len(tiles) == PATTERN_TABLE_TILE_COUNT


def test_each_decoded_pattern_table_tile_is_8_by_8():
    """
    Objective:
    Each decoded tile keeps the same shape as decode_chr_tile: 8 rows x 8 columns.
    """
    tiles = decode_pattern_table(bytes([0x00] * PATTERN_TABLE_SIZE))

    first_tile = tiles[0]

    assert len(first_tile) == 8
    assert all(len(row) == 8 for row in first_tile)


def test_first_pattern_table_tile_uses_bytes_0_to_15():
    """
    Objective:
    Tile 0 should be decoded from pattern table bytes 0-15.
    """
    tile = bytearray(16)
    tile[0] = 0b1000_0000

    pattern_table = make_pattern_table_with_tile(0, bytes(tile))
    tiles = decode_pattern_table(pattern_table)

    assert tiles[0][0] == [1, 0, 0, 0, 0, 0, 0, 0]
    assert tiles[1] == [[0] * 8 for _ in range(8)]


def test_second_pattern_table_tile_uses_bytes_16_to_31():
    """
    Objective:
    Tile 1 should start at byte offset 16.
    """
    tile = bytearray(16)
    tile[8] = 0b1000_0000

    pattern_table = make_pattern_table_with_tile(1, bytes(tile))
    tiles = decode_pattern_table(pattern_table)

    assert tiles[0] == [[0] * 8 for _ in range(8)]
    assert tiles[1][0] == [2, 0, 0, 0, 0, 0, 0, 0]


def test_last_pattern_table_tile_uses_final_16_bytes():
    """
    Objective:
    Tile 255 should be decoded from the final 16 bytes, offsets 4080-4095.
    """
    tile = bytearray(16)
    tile[0] = 0b1000_0000
    tile[8] = 0b1000_0000

    pattern_table = make_pattern_table_with_tile(255, bytes(tile))
    tiles = decode_pattern_table(pattern_table)

    assert tiles[254] == [[0] * 8 for _ in range(8)]
    assert tiles[255][0] == [3, 0, 0, 0, 0, 0, 0, 0]
