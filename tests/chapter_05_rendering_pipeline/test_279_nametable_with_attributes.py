"""
Render nametable background using attribute-selected palettes.

Reference:
    https://www.nesdev.org/wiki/PPU_attribute_tables

File to update:
    emulator/rendering/nametable_renderer.py

Why this step exists:
The first nametable renderer used one shared 4-color palette for the entire
background. That was a useful starting point, but real NES backgrounds use the
attribute table to choose between four background palettes in different regions.

This step adds a new renderer instead of changing the old one:

    old/simple:
        nametable_to_framebuffer(nametable, pattern_table, palette)

    new/attribute-aware:
        nametable_with_attributes_to_framebuffer(
            nametable,
            attribute_table,
            pattern_table,
            background_palettes,
        )

What are background_palettes?
background_palettes is a list of four 4-color RGB palettes:

    background_palettes[0] -> palette ID 0
    background_palettes[1] -> palette ID 1
    background_palettes[2] -> palette ID 2
    background_palettes[3] -> palette ID 3

Each tile pixel still produces only a color index 0-3. The attribute table selects
which palette ID to use for the tile region:

    palette_id = get_attribute_palette_id(attribute_table, tile_x, tile_y)
    rgb = background_palettes[palette_id][color_index]

Important hardware model:
The attribute table does not store RGB colors. It selects a background palette ID.
For this step, we pass already-resolved RGB background palettes manually. Later,
another step can build those palettes from PPU palette RAM and NES_PALETTE_RGB.

Suggested implementation example:

    from emulator.rendering.attribute_table import get_attribute_palette_id

    BackgroundPalettes = list[list[RGBColor]]


    def nametable_with_attributes_to_framebuffer(
        nametable_bytes: bytes,
        attribute_table: bytes,
        pattern_table_bytes: bytes,
        background_palettes: BackgroundPalettes,
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

                palette_id = get_attribute_palette_id(attribute_table, tile_x, tile_y)
                palette = background_palettes[palette_id]

                for row in range(CHR_TILE_HEIGHT):
                    for col in range(CHR_TILE_WIDTH):
                        color_index = tile[row][col]
                        rgb = palette[color_index]

                        pixel_x = tile_x * CHR_TILE_WIDTH + col
                        pixel_y = tile_y * CHR_TILE_HEIGHT + row
                        framebuffer.set_pixel(pixel_x, pixel_y, rgb)

        return framebuffer

Compatibility rule:
Keep nametable_to_framebuffer(..., palette) unchanged. It remains the simple
one-palette renderer used by earlier tests.

Out of scope:
    - PPU palette RAM lookup
    - universal background color behavior
    - scrolling
    - sprites
    - OAMDMA
    - pygame display
"""

from emulator.ppu.chr_decoder import PATTERN_TABLE_SIZE
from emulator.rendering.attribute_table import TABLE_SIZE
from emulator.rendering.framebuffer import Framebuffer
from emulator.rendering.nametable_renderer import (
    BackgroundPalettes,
    NAMETABLE_SIZE,
    nametable_to_framebuffer,
    nametable_with_attributes_to_framebuffer,
)


SHARED_PALETTE = [
    (0, 0, 0),
    (10, 10, 10),
    (20, 20, 20),
    (30, 30, 30),
]


BACKGROUND_PALETTES: BackgroundPalettes = [
    [(0, 0, 0), (10, 0, 0), (20, 0, 0), (30, 0, 0)],
    [(0, 0, 0), (0, 10, 0), (0, 20, 0), (0, 30, 0)],
    [(0, 0, 0), (0, 0, 10), (0, 0, 20), (0, 0, 30)],
    [(0, 0, 0), (10, 10, 10), (20, 20, 20), (30, 30, 30)],
]


def pack_attribute_byte(
    topleft: int,
    topright: int,
    bottomleft: int,
    bottomright: int,
) -> int:
    """Pack four 2-bit palette IDs using the NES attribute byte layout."""
    return (
        (bottomright << 6)
        | (bottomleft << 4)
        | (topright << 2)
        | (topleft << 0)
    )


def make_empty_pattern_table() -> bytearray:
    """Create one synthetic 4096-byte pattern table."""
    return bytearray(PATTERN_TABLE_SIZE)


def make_empty_nametable() -> bytearray:
    """Create the visible 960-byte nametable tile-ID area."""
    return bytearray(NAMETABLE_SIZE)


def make_empty_attribute_table() -> bytearray:
    """Create one synthetic 64-byte attribute table."""
    return bytearray(TABLE_SIZE)


def set_tile_row_to_color_index(
    pattern_table: bytearray,
    tile_id: int,
    row: int,
    color_index: int,
) -> None:
    """
    Set one synthetic tile row to a constant CHR color index.

    color_index 0 -> low=0, high=0
    color_index 1 -> low=1, high=0
    color_index 2 -> low=0, high=1
    color_index 3 -> low=1, high=1
    """
    tile_offset = tile_id * 16
    low_bit = color_index & 0b01
    high_bit = (color_index >> 1) & 0b01

    pattern_table[tile_offset + row] = 0xFF if low_bit else 0x00
    pattern_table[tile_offset + 8 + row] = 0xFF if high_bit else 0x00


def test_nametable_with_attributes_to_framebuffer_function_exists():
    """
    Objective:
    Expose a new attribute-aware renderer without replacing the old simple one.
    """
    assert callable(nametable_with_attributes_to_framebuffer)


def test_background_palettes_type_alias_exists():
    """
    Objective:
    Name the input shape: four background palettes, each containing RGB colors.
    """
    assert BackgroundPalettes == list[list[tuple[int, int, int]]]


def test_attribute_aware_nametable_renderer_returns_256_by_240_framebuffer():
    """
    Objective:
    Attribute-aware rendering keeps the normal NES visible background dimensions.
    """
    nametable = bytes(make_empty_nametable())
    attribute_table = bytes(make_empty_attribute_table())
    pattern_table = bytes(make_empty_pattern_table())

    framebuffer = nametable_with_attributes_to_framebuffer(
        nametable,
        attribute_table,
        pattern_table,
        BACKGROUND_PALETTES,
    )

    assert isinstance(framebuffer, Framebuffer)
    assert framebuffer.width == 256
    assert framebuffer.height == 240


def test_top_left_attribute_quadrant_selects_background_palette_zero():
    """
    Objective:
    The top-left 2x2 tile quadrant uses bits 0-1 of the attribute byte.

    Here those bits select palette ID 0. Tile #1 emits color index 3, so the final
    RGB color should be BACKGROUND_PALETTES[0][3].
    """
    nametable = make_empty_nametable()
    nametable[0] = 1

    attribute_table = make_empty_attribute_table()
    attribute_table[0] = pack_attribute_byte(0, 1, 2, 3)

    pattern_table = make_empty_pattern_table()
    set_tile_row_to_color_index(pattern_table, tile_id=1, row=0, color_index=3)

    framebuffer = nametable_with_attributes_to_framebuffer(
        bytes(nametable),
        bytes(attribute_table),
        bytes(pattern_table),
        BACKGROUND_PALETTES,
    )

    assert framebuffer.get_pixel(0, 0) == BACKGROUND_PALETTES[0][3]


def test_top_right_attribute_quadrant_selects_background_palette_one():
    """
    Objective:
    Tile coordinate (2, 0) is in the top-right quadrant of the first attribute
    byte, so it should use palette ID 1 from bits 2-3.
    """
    nametable = make_empty_nametable()
    nametable[2] = 1

    attribute_table = make_empty_attribute_table()
    attribute_table[0] = pack_attribute_byte(0, 1, 2, 3)

    pattern_table = make_empty_pattern_table()
    set_tile_row_to_color_index(pattern_table, tile_id=1, row=0, color_index=3)

    framebuffer = nametable_with_attributes_to_framebuffer(
        bytes(nametable),
        bytes(attribute_table),
        bytes(pattern_table),
        BACKGROUND_PALETTES,
    )

    assert framebuffer.get_pixel(16, 0) == BACKGROUND_PALETTES[1][3]


def test_bottom_left_attribute_quadrant_selects_background_palette_two():
    """
    Objective:
    Tile coordinate (0, 2) is in the bottom-left quadrant of the first attribute
    byte, so it should use palette ID 2 from bits 4-5.
    """
    nametable = make_empty_nametable()
    nametable[2 * 32] = 1

    attribute_table = make_empty_attribute_table()
    attribute_table[0] = pack_attribute_byte(0, 1, 2, 3)

    pattern_table = make_empty_pattern_table()
    set_tile_row_to_color_index(pattern_table, tile_id=1, row=0, color_index=3)

    framebuffer = nametable_with_attributes_to_framebuffer(
        bytes(nametable),
        bytes(attribute_table),
        bytes(pattern_table),
        BACKGROUND_PALETTES,
    )

    assert framebuffer.get_pixel(0, 16) == BACKGROUND_PALETTES[2][3]


def test_bottom_right_attribute_quadrant_selects_background_palette_three():
    """
    Objective:
    Tile coordinate (2, 2) is in the bottom-right quadrant of the first attribute
    byte, so it should use palette ID 3 from bits 6-7.
    """
    nametable = make_empty_nametable()
    nametable[(2 * 32) + 2] = 1

    attribute_table = make_empty_attribute_table()
    attribute_table[0] = pack_attribute_byte(0, 1, 2, 3)

    pattern_table = make_empty_pattern_table()
    set_tile_row_to_color_index(pattern_table, tile_id=1, row=0, color_index=3)

    framebuffer = nametable_with_attributes_to_framebuffer(
        bytes(nametable),
        bytes(attribute_table),
        bytes(pattern_table),
        BACKGROUND_PALETTES,
    )

    assert framebuffer.get_pixel(16, 16) == BACKGROUND_PALETTES[3][3]


def test_old_simple_nametable_renderer_still_uses_one_shared_palette():
    """
    Objective:
    Adding the attribute-aware renderer must not change the old simple renderer.

    The old renderer ignores attribute tables entirely and maps every tile through
    the same supplied 4-color palette.
    """
    nametable = make_empty_nametable()
    nametable[0] = 1

    pattern_table = make_empty_pattern_table()
    set_tile_row_to_color_index(pattern_table, tile_id=1, row=0, color_index=3)

    framebuffer = nametable_to_framebuffer(
        bytes(nametable),
        bytes(pattern_table),
        SHARED_PALETTE,
    )

    assert framebuffer.get_pixel(0, 0) == SHARED_PALETTE[3]
