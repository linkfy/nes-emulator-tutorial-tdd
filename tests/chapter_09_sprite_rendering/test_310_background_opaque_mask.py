"""
Build a background opacity mask from nametable and pattern table data.

File to update:
    emulator/rendering/nametable_renderer.py

Why this step exists:
Sprites have a priority bit that can place them behind non-transparent background
pixels. To implement that correctly, the compositor needs to know whether each
background pixel is opaque.

RGB framebuffer data alone is not enough because once a background pixel is
converted to RGB, we lose the original CHR color index.

This step adds a pure mask:

    BackgroundOpaqueMask = list[bool]

Where:

    False -> background CHR color index was 0
    True  -> background CHR color index was 1, 2, or 3

Suggested implementation example:

    BackgroundOpaqueMask = list[bool]


    def build_background_opaque_mask(
        pattern_table: bytes,
        nametable: bytes,
    ) -> BackgroundOpaqueMask:
        if len(nametable) != NAMETABLE_SIZE:
            raise ValueError("Nametable must be 960 bytes")

        decoded_tiles = decode_pattern_table(pattern_table)

        opaque_mask: BackgroundOpaqueMask = [False] * (
            BACKGROUND_WIDTH * BACKGROUND_HEIGHT
        )

        for tile_y in range(NAMETABLE_ROWS):
            for tile_x in range(NAMETABLE_TILES_PER_ROW):
                tile_index = nametable[tile_y * NAMETABLE_TILES_PER_ROW + tile_x]
                tile = decoded_tiles[tile_index]

                for pixel_y in range(CHR_TILE_HEIGHT):
                    for pixel_x in range(CHR_TILE_WIDTH):
                        color_index = tile[pixel_y][pixel_x]

                        screen_x = tile_x * CHR_TILE_WIDTH + pixel_x
                        screen_y = tile_y * CHR_TILE_HEIGHT + pixel_y

                        mask_index = screen_y * BACKGROUND_WIDTH + screen_x
                        opaque_mask[mask_index] = color_index != 0

        return opaque_mask

Why no attribute table or palette RAM?
Opacity depends only on the CHR color index. Attribute table and palette RAM decide
which colors are displayed, but they do not change whether a background pixel's CHR
color index is zero or nonzero.

Out of scope:
    - applying sprite priority
    - changing the framebuffer compositor
    - sprite rendering
    - sprite 0 hit
    - sprite overflow
    - pygame
"""

from pathlib import Path

import pytest

from emulator.rendering.nametable_renderer import (
    BACKGROUND_HEIGHT,
    BACKGROUND_WIDTH,
    NAMETABLE_SIZE,
    BackgroundOpaqueMask,
    build_background_opaque_mask,
)
from tests.chapter_09_sprite_rendering.test_304_render_one_sprite_8x8 import encode_chr_tile


def make_pattern_table_with_tiles(*tiles: bytes) -> bytes:
    """Build a 4096-byte pattern table with provided tiles at the front."""
    pattern_table = bytearray(0x1000)

    for tile_index, tile in enumerate(tiles):
        start = tile_index * 16
        pattern_table[start:start + 16] = tile

    return bytes(pattern_table)


def make_tile_with_pixel(x: int, y: int, color_index: int) -> bytes:
    """Create one CHR tile with a single configured pixel."""
    grid = [[0 for _ in range(8)] for _ in range(8)]
    grid[y][x] = color_index
    return encode_chr_tile(grid)


def test_background_opaque_mask_type_alias_is_list_of_bool_runtime_shape():
    """
    Objective:
    BackgroundOpaqueMask is intentionally a simple list[bool], not a dataclass.
    """
    mask: BackgroundOpaqueMask = [False, True]

    assert mask == [False, True]


def test_build_background_opaque_mask_has_one_entry_per_screen_pixel():
    """
    Objective:
    The mask is per pixel, not per tile.
    """
    pattern_table = make_pattern_table_with_tiles(make_tile_with_pixel(0, 0, 0))
    nametable = bytes([0] * NAMETABLE_SIZE)

    mask = build_background_opaque_mask(pattern_table, nametable)

    assert len(mask) == BACKGROUND_WIDTH * BACKGROUND_HEIGHT
    assert len(mask) == 256 * 240


def test_background_color_index_zero_is_not_opaque():
    """
    Objective:
    CHR color index 0 represents background transparency/backdrop for priority
    decisions, so the mask entry should be False.
    """
    pattern_table = make_pattern_table_with_tiles(make_tile_with_pixel(0, 0, 0))
    nametable = bytes([0] * NAMETABLE_SIZE)

    mask = build_background_opaque_mask(pattern_table, nametable)

    assert mask[0] is False



def test_background_color_indexes_one_two_three_are_opaque():
    """
    Objective:
    CHR color indexes 1, 2, and 3 are non-transparent background pixels.
    """
    tile_1 = make_tile_with_pixel(0, 0, 1)
    tile_2 = make_tile_with_pixel(0, 0, 2)
    tile_3 = make_tile_with_pixel(0, 0, 3)
    pattern_table = make_pattern_table_with_tiles(tile_1, tile_2, tile_3)

    for tile_index in [0, 1, 2]:
        nametable = bytes([tile_index] + [0] * (NAMETABLE_SIZE - 1))
        mask = build_background_opaque_mask(pattern_table, nametable)

        assert mask[0] is True


def test_background_opaque_mask_maps_tile_pixel_to_screen_pixel():
    """
    Objective:
    The mask index uses screen coordinates:

        mask_index = screen_y * BACKGROUND_WIDTH + screen_x
    """
    tile = make_tile_with_pixel(x=3, y=4, color_index=1)
    pattern_table = make_pattern_table_with_tiles(tile)
    nametable = bytes([0] * NAMETABLE_SIZE)

    mask = build_background_opaque_mask(pattern_table, nametable)

    expected_index = 4 * BACKGROUND_WIDTH + 3

    assert mask[expected_index] is True


def test_background_opaque_mask_maps_later_nametable_tile_to_correct_screen_area():
    """
    Objective:
    Nametable tile coordinates use 32 tiles per row and each tile covers 8x8 pixels.
    """
    tile = make_tile_with_pixel(x=2, y=1, color_index=1)
    pattern_table = make_pattern_table_with_tiles(tile)

    nametable = bytearray([0] * NAMETABLE_SIZE)
    tile_x = 5
    tile_y = 7
    nametable[tile_y * 32 + tile_x] = 0

    mask = build_background_opaque_mask(pattern_table, bytes(nametable))

    screen_x = tile_x * 8 + 2
    screen_y = tile_y * 8 + 1
    expected_index = screen_y * BACKGROUND_WIDTH + screen_x

    assert mask[expected_index] is True


def test_build_background_opaque_mask_rejects_short_nametable():
    """
    Objective:
    The helper expects the 960 visible tile bytes of one nametable.
    """
    pattern_table = make_pattern_table_with_tiles(make_tile_with_pixel(0, 0, 1))

    with pytest.raises(ValueError, match="Nametable must be 960 bytes"):
        build_background_opaque_mask(pattern_table, bytes([0] * (NAMETABLE_SIZE - 1)))


def test_background_opaque_mask_does_not_need_attribute_or_palette_data():
    """
    Objective:
    Opacity depends on CHR color index only, not palette selection.
    """
    source = Path("emulator/rendering/nametable_renderer.py").read_text()

    function_source = source[source.index("def build_background_opaque_mask") :]

    assert "attribute_table" not in function_source
    assert "palette_ram" not in function_source


def test_background_opaque_mask_does_not_import_pygame_or_sprite_renderer():
    """
    Objective:
    The mask is pure background-rendering data. It should not depend on pygame or
    sprite rendering.
    """
    source = Path("emulator/rendering/nametable_renderer.py").read_text()

    assert "import pygame" not in source
    assert "sprite_renderer" not in source
