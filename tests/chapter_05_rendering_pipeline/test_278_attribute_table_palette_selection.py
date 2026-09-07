"""
Decode background palette selection from a nametable attribute table.

Reference:
    https://www.nesdev.org/wiki/PPU_attribute_tables

File to create:
    emulator/rendering/attribute_table.py

Why this step exists:
The current nametable renderer uses one shared 4-color palette for every tile.
Real NES backgrounds choose between four background sub-palettes using the
nametable's attribute table.

This step does not render with attributes yet. It only answers one small question:

    For tile coordinate (tile_x, tile_y), which palette ID does the attribute
    table select?

What is an attribute table?
Each nametable has:

    960 bytes tile IDs
    64 bytes attribute table

The attribute table is an 8x8 byte grid. Each attribute byte covers a 4x4 tile
area, which is 32x32 pixels.

One attribute byte is split into four 2x2 tile quadrants:

    +-----------------------+
    | top-left | top-right  |
    |  2x2     |   2x2      |
    +----------+------------+
    | bottom-l | bottom-r   |
    |  2x2     |   2x2      |
    +-----------------------+

Each quadrant stores a 2-bit palette ID:

    0b00 -> palette 0
    0b01 -> palette 1
    0b10 -> palette 2
    0b11 -> palette 3

Important distinction:
The attribute table does not store RGB colors and does not store NES color indexes.
It selects which background sub-palette to use. Later, palette RAM and the NES RGB
palette will turn that selection into actual colors.

Bit layout inside one attribute byte:

    bits 0-1 -> top-left quadrant
    bits 2-3 -> top-right quadrant
    bits 4-5 -> bottom-left quadrant
    bits 6-7 -> bottom-right quadrant

This step implements: unpack/read one quadrant from the byte.

Readable implementation example:

    TABLE_SIZE = 64
    BYTES_PER_ROW = 8


    def get_attribute_palette_id(
        attribute_table: bytes,
        tile_x: int,
        tile_y: int,
    ) -> int:
        if len(attribute_table) != TABLE_SIZE:
            raise ValueError("Attribute table must be 64 bytes")

        attribute_x = tile_x // 4
        attribute_y = tile_y // 4
        attribute_index = attribute_y * BYTES_PER_ROW + attribute_x
        attribute_byte = attribute_table[attribute_index]

        quadrant_x = (tile_x % 4) // 2
        quadrant_y = (tile_y % 4) // 2

        is_top_left = quadrant_x == 0 and quadrant_y == 0
        is_top_right = quadrant_x == 1 and quadrant_y == 0
        is_bottom_left = quadrant_x == 0 and quadrant_y == 1

        if is_top_left:
            return attribute_byte & 0b11

        if is_top_right:
            return (attribute_byte >> 2) & 0b11

        if is_bottom_left:
            return (attribute_byte >> 4) & 0b11

        return (attribute_byte >> 6) & 0b11

Why tile_x // 4 and tile_y // 4?
Because each attribute byte covers 4x4 tiles.

Why (tile_x % 4) // 2?
Inside that 4x4 area:

    tile positions 0,1 belong to quadrant 0
    tile positions 2,3 belong to quadrant 1

So:

    0 % 4 // 2 -> 0
    1 % 4 // 2 -> 0
    2 % 4 // 2 -> 1
    3 % 4 // 2 -> 1

Out of scope:
    - rendering nametables with attributes
    - PPU palette RAM lookup
    - RGB palette conversion
    - scrolling
    - sprites
    - pygame display
"""

from pathlib import Path

import pytest

from emulator.rendering.attribute_table import (
    BYTES_PER_ROW,
    TABLE_SIZE,
    get_attribute_palette_id,
)


def pack_attribute_byte(
    topleft: int,
    topright: int,
    bottomleft: int,
    bottomright: int,
) -> int:
    """
    Pack four 2-bit palette IDs into one attribute byte.

    This helper mirrors the documentation formula and makes the test examples
    easier to read.
    """
    return (
        (bottomright << 6)
        | (bottomleft << 4)
        | (topright << 2)
        | (topleft << 0)
    )


def make_attribute_table() -> bytearray:
    """Create a blank 64-byte attribute table."""
    return bytearray(TABLE_SIZE)


def test_attribute_table_file_exists():
    """
    Objective:
    Keep attribute-table bit decoding separate from nametable rendering.
    """
    assert Path("emulator/rendering/attribute_table.py").exists()


def test_attribute_table_declares_size_constants():
    """
    Objective:
    Name the visible nametable attribute-table geometry.
    """
    assert TABLE_SIZE == 64
    assert BYTES_PER_ROW == 8


def test_get_attribute_palette_id_function_exists():
    """
    Objective:
    Expose one helper for asking which background palette a tile coordinate uses.
    """
    assert callable(get_attribute_palette_id)


def test_all_zero_attribute_table_selects_palette_zero_everywhere():
    """
    Objective:
    If all attribute bytes are zero, every quadrant selects palette ID 0.
    """
    attribute_table = bytes(make_attribute_table())

    assert get_attribute_palette_id(attribute_table, tile_x=0, tile_y=0) == 0
    assert get_attribute_palette_id(attribute_table, tile_x=3, tile_y=3) == 0
    assert get_attribute_palette_id(attribute_table, tile_x=31, tile_y=29) == 0


def test_top_left_quadrant_reads_bits_zero_and_one():
    """
    Objective:
    Tiles in the top-left 2x2 quadrant read bits 0-1 of the attribute byte.

    Example byte:
        top-left = 1
        other quadrants = 0

        binary: 0b00_00_00_01
    """
    attribute_table = make_attribute_table()
    attribute_table[0] = pack_attribute_byte(
        topleft=1,
        topright=0,
        bottomleft=0,
        bottomright=0,
    )

    assert get_attribute_palette_id(bytes(attribute_table), 0, 0) == 1
    assert get_attribute_palette_id(bytes(attribute_table), 1, 0) == 1
    assert get_attribute_palette_id(bytes(attribute_table), 0, 1) == 1
    assert get_attribute_palette_id(bytes(attribute_table), 1, 1) == 1


def test_top_right_quadrant_reads_bits_two_and_three():
    """
    Objective:
    Tiles in the top-right 2x2 quadrant read bits 2-3 of the attribute byte.

    Example byte:
        top-right = 2
        binary contribution: 0b00_00_10_00
    """
    attribute_table = make_attribute_table()
    attribute_table[0] = pack_attribute_byte(
        topleft=0,
        topright=2,
        bottomleft=0,
        bottomright=0,
    )

    assert get_attribute_palette_id(bytes(attribute_table), 2, 0) == 2
    assert get_attribute_palette_id(bytes(attribute_table), 3, 0) == 2
    assert get_attribute_palette_id(bytes(attribute_table), 2, 1) == 2
    assert get_attribute_palette_id(bytes(attribute_table), 3, 1) == 2


def test_bottom_left_quadrant_reads_bits_four_and_five():
    """
    Objective:
    Tiles in the bottom-left 2x2 quadrant read bits 4-5 of the attribute byte.

    This protects against a common bug: accidentally treating bottom-left like
    top-left or bottom-right.
    """
    attribute_table = make_attribute_table()
    attribute_table[0] = pack_attribute_byte(
        topleft=0,
        topright=0,
        bottomleft=3,
        bottomright=0,
    )

    assert get_attribute_palette_id(bytes(attribute_table), 0, 2) == 3
    assert get_attribute_palette_id(bytes(attribute_table), 1, 2) == 3
    assert get_attribute_palette_id(bytes(attribute_table), 0, 3) == 3
    assert get_attribute_palette_id(bytes(attribute_table), 1, 3) == 3


def test_bottom_right_quadrant_reads_bits_six_and_seven():
    """
    Objective:
    Tiles in the bottom-right 2x2 quadrant read bits 6-7 of the attribute byte.
    """
    attribute_table = make_attribute_table()
    attribute_table[0] = pack_attribute_byte(
        topleft=0,
        topright=0,
        bottomleft=0,
        bottomright=2,
    )

    assert get_attribute_palette_id(bytes(attribute_table), 2, 2) == 2
    assert get_attribute_palette_id(bytes(attribute_table), 3, 2) == 2
    assert get_attribute_palette_id(bytes(attribute_table), 2, 3) == 2
    assert get_attribute_palette_id(bytes(attribute_table), 3, 3) == 2


def test_one_attribute_byte_can_store_four_different_palette_ids():
    """
    Objective:
    One attribute byte can select four different palette IDs for its four 2x2 tile
    quadrants.

    Packed example:
        top-left     = 0
        top-right    = 1
        bottom-left  = 2
        bottom-right = 3

    Byte layout:
        0b11_10_01_00
    """
    attribute_table = make_attribute_table()
    attribute_table[0] = pack_attribute_byte(
        topleft=0,
        topright=1,
        bottomleft=2,
        bottomright=3,
    )

    assert attribute_table[0] == 0b11_10_01_00
    assert get_attribute_palette_id(bytes(attribute_table), 0, 0) == 0
    assert get_attribute_palette_id(bytes(attribute_table), 2, 0) == 1
    assert get_attribute_palette_id(bytes(attribute_table), 0, 2) == 2
    assert get_attribute_palette_id(bytes(attribute_table), 2, 2) == 3


def test_neighboring_attribute_byte_starts_at_tile_x_four():
    """
    Objective:
    Since each attribute byte covers 4 tiles horizontally, tile_x=4 uses the next
    attribute byte in the same attribute-table row.
    """
    attribute_table = make_attribute_table()
    attribute_table[0] = pack_attribute_byte(0, 0, 0, 0)
    attribute_table[1] = pack_attribute_byte(2, 0, 0, 0)

    assert get_attribute_palette_id(bytes(attribute_table), 0, 0) == 0
    assert get_attribute_palette_id(bytes(attribute_table), 4, 0) == 2
    assert get_attribute_palette_id(bytes(attribute_table), 5, 1) == 2


def test_next_attribute_table_row_starts_at_tile_y_four():
    """
    Objective:
    Since each attribute byte covers 4 tiles vertically, tile_y=4 uses the next
    attribute-table row.
    """
    attribute_table = make_attribute_table()
    attribute_table[0] = pack_attribute_byte(0, 0, 0, 0)
    attribute_table[BYTES_PER_ROW] = pack_attribute_byte(3, 0, 0, 0)

    assert get_attribute_palette_id(bytes(attribute_table), 0, 0) == 0
    assert get_attribute_palette_id(bytes(attribute_table), 0, 4) == 3
    assert get_attribute_palette_id(bytes(attribute_table), 1, 5) == 3


def test_attribute_table_must_be_64_bytes():
    """
    Objective:
    Attribute table decoding expects the 64-byte attribute area, not the full
    1024-byte nametable page and not the 960-byte tile-ID area.
    """
    with pytest.raises(ValueError, match="Attribute table must be 64 bytes"):
        get_attribute_palette_id(bytes([0x00] * 63), tile_x=0, tile_y=0)
