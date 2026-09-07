"""
Render one 8x8 sprite into framebuffer data.

File to update:
    emulator/rendering/sprite_renderer.py

Why this step exists:
The previous sprite steps decoded OAM entries, decoded sprite attributes, and built
sprite palettes. Now we draw one sprite into a pure Framebuffer.

This is the first sprite step that produces visible pixel data, but it is still
small and controlled:

    one SpriteEntry
    one CHR tile
    one selected sprite palette
    one Framebuffer target

Suggested implementation example:

    def render_sprite_8x8_to_framebuffer(
        framebuffer: Framebuffer,
        sprite: SpriteEntry,
        pattern_table: bytes,
        sprite_palettes: SpritePalettes,
    ) -> None:
        attributes = decode_sprite_attributes(sprite.attributes)

        tile_start = sprite.tile_index * 16
        tile_end = tile_start + 16

        if tile_end > len(pattern_table):
            raise ValueError("Pattern table does not contain sprite tile bytes")

        tile_bytes = pattern_table[tile_start:tile_end]
        color_indexes = decode_chr_tile(tile_bytes)
        palette = sprite_palettes[attributes.palette_id]

        for tile_y in range(8):
            for tile_x in range(8):
                color_index = color_indexes[tile_y][tile_x]

                if color_index == 0:
                    continue

                screen_x = sprite.x + tile_x
                screen_y = sprite.y + tile_y

                if not (0 <= screen_x < framebuffer.width):
                    continue
                if not (0 <= screen_y < framebuffer.height):
                    continue

                framebuffer.set_pixel(screen_x, screen_y, palette[color_index])

Important transparency rule:
For sprites, CHR color index 0 is transparent. It must not overwrite the existing
framebuffer pixel.

Important Y-position simplification:
Real NES sprite Y positioning has a hardware quirk where the stored OAM Y value is
not exactly the visible top scanline. This tutorial step uses raw sprite.y as the
screen Y position. More accurate timing/position behavior can come later.

Out of scope:
    - horizontal/vertical flip support
    - sprite priority behind background
    - rendering all 64 sprites
    - background/sprite compositing policy
    - sprite 0 hit
    - sprite overflow
    - pygame
"""

from pathlib import Path

import pytest

from emulator.rendering.framebuffer import BLACK, Framebuffer
from emulator.rendering.sprite_renderer import (
    SpriteEntry,
    render_sprite_8x8_to_framebuffer,
)


def encode_chr_tile(color_indexes: list[list[int]]) -> bytes:
    """
    Encode an 8x8 grid of CHR color indexes into one NES 16-byte tile.

    This is the inverse of decode_chr_tile() for synthetic test data:
        bytes 0..7  -> low bit plane
        bytes 8..15 -> high bit plane
    """
    low_plane: list[int] = []
    high_plane: list[int] = []

    for row in color_indexes:
        low_byte = 0
        high_byte = 0

        for x, color_index in enumerate(row):
            bit_position = 7 - x
            low_byte |= (color_index & 0b01) << bit_position
            high_byte |= ((color_index >> 1) & 0b01) << bit_position

        low_plane.append(low_byte)
        high_plane.append(high_byte)

    return bytes(low_plane + high_plane)


def make_sprite_palettes() -> list[list[tuple[int, int, int]]]:
    """Create four synthetic sprite palettes with easy-to-recognize RGB values."""
    return [
        [(0, 0, 0), (10, 0, 0), (20, 0, 0), (30, 0, 0)],
        [(0, 0, 0), (0, 10, 0), (0, 20, 0), (0, 30, 0)],
        [(0, 0, 0), (0, 0, 10), (0, 0, 20), (0, 0, 30)],
        [(0, 0, 0), (10, 10, 10), (20, 20, 20), (30, 30, 30)],
    ]


def test_render_sprite_8x8_draws_nonzero_pixels_to_framebuffer():
    """
    Objective:
    Nonzero CHR color indexes become RGB pixels in the target framebuffer.
    """
    tile = encode_chr_tile(
        [
            [1, 2, 3, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
        ]
    )
    framebuffer = Framebuffer(width=16, height=16)
    sprite = SpriteEntry(y=4, tile_index=0, attributes=0, x=5)

    render_sprite_8x8_to_framebuffer(framebuffer, sprite, tile, make_sprite_palettes())

    assert framebuffer.get_pixel(5, 4) == (10, 0, 0)
    assert framebuffer.get_pixel(6, 4) == (20, 0, 0)
    assert framebuffer.get_pixel(7, 4) == (30, 0, 0)


def test_render_sprite_8x8_treats_color_index_zero_as_transparent():
    """
    Objective:
    Sprite color index 0 must not overwrite the existing framebuffer pixel.
    """
    tile = encode_chr_tile([[0 for _ in range(8)] for _ in range(8)])
    framebuffer = Framebuffer(width=8, height=8)
    framebuffer.set_pixel(0, 0, (99, 88, 77))
    sprite = SpriteEntry(y=0, tile_index=0, attributes=0, x=0)

    render_sprite_8x8_to_framebuffer(framebuffer, sprite, tile, make_sprite_palettes())

    assert framebuffer.get_pixel(0, 0) == (99, 88, 77)


def test_render_sprite_8x8_uses_palette_id_from_sprite_attributes():
    """
    Objective:
    Attribute bits 0-1 select which sprite palette is used.
    """
    tile = encode_chr_tile(
        [
            [3, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
        ]
    )
    framebuffer = Framebuffer(width=8, height=8)
    sprite = SpriteEntry(y=0, tile_index=0, attributes=0b0000_0010, x=0)

    render_sprite_8x8_to_framebuffer(framebuffer, sprite, tile, make_sprite_palettes())

    assert framebuffer.get_pixel(0, 0) == (0, 0, 30)


def test_render_sprite_8x8_uses_sprite_x_and_y_as_screen_position():
    """
    Objective:
    SpriteEntry.x and SpriteEntry.y choose where tile pixel (0, 0) appears.
    """
    tile = encode_chr_tile(
        [
            [1, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
        ]
    )
    framebuffer = Framebuffer(width=16, height=16)
    sprite = SpriteEntry(y=6, tile_index=0, attributes=0, x=7)

    render_sprite_8x8_to_framebuffer(framebuffer, sprite, tile, make_sprite_palettes())

    assert framebuffer.get_pixel(7, 6) == (10, 0, 0)
    assert framebuffer.get_pixel(0, 0) == BLACK


def test_render_sprite_8x8_clips_pixels_outside_framebuffer():
    """
    Objective:
    Offscreen sprite pixels should be skipped instead of causing index errors.
    """
    tile = encode_chr_tile([[1 for _ in range(8)] for _ in range(8)])
    framebuffer = Framebuffer(width=4, height=4)
    sprite = SpriteEntry(y=2, tile_index=0, attributes=0, x=2)

    render_sprite_8x8_to_framebuffer(framebuffer, sprite, tile, make_sprite_palettes())

    assert framebuffer.get_pixel(2, 2) == (10, 0, 0)
    assert framebuffer.get_pixel(3, 2) == (10, 0, 0)
    assert framebuffer.get_pixel(2, 3) == (10, 0, 0)
    assert framebuffer.get_pixel(3, 3) == (10, 0, 0)


def test_render_sprite_8x8_uses_tile_index_to_select_pattern_table_tile():
    """
    Objective:
    SpriteEntry.tile_index selects which 16-byte tile to decode from the pattern
    table.
    """
    tile_0 = encode_chr_tile([[0 for _ in range(8)] for _ in range(8)])
    tile_1 = encode_chr_tile(
        [[2 if x == 0 and y == 0 else 0 for x in range(8)] for y in range(8)]
    )
    pattern_table = tile_0 + tile_1
    framebuffer = Framebuffer(width=8, height=8)
    sprite = SpriteEntry(y=0, tile_index=1, attributes=0, x=0)

    render_sprite_8x8_to_framebuffer(
        framebuffer,
        sprite,
        pattern_table,
        make_sprite_palettes(),
    )

    assert framebuffer.get_pixel(0, 0) == (20, 0, 0)


def test_render_sprite_8x8_raises_when_pattern_table_lacks_tile_bytes():
    """
    Objective:
    A clear error should be raised if tile_index points past available pattern data.
    """
    framebuffer = Framebuffer(width=8, height=8)
    sprite = SpriteEntry(y=0, tile_index=1, attributes=0, x=0)

    with pytest.raises(ValueError, match="Pattern table does not contain sprite tile bytes"):
        render_sprite_8x8_to_framebuffer(
            framebuffer,
            sprite,
            bytes([0x00] * 16),
            make_sprite_palettes(),
        )


def test_render_sprite_8x8_does_not_import_pygame_or_render_all_sprites():
    """
    Objective:
    This step renders one sprite into pure framebuffer data. It should not add
    frontend dependencies or all-sprite rendering yet.
    """
    source = Path("emulator/rendering/sprite_renderer.py").read_text()

    assert "import pygame" not in source
    assert "render_all" not in source
