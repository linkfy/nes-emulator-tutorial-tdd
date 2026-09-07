"""
Add horizontal and vertical flip support to one-sprite rendering.

File to update:
    emulator/rendering/sprite_renderer.py

Why this step exists:
Sprite attributes already decode horizontal and vertical flip bits. The one-sprite
renderer should now use those bits when choosing which CHR pixel to draw.

Sprite attribute flip bits:

    bit 6: horizontal flip
    bit 7: vertical flip

Important model:
Flipping mirrors the image inside the sprite's 8x8 box. It does not move the
sprite's screen position.

Suggested implementation example inside render_sprite_8x8_to_framebuffer():

    for tile_y in range(8):
        for tile_x in range(8):
            source_x = 7 - tile_x if attributes.flip_horizontal else tile_x
            source_y = 7 - tile_y if attributes.flip_vertical else tile_y

            color_index = color_indexes[source_y][source_x]

            if color_index == 0:
                continue

            screen_x = sprite.x + tile_x
            screen_y = sprite.y + tile_y

            ...

Minimal example:

    original row:          1 2 3 . . . . .
    horizontal flip row:   . . . . . 3 2 1

Common misconception:

    "Horizontal flip should change sprite.x."

No. The destination box stays at sprite.x/sprite.y. Only the source pixel lookup is
mirrored.

Out of scope:
    - rendering all 64 sprites
    - sprite priority behind background
    - sprite 0 hit
    - sprite overflow
    - pygame
"""

from pathlib import Path

from emulator.rendering.framebuffer import BLACK, Framebuffer
from emulator.rendering.sprite_renderer import (
    SPRITE_FLIP_HORIZONTAL,
    SPRITE_FLIP_VERTICAL,
    SpriteEntry,
    render_sprite_8x8_to_framebuffer,
)
from tests.chapter_09_sprite_rendering.test_304_render_one_sprite_8x8 import (
    encode_chr_tile,
    make_sprite_palettes,
)


def make_corner_marker_tile() -> bytes:
    """
    Build a tile with visible pixels in distinct corners.

    Color index placement:
        top-left     = 1
        top-right    = 2
        bottom-left  = 3
        bottom-right = 1
    """
    grid = [[0 for _ in range(8)] for _ in range(8)]
    grid[0][0] = 1
    grid[0][7] = 2
    grid[7][0] = 3
    grid[7][7] = 1
    return encode_chr_tile(grid)


def test_horizontal_flip_mirrors_sprite_pixels_left_to_right():
    """
    Objective:
    Horizontal flip mirrors source pixels along the X axis inside the 8x8 sprite box.
    """
    framebuffer = Framebuffer(width=8, height=8)
    sprite = SpriteEntry(
        y=0,
        tile_index=0,
        attributes=SPRITE_FLIP_HORIZONTAL,
        x=0,
    )

    render_sprite_8x8_to_framebuffer(
        framebuffer,
        sprite,
        make_corner_marker_tile(),
        make_sprite_palettes(),
    )

    assert framebuffer.get_pixel(7, 0) == (10, 0, 0)  # original top-left moved right
    assert framebuffer.get_pixel(0, 0) == (20, 0, 0)  # original top-right moved left
    assert framebuffer.get_pixel(7, 7) == (30, 0, 0)  # original bottom-left moved right
    assert framebuffer.get_pixel(0, 7) == (10, 0, 0)  # original bottom-right moved left


def test_vertical_flip_mirrors_sprite_pixels_top_to_bottom():
    """
    Objective:
    Vertical flip mirrors source pixels along the Y axis inside the 8x8 sprite box.
    """
    framebuffer = Framebuffer(width=8, height=8)
    sprite = SpriteEntry(
        y=0,
        tile_index=0,
        attributes=SPRITE_FLIP_VERTICAL,
        x=0,
    )

    render_sprite_8x8_to_framebuffer(
        framebuffer,
        sprite,
        make_corner_marker_tile(),
        make_sprite_palettes(),
    )

    assert framebuffer.get_pixel(0, 7) == (10, 0, 0)  # original top-left moved down
    assert framebuffer.get_pixel(7, 7) == (20, 0, 0)  # original top-right moved down
    assert framebuffer.get_pixel(0, 0) == (30, 0, 0)  # original bottom-left moved up
    assert framebuffer.get_pixel(7, 0) == (10, 0, 0)  # original bottom-right moved up


def test_horizontal_and_vertical_flip_work_together():
    """
    Objective:
    When both flip bits are set, pixels are mirrored on both axes.
    """
    framebuffer = Framebuffer(width=8, height=8)
    sprite = SpriteEntry(
        y=0,
        tile_index=0,
        attributes=SPRITE_FLIP_HORIZONTAL | SPRITE_FLIP_VERTICAL,
        x=0,
    )

    render_sprite_8x8_to_framebuffer(
        framebuffer,
        sprite,
        make_corner_marker_tile(),
        make_sprite_palettes(),
    )

    assert framebuffer.get_pixel(7, 7) == (10, 0, 0)  # original top-left
    assert framebuffer.get_pixel(0, 7) == (20, 0, 0)  # original top-right
    assert framebuffer.get_pixel(7, 0) == (30, 0, 0)  # original bottom-left
    assert framebuffer.get_pixel(0, 0) == (10, 0, 0)  # original bottom-right


def test_flip_does_not_change_sprite_screen_position():
    """
    Objective:
    Flipping mirrors pixels inside the 8x8 box but keeps the destination box at
    sprite.x and sprite.y.
    """
    tile = encode_chr_tile(
        [[1 if x == 7 and y == 7 else 0 for x in range(8)] for y in range(8)]
    )
    framebuffer = Framebuffer(width=16, height=16)
    sprite = SpriteEntry(
        y=4,
        tile_index=0,
        attributes=SPRITE_FLIP_HORIZONTAL | SPRITE_FLIP_VERTICAL,
        x=5,
    )

    render_sprite_8x8_to_framebuffer(framebuffer, sprite, tile, make_sprite_palettes())

    assert framebuffer.get_pixel(5, 4) == (10, 0, 0)
    assert framebuffer.get_pixel(4, 4) == BLACK
    assert framebuffer.get_pixel(13, 12) == BLACK


def test_transparency_still_applies_after_flip():
    """
    Objective:
    Color index 0 remains transparent even when the source pixel is selected through
    flipped coordinates.
    """
    tile = encode_chr_tile(
        [[1 if x == 7 and y == 0 else 0 for x in range(8)] for y in range(8)]
    )
    framebuffer = Framebuffer(width=8, height=8)
    framebuffer.set_pixel(7, 0, (99, 88, 77))
    sprite = SpriteEntry(y=0, tile_index=0, attributes=SPRITE_FLIP_HORIZONTAL, x=0)

    render_sprite_8x8_to_framebuffer(framebuffer, sprite, tile, make_sprite_palettes())

    assert framebuffer.get_pixel(0, 0) == (10, 0, 0)
    assert framebuffer.get_pixel(7, 0) == (99, 88, 77)


def test_flip_support_does_not_import_pygame_or_render_all_sprites():
    """
    Objective:
    Flip support belongs to pure one-sprite framebuffer rendering. It should not add
    frontend dependencies or all-sprite logic yet.
    """
    source = Path("emulator/rendering/sprite_renderer.py").read_text()

    assert "import pygame" not in source
    assert "render_all" not in source
