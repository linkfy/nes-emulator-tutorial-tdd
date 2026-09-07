"""
Implement a CHR tile decoder.

Reference:
    https://www.nesdev.org/wiki/PPU_pattern_tables

File to create:
    emulator/ppu/chr_decoder.py

Function to implement:
    decode_chr_tile(tile_bytes: bytes) -> list[list[int]]

What is a CHR tile?
A CHR tile is one 8x8 graphics tile stored as 16 bytes.

It does not store final RGB colors. It stores 2-bit color indexes:

    0, 1, 2, or 3

Those indexes will later be combined with palette RAM to choose actual NES
colors.

CHR tile byte layout:

    bytes 0-7   -> low bitplane, one byte per row
    bytes 8-15  -> high bitplane, one byte per row

For each row:

    low_byte  = tile_bytes[row]
    high_byte = tile_bytes[row + 8]

For each column, read bits from left to right:

    column 0 -> bit 7
    column 1 -> bit 6
    ...
    column 7 -> bit 0

Suggested implementation example:

    def decode_chr_tile(tile_bytes: bytes) -> list[list[int]]:
        if len(tile_bytes) != 16:
            raise ValueError("To decode CHR tile, tile must be 16 bytes")

        rows = []

        for row in range(8):
            low_byte = tile_bytes[row]
            high_byte = tile_bytes[row + 8]
            columns = []

            for col in range(8):
                bit_position = 7 - col

                low = (low_byte >> bit_position) & 1
                high = (high_byte >> bit_position) & 1

                pixel = (high << 1) | low
                columns.append(pixel)

            rows.append(columns)

        return rows

Out of scope:
    - pattern table rendering
    - RGB/NES palette colors
    - nametable background rendering
    - sprite rendering
    - PPU timing
"""

import pytest

from emulator.ppu.chr_decoder import decode_chr_tile


def test_decode_chr_tile_rejects_input_that_is_not_16_bytes():
    """
    Objective:
    A single NES CHR tile must be exactly 16 bytes.
    """
    with pytest.raises(ValueError, match="16 bytes"):
        decode_chr_tile(bytes([0x00] * 15))


def test_decode_all_zero_tile_to_8_by_8_grid_of_zero_indexes():
    """
    Objective:
    If both bitplanes are zero, every pixel color index is 0.
    """
    pixels = decode_chr_tile(bytes([0x00] * 16))

    assert pixels == [[0] * 8 for _ in range(8)]


def test_low_bitplane_sets_color_index_1():
    """
    Objective:
    A bit set only in the low plane produces color index 1.

    Example:
        low row byte  = 1000_0000
        high row byte = 0000_0000
        first pixel   = 1
    """
    tile = bytearray(16)
    tile[0] = 0b1000_0000

    pixels = decode_chr_tile(bytes(tile))

    assert pixels[0] == [1, 0, 0, 0, 0, 0, 0, 0]


def test_high_bitplane_sets_color_index_2():
    """
    Objective:
    A bit set only in the high plane produces color index 2.
    """
    tile = bytearray(16)
    tile[8] = 0b1000_0000

    pixels = decode_chr_tile(bytes(tile))

    assert pixels[0] == [2, 0, 0, 0, 0, 0, 0, 0]


def test_both_bitplanes_set_color_index_3():
    """
    Objective:
    A bit set in both planes produces color index 3.
    """
    tile = bytearray(16)
    tile[0] = 0b1000_0000
    tile[8] = 0b1000_0000

    pixels = decode_chr_tile(bytes(tile))

    assert pixels[0] == [3, 0, 0, 0, 0, 0, 0, 0]


def test_decode_reads_row_bits_left_to_right_from_bit_7_to_bit_0():
    """
    Objective:
    CHR bits are decoded left-to-right from bit 7 to bit 0.

    This prevents horizontally flipped tiles.
    """
    tile = bytearray(16)
    tile[0] = 0b1010_0101

    pixels = decode_chr_tile(bytes(tile))

    assert pixels[0] == [1, 0, 1, 0, 0, 1, 0, 1]


def test_decode_combines_low_and_high_planes_across_a_full_row():
    """
    Objective:
    Each pixel is built from the matching low-plane and high-plane bit.
    """
    tile = bytearray(16)
    tile[0] = 0b1100_0011
    tile[8] = 0b1010_0101

    pixels = decode_chr_tile(bytes(tile))

    assert pixels[0] == [3, 1, 2, 0, 0, 2, 1, 3]

