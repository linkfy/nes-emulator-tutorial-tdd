"""
Detect the first sprite 0/background opaque-pixel overlap.

File to create:
    emulator/rendering/sprite_zero_hit.py

Why this step exists:
Step 319 established when sprite 0 hit is cleared. Before setting PPUSTATUS bit 6,
we need a pure helper that answers:

    Does a non-transparent sprite 0 pixel overlap a non-transparent background pixel?
    If so, where is the first overlap?

Returning a position instead of only True/False gives the next timing step enough
information to decide when the PPU should set sprite 0 hit.

Definitions:

    Sprite pixel is opaque:
        its decoded CHR color index is 1, 2, or 3

    Background pixel is opaque:
        background_opaque_mask[y * screen_width + x] is True

    Sprite 0 overlap:
        both conditions are true at the same visible screen coordinate

Suggested implementation example:

    from emulator.ppu.chr_decoder import decode_chr_tile
    from emulator.rendering.framebuffer import NES_SCREEN_HEIGHT, NES_SCREEN_WIDTH
    from emulator.rendering.nametable_renderer import BackgroundOpaqueMask
    from emulator.rendering.sprite_renderer import (
        SpriteEntry,
        decode_sprite_attributes,
    )


    SpriteZeroHitPosition = tuple[int, int]


    def find_sprite_zero_hit_position(
        sprite_zero: SpriteEntry,
        pattern_table: bytes,
        background_opaque_mask: BackgroundOpaqueMask,
        screen_width: int = NES_SCREEN_WIDTH,
        screen_height: int = NES_SCREEN_HEIGHT,
    ) -> SpriteZeroHitPosition | None:
        if len(background_opaque_mask) != screen_width * screen_height:
            raise ValueError(
                "Background opaque mask size must be equal to screen width * height"
            )

        tile_start = sprite_zero.tile_index * 16
        tile_end = tile_start + 16

        if tile_end > len(pattern_table):
            raise ValueError("Pattern table does not contain sprite 0 tile bytes")

        attributes = decode_sprite_attributes(sprite_zero.attributes)
        color_indexes = decode_chr_tile(pattern_table[tile_start:tile_end])

        for tile_y in range(8):
            for tile_x in range(8):
                source_x = 7 - tile_x if attributes.flip_horizontal else tile_x
                source_y = 7 - tile_y if attributes.flip_vertical else tile_y

                sprite_color_index = color_indexes[source_y][source_x]

                if sprite_color_index == 0:
                    continue

                screen_x = sprite_zero.x + tile_x
                screen_y = sprite_zero.y + tile_y

                if not (0 <= screen_x < screen_width):
                    continue
                if not (0 <= screen_y < screen_height):
                    continue

                mask_index = screen_y * screen_width + screen_x

                if background_opaque_mask[mask_index]:
                    return screen_x, screen_y

        return None

Important coordinate simplification:
Real NES OAM stores the sprite top Y coordinate minus one, so the first sprite row
normally appears at OAM Y + 1. The existing tutorial sprite renderer currently uses
OAM Y directly. This helper intentionally matches that existing renderer so visible
sprite pixels and overlap coordinates remain consistent. A later focused accuracy
step should update both together.

Important rules:
    - sprite color index 0 never contributes to a hit
    - background mask False never contributes to a hit
    - sprite priority bit 5 does not prevent sprite 0 hit detection
    - clipping must happen before indexing the background mask
    - this helper must not mutate PPUSTATUS

Out of scope:
    - setting or clearing PPUSTATUS
    - scheduling the hit by scanline/cycle
    - exact OAM Y + 1 behavior
    - x=255 hardware exception
    - PPUMASK rendering-enable rules
    - 8x16 sprites
    - Super Mario Bros. validation
"""

import pytest

from emulator.rendering.framebuffer import NES_SCREEN_HEIGHT, NES_SCREEN_WIDTH
from emulator.rendering.sprite_renderer import (
    SPRITE_FLIP_HORIZONTAL,
    SPRITE_FLIP_VERTICAL,
    SPRITE_IS_BEHIND_BACKGROUND,
    SpriteEntry,
)
from emulator.rendering.sprite_zero_hit import (
    SpriteZeroHitPosition,
    find_sprite_zero_hit_position,
)
from tests.chapter_09_sprite_rendering.test_304_render_one_sprite_8x8 import encode_chr_tile


def make_pattern_table_with_tile(tile: bytes, tile_index: int = 0) -> bytes:
    """Build one 4096-byte pattern table containing a synthetic tile."""
    pattern_table = bytearray(0x1000)
    start = tile_index * 16
    pattern_table[start:start + 16] = tile
    return bytes(pattern_table)


def make_tile_with_pixels(*pixels: tuple[int, int, int]) -> bytes:
    """Create one CHR tile from (x, y, color_index) pixel descriptions."""
    grid = [[0 for _ in range(8)] for _ in range(8)]

    for x, y, color_index in pixels:
        grid[y][x] = color_index

    return encode_chr_tile(grid)


def make_mask(
    width: int,
    height: int,
    *opaque_positions: tuple[int, int],
) -> list[bool]:
    mask = [False] * (width * height)

    for x, y in opaque_positions:
        mask[y * width + x] = True

    return mask


def test_sprite_zero_hit_position_type_alias_has_coordinate_shape():
    """
    Objective:
    A hit position is a simple screen-coordinate tuple, not a PPU-mutating object.
    """
    position: SpriteZeroHitPosition = (12, 34)

    assert position == (12, 34)


def test_opaque_sprite_pixel_over_opaque_background_returns_screen_position():
    """
    Objective:
    A nonzero sprite pixel and a True background mask entry at the same coordinate
    produce a hit.
    """
    width = 16
    height = 16
    sprite = SpriteEntry(y=4, tile_index=0, attributes=0, x=5)
    tile = make_tile_with_pixels((2, 3, 1))
    pattern_table = make_pattern_table_with_tile(tile)
    mask = make_mask(width, height, (7, 7))

    result = find_sprite_zero_hit_position(
        sprite_zero=sprite,
        pattern_table=pattern_table,
        background_opaque_mask=mask,
        screen_width=width,
        screen_height=height,
    )

    assert result == (7, 7)


def test_transparent_sprite_pixel_does_not_produce_hit():
    """
    Objective:
    Sprite CHR color index 0 remains transparent even over opaque background.
    """
    width = 8
    height = 8
    sprite = SpriteEntry(y=0, tile_index=0, attributes=0, x=0)
    pattern_table = make_pattern_table_with_tile(make_tile_with_pixels())
    mask = make_mask(width, height, (0, 0))

    result = find_sprite_zero_hit_position(
        sprite,
        pattern_table,
        mask,
        width,
        height,
    )

    assert result is None


def test_opaque_sprite_pixel_over_transparent_background_does_not_produce_hit():
    """
    Objective:
    A visible sprite pixel alone is insufficient; the background must also be
    opaque at that coordinate.
    """
    width = 8
    height = 8
    sprite = SpriteEntry(y=0, tile_index=0, attributes=0, x=0)
    tile = make_tile_with_pixels((0, 0, 3))
    pattern_table = make_pattern_table_with_tile(tile)
    mask = make_mask(width, height)

    result = find_sprite_zero_hit_position(
        sprite,
        pattern_table,
        mask,
        width,
        height,
    )

    assert result is None


def test_helper_returns_first_overlap_in_scan_order():
    """
    Objective:
    Multiple overlaps should produce one deterministic earliest result in the
    helper's top-to-bottom, left-to-right scan order.
    """
    width = 8
    height = 8
    sprite = SpriteEntry(y=0, tile_index=0, attributes=0, x=0)
    tile = make_tile_with_pixels((5, 1, 1), (2, 0, 2), (1, 0, 3))
    pattern_table = make_pattern_table_with_tile(tile)
    mask = make_mask(width, height, (5, 1), (2, 0), (1, 0))

    result = find_sprite_zero_hit_position(
        sprite,
        pattern_table,
        mask,
        width,
        height,
    )

    assert result == (1, 0)


def test_horizontal_flip_changes_overlap_screen_position():
    """
    Objective:
    Sprite attribute horizontal flip changes where a source CHR pixel appears.
    """
    width = 8
    height = 8
    sprite = SpriteEntry(
        y=0,
        tile_index=0,
        attributes=SPRITE_FLIP_HORIZONTAL,
        x=0,
    )
    tile = make_tile_with_pixels((0, 2, 1))
    pattern_table = make_pattern_table_with_tile(tile)
    mask = make_mask(width, height, (7, 2))

    result = find_sprite_zero_hit_position(
        sprite,
        pattern_table,
        mask,
        width,
        height,
    )

    assert result == (7, 2)


def test_vertical_flip_changes_overlap_screen_position():
    """
    Objective:
    Sprite attribute vertical flip changes where a source CHR pixel appears.
    """
    width = 8
    height = 8
    sprite = SpriteEntry(
        y=0,
        tile_index=0,
        attributes=SPRITE_FLIP_VERTICAL,
        x=0,
    )
    tile = make_tile_with_pixels((3, 0, 1))
    pattern_table = make_pattern_table_with_tile(tile)
    mask = make_mask(width, height, (3, 7))

    result = find_sprite_zero_hit_position(
        sprite,
        pattern_table,
        mask,
        width,
        height,
    )

    assert result == (3, 7)


def test_sprite_priority_behind_background_does_not_prevent_hit():
    """
    Objective:
    Priority controls which RGB pixel is visible. It does not remove the underlying
    sprite/background opacity overlap used for sprite 0 hit.
    """
    width = 8
    height = 8
    sprite = SpriteEntry(
        y=0,
        tile_index=0,
        attributes=SPRITE_IS_BEHIND_BACKGROUND,
        x=0,
    )
    tile = make_tile_with_pixels((4, 5, 1))
    pattern_table = make_pattern_table_with_tile(tile)
    mask = make_mask(width, height, (4, 5))

    result = find_sprite_zero_hit_position(
        sprite,
        pattern_table,
        mask,
        width,
        height,
    )

    assert result == (4, 5)


def test_offscreen_sprite_pixels_are_skipped_before_mask_indexing():
    """
    Objective:
    Clipping should prevent an offscreen sprite pixel from indexing an unrelated or
    invalid mask entry.
    """
    width = 4
    height = 4
    sprite = SpriteEntry(y=3, tile_index=0, attributes=0, x=3)
    tile = make_tile_with_pixels((7, 7, 1))
    pattern_table = make_pattern_table_with_tile(tile)
    mask = make_mask(width, height)

    result = find_sprite_zero_hit_position(
        sprite,
        pattern_table,
        mask,
        width,
        height,
    )

    assert result is None


def test_invalid_background_mask_size_is_rejected():
    """
    Objective:
    Make the mask/frame coordinate invariant explicit instead of allowing obscure
    indexing failures.
    """
    sprite = SpriteEntry(y=0, tile_index=0, attributes=0, x=0)
    pattern_table = make_pattern_table_with_tile(
        make_tile_with_pixels((0, 0, 1))
    )

    with pytest.raises(ValueError):
        find_sprite_zero_hit_position(
            sprite,
            pattern_table,
            [False] * 63,
            screen_width=8,
            screen_height=8,
        )


def test_pattern_table_must_contain_sprite_zero_tile_bytes():
    """
    Objective:
    A sprite tile index must identify a complete 16-byte CHR tile.
    """
    sprite = SpriteEntry(y=0, tile_index=1, attributes=0, x=0)

    with pytest.raises(ValueError):
        find_sprite_zero_hit_position(
            sprite,
            pattern_table=bytes([0] * 16),
            background_opaque_mask=[False] * 64,
            screen_width=8,
            screen_height=8,
        )


def test_default_dimensions_match_visible_nes_screen():
    """
    Objective:
    Default helper dimensions should match the existing pure Framebuffer defaults.
    """
    sprite = SpriteEntry(y=0, tile_index=0, attributes=0, x=0)
    pattern_table = make_pattern_table_with_tile(make_tile_with_pixels())
    mask = [False] * (NES_SCREEN_WIDTH * NES_SCREEN_HEIGHT)

    result = find_sprite_zero_hit_position(
        sprite,
        pattern_table,
        mask,
    )

    assert result is None
