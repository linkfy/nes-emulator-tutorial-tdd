"""
Composite background and sprites into one framebuffer.

File to create:
    emulator/rendering/frame_compositor.py

Why this step exists:
The emulator can now render background framebuffer data and render OAM sprites into
a framebuffer. This step combines those paths:

    background framebuffer + OAM sprites -> final framebuffer

Important design choice:
The compositor should return a new Framebuffer. It should not mutate the original
background framebuffer. This makes the function easier to reason about and easier
to test.

Suggested implementation example:

    from emulator.rendering.framebuffer import Framebuffer
    from emulator.rendering.palette_ram import SpritePalettes
    from emulator.rendering.sprite_renderer import render_oam_sprites_to_framebuffer


    def composite_background_and_sprites(
        background: Framebuffer,
        oam: bytes | bytearray,
        pattern_table: bytes,
        sprite_palettes: SpritePalettes,
    ) -> Framebuffer:
        framebuffer = Framebuffer(
            width=background.width,
            height=background.height,
            pixels=list(background.pixels),
        )

        render_oam_sprites_to_framebuffer(
            framebuffer,
            oam,
            pattern_table,
            sprite_palettes,
        )

        return framebuffer

Out of scope:
    - sprite priority behind background
    - sprite 0 hit
    - sprite overflow
    - 8x16 sprites
    - Console integration
    - pygame
"""

from pathlib import Path

from emulator.rendering.frame_compositor import composite_background_and_sprites
from emulator.rendering.framebuffer import Framebuffer
from tests.chapter_09_sprite_rendering.test_304_render_one_sprite_8x8 import (
    encode_chr_tile,
    make_sprite_palettes,
)
from tests.chapter_09_sprite_rendering.test_306_render_all_oam_sprites import (
    OAM_SIZE,
    make_offscreen_oam,
    write_oam_sprite,
)


def make_single_pixel_tile(color_index: int) -> bytes:
    """Create one CHR tile with a single visible pixel at tile coordinate (0, 0)."""
    return encode_chr_tile(
        [[color_index if x == 0 and y == 0 else 0 for x in range(8)] for y in range(8)]
    )


def test_frame_compositor_file_exists():
    """
    Objective:
    Composition lives in its own rendering module instead of being hidden in
    main.py or Console.
    """
    assert Path("emulator/rendering/frame_compositor.py").exists()


def test_composite_background_and_sprites_returns_new_framebuffer():
    """
    Objective:
    The compositor returns a new framebuffer object rather than mutating and
    returning the original background input.
    """
    background = Framebuffer(width=8, height=8)
    oam = make_offscreen_oam()

    result = composite_background_and_sprites(
        background,
        oam,
        make_single_pixel_tile(1),
        make_sprite_palettes(),
    )

    assert isinstance(result, Framebuffer)
    assert result is not background
    assert result.width == background.width
    assert result.height == background.height


def test_composite_background_and_sprites_does_not_mutate_background():
    """
    Objective:
    The input background framebuffer remains unchanged after sprite overlay.
    """
    background = Framebuffer(width=8, height=8)
    background.set_pixel(0, 0, (1, 2, 3))
    before = list(background.pixels)

    oam = make_offscreen_oam()
    write_oam_sprite(oam, 0, y=0, tile_index=0, attributes=0, x=0)

    result = composite_background_and_sprites(
        background,
        oam,
        make_single_pixel_tile(1),
        make_sprite_palettes(),
    )

    assert background.pixels == before
    assert result.get_pixel(0, 0) == (10, 0, 0)


def test_composite_preserves_background_where_no_sprite_draws():
    """
    Objective:
    Pixels not covered by non-transparent sprite pixels keep their background color.
    """
    background = Framebuffer(width=8, height=8)
    background.set_pixel(5, 5, (44, 55, 66))

    oam = make_offscreen_oam()
    write_oam_sprite(oam, 0, y=0, tile_index=0, attributes=0, x=0)

    result = composite_background_and_sprites(
        background,
        oam,
        make_single_pixel_tile(1),
        make_sprite_palettes(),
    )

    assert result.get_pixel(5, 5) == (44, 55, 66)


def test_composite_overlays_sprite_pixels_on_background_copy():
    """
    Objective:
    Non-transparent sprite pixels appear in the returned framebuffer.
    """
    background = Framebuffer(width=8, height=8)
    background.set_pixel(2, 3, (1, 2, 3))

    oam = make_offscreen_oam()
    write_oam_sprite(oam, 0, y=3, tile_index=0, attributes=0, x=2)

    result = composite_background_and_sprites(
        background,
        oam,
        make_single_pixel_tile(2),
        make_sprite_palettes(),
    )

    assert result.get_pixel(2, 3) == (20, 0, 0)


def test_composite_preserves_background_under_transparent_sprite_pixels():
    """
    Objective:
    Sprite color index 0 is transparent, so background pixels remain visible.
    """
    background = Framebuffer(width=8, height=8)
    background.set_pixel(0, 0, (99, 88, 77))

    oam = make_offscreen_oam()
    write_oam_sprite(oam, 0, y=0, tile_index=0, attributes=0, x=0)

    transparent_tile = encode_chr_tile([[0 for _ in range(8)] for _ in range(8)])

    result = composite_background_and_sprites(
        background,
        oam,
        transparent_tile,
        make_sprite_palettes(),
    )

    assert result.get_pixel(0, 0) == (99, 88, 77)


def test_composite_uses_all_sprite_renderer_priority_behavior():
    """
    Objective:
    Composition should preserve all-sprite OAM priority behavior: lower OAM index
    appears in front when sprites overlap.
    """
    background = Framebuffer(width=8, height=8)
    oam = make_offscreen_oam()
    write_oam_sprite(oam, 0, y=0, tile_index=0, attributes=0, x=0)
    write_oam_sprite(oam, 1, y=0, tile_index=1, attributes=0, x=0)

    pattern_table = make_single_pixel_tile(1) + make_single_pixel_tile(2)

    result = composite_background_and_sprites(
        background,
        oam,
        pattern_table,
        make_sprite_palettes(),
    )

    assert result.get_pixel(0, 0) == (10, 0, 0)


def test_compositor_accepts_bytes_or_bytearray_oam():
    """
    Objective:
    The compositor can use either mutable PPU.oam data or immutable OAM snapshots.
    """
    background = Framebuffer(width=8, height=8)
    oam = make_offscreen_oam()
    write_oam_sprite(oam, 0, y=0, tile_index=0, attributes=0, x=0)

    result_from_bytearray = composite_background_and_sprites(
        background,
        oam,
        make_single_pixel_tile(1),
        make_sprite_palettes(),
    )
    result_from_bytes = composite_background_and_sprites(
        background,
        bytes(oam),
        make_single_pixel_tile(1),
        make_sprite_palettes(),
    )

    assert result_from_bytearray.get_pixel(0, 0) == (10, 0, 0)
    assert result_from_bytes.get_pixel(0, 0) == (10, 0, 0)


def test_compositor_does_not_import_pygame_or_console():
    """
    Objective:
    Composition is pure rendering data logic. Console and pygame integration come
    later.
    """
    source = Path("emulator/rendering/frame_compositor.py").read_text()

    assert "import pygame" not in source
    assert "Console" not in source
