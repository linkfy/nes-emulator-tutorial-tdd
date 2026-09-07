"""
Use the background opacity mask to apply sprite priority bit 5.

File to update:
    emulator/rendering/sprite_renderer.py

Why this step exists:
Step 310 built a per-pixel background opacity mask. Step 311 threaded that mask
through the sprite rendering pipeline. This step finally uses the mask in the
one-sprite renderer.

Rule:

    If a sprite pixel is non-transparent,
    and the sprite has priority bit 5 set,
    and the background mask says that screen pixel is opaque,
    then keep the background pixel and skip drawing the sprite pixel.

Important ordering:

    1. sprite CHR color index 0 -> skip
    2. offscreen pixel -> skip
    3. behind-background sprite over opaque background -> skip
    4. otherwise draw sprite pixel

Example implementation fragment:

def render_sprite_8x8_to_framebuffer (...) -> ...
    ...
    ... 

    screen_x = sprite.x + tile_x
    screen_y = sprite.y + tile_y

    if not (0 <= screen_x < framebuffer.width):
        continue
    if not (0 <= screen_y < framebuffer.height):
        continue

    # --- ADD THIS NEW BLOCK ---
    if (
        background_opaque_mask is not None
        and attributes.is_behind_background
        and background_opaque_mask[screen_y * framebuffer.width + screen_x]
    ):
        continue
    # --- END NEW BLOCK ---

    framebuffer.set_pixel(...)

Why after clipping?
The mask index uses screen coordinates. If you index the mask before checking that
the pixel is on screen, offscreen sprites can read the wrong mask entry or raise an
IndexError.

Out of scope:
    - building the mask inside Console.render_framebuffer()
    - selecting the background pattern table from PPUCTRL bit 4
    - sprite 0 hit
    - sprite overflow
    - pygame
"""

from emulator.rendering.framebuffer import Framebuffer
from emulator.rendering.nametable_renderer import BackgroundOpaqueMask
from emulator.rendering.sprite_renderer import (
    SPRITE_IS_BEHIND_BACKGROUND,
    SpriteEntry,
    render_sprite_8x8_to_framebuffer,
)
from tests.chapter_09_sprite_rendering.test_304_render_one_sprite_8x8 import encode_chr_tile


BACKGROUND_COLOR = (1, 1, 1)
SPRITE_COLOR = (200, 20, 20)


def make_pattern_table_with_one_tile(tile: bytes) -> bytes:
    pattern_table = bytearray(0x1000)
    pattern_table[0:16] = tile
    return bytes(pattern_table)


def make_tile_with_single_pixel(x: int, y: int, color_index: int) -> bytes:
    grid = [[0 for _ in range(8)] for _ in range(8)]
    grid[y][x] = color_index
    return encode_chr_tile(grid)


def make_sprite_palettes():
    return [
        [(0, 0, 0), SPRITE_COLOR, (0, 200, 0), (0, 0, 200)],
        [(0, 0, 0)] * 4,
        [(0, 0, 0)] * 4,
        [(0, 0, 0)] * 4,
    ]


def make_background_framebuffer() -> Framebuffer:
    return Framebuffer(
        width=8,
        height=8,
        pixels=[BACKGROUND_COLOR] * 64,
    )


def test_behind_background_sprite_is_hidden_when_background_mask_is_opaque():
    """
    Objective:
    Priority bit 5 should prevent a sprite pixel from replacing an opaque
    background pixel.
    """
    framebuffer = make_background_framebuffer()
    pattern_table = make_pattern_table_with_one_tile(
        make_tile_with_single_pixel(x=0, y=0, color_index=1)
    )
    sprite = SpriteEntry(
        y=0,
        tile_index=0,
        attributes=SPRITE_IS_BEHIND_BACKGROUND,
        x=0,
    )
    mask: BackgroundOpaqueMask = [True] * 64

    render_sprite_8x8_to_framebuffer(
        framebuffer=framebuffer,
        sprite=sprite,
        pattern_table=pattern_table,
        sprite_palettes=make_sprite_palettes(),
        background_opaque_mask=mask,
    )

    assert framebuffer.get_pixel(0, 0) == BACKGROUND_COLOR


def test_behind_background_sprite_draws_when_background_mask_is_transparent():
    """
    Objective:
    A behind-background sprite is still visible where the background CHR color index
    was zero.
    """
    framebuffer = make_background_framebuffer()
    pattern_table = make_pattern_table_with_one_tile(
        make_tile_with_single_pixel(x=0, y=0, color_index=1)
    )
    sprite = SpriteEntry(
        y=0,
        tile_index=0,
        attributes=SPRITE_IS_BEHIND_BACKGROUND,
        x=0,
    )
    mask: BackgroundOpaqueMask = [False] * 64

    render_sprite_8x8_to_framebuffer(
        framebuffer=framebuffer,
        sprite=sprite,
        pattern_table=pattern_table,
        sprite_palettes=make_sprite_palettes(),
        background_opaque_mask=mask,
    )

    assert framebuffer.get_pixel(0, 0) == SPRITE_COLOR


def test_front_priority_sprite_draws_even_when_background_mask_is_opaque():
    """
    Objective:
    The mask only hides sprites whose priority bit says they are behind the
    background.
    """
    framebuffer = make_background_framebuffer()
    pattern_table = make_pattern_table_with_one_tile(
        make_tile_with_single_pixel(x=0, y=0, color_index=1)
    )
    sprite = SpriteEntry(
        y=0,
        tile_index=0,
        attributes=0,
        x=0,
    )
    mask: BackgroundOpaqueMask = [True] * 64

    render_sprite_8x8_to_framebuffer(
        framebuffer=framebuffer,
        sprite=sprite,
        pattern_table=pattern_table,
        sprite_palettes=make_sprite_palettes(),
        background_opaque_mask=mask,
    )

    assert framebuffer.get_pixel(0, 0) == SPRITE_COLOR


def test_transparent_sprite_pixel_still_draws_nothing_even_with_transparent_background_mask():
    """
    Objective:
    Sprite CHR color index 0 remains transparent. The background mask does not make
    transparent sprite pixels visible.
    """
    framebuffer = make_background_framebuffer()
    pattern_table = make_pattern_table_with_one_tile(
        make_tile_with_single_pixel(x=0, y=0, color_index=0)
    )
    sprite = SpriteEntry(
        y=0,
        tile_index=0,
        attributes=SPRITE_IS_BEHIND_BACKGROUND,
        x=0,
    )
    mask: BackgroundOpaqueMask = [False] * 64

    render_sprite_8x8_to_framebuffer(
        framebuffer=framebuffer,
        sprite=sprite,
        pattern_table=pattern_table,
        sprite_palettes=make_sprite_palettes(),
        background_opaque_mask=mask,
    )

    assert framebuffer.get_pixel(0, 0) == BACKGROUND_COLOR


def test_priority_mask_is_not_required_for_old_front_sprite_behavior():
    """
    Objective:
    The optional mask keeps old callers working. Without a mask, non-transparent
    sprite pixels still draw as before.
    """
    framebuffer = make_background_framebuffer()
    pattern_table = make_pattern_table_with_one_tile(
        make_tile_with_single_pixel(x=0, y=0, color_index=1)
    )
    sprite = SpriteEntry(
        y=0,
        tile_index=0,
        attributes=SPRITE_IS_BEHIND_BACKGROUND,
        x=0,
    )

    render_sprite_8x8_to_framebuffer(
        framebuffer=framebuffer,
        sprite=sprite,
        pattern_table=pattern_table,
        sprite_palettes=make_sprite_palettes(),
    )

    assert framebuffer.get_pixel(0, 0) == SPRITE_COLOR
