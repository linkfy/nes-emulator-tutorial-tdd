"""
Render all 64 OAM sprites into framebuffer data.

File to update:
    emulator/rendering/sprite_renderer.py

Why this step exists:
We can now render one SpriteEntry. Since OAMDMA fills PPU.oam with 64 sprite
entries, the next step is to loop over all OAM entries and render each sprite into
the target framebuffer.

Important sprite priority rule:
When sprites overlap, lower OAM index has higher priority:

    sprite 0 is in front of sprite 1
    sprite 1 is in front of sprite 2
    ...

Because this renderer mutates a framebuffer, draw in reverse OAM order:

    sprite 63 first
    ...
    sprite 0 last

That way lower-index sprites overwrite higher-index sprites at overlapping pixels.

Suggested implementation example:

    def render_oam_sprites_to_framebuffer(
        framebuffer: Framebuffer,
        oam: bytes | bytearray,
        pattern_table: bytes,
        sprite_palettes: SpritePalettes,
    ) -> None:
        if len(oam) < OAM_SIZE:
            raise ValueError("OAM must contain 256 bytes")

        for sprite_index in reversed(range(OAM_SPRITE_COUNT)):
            sprite = decode_sprite_entry(oam, sprite_index)
            render_sprite_8x8_to_framebuffer(
                framebuffer,
                sprite,
                pattern_table,
                sprite_palettes,
            )

Out of scope:
    - sprite 0 hit
    - sprite overflow
    - background priority/compositing policy
    - 8x16 sprites
    - scanline sprite evaluation
    - pygame
"""

from pathlib import Path

import pytest

from emulator.rendering.framebuffer import Framebuffer
from emulator.rendering.sprite_renderer import (
    BYTES_PER_SPRITE,
    OAM_SIZE,
    OAM_SPRITE_COUNT,
    render_oam_sprites_to_framebuffer,
)
from tests.chapter_09_sprite_rendering.test_304_render_one_sprite_8x8 import (
    encode_chr_tile,
    make_sprite_palettes,
)


def make_single_pixel_tile(color_index: int) -> bytes:
    """Create a tile with one visible pixel at tile coordinate (0, 0)."""
    return encode_chr_tile(
        [[color_index if x == 0 and y == 0 else 0 for x in range(8)] for y in range(8)]
    )


def write_oam_sprite(
    oam: bytearray,
    sprite_index: int,
    *,
    y: int,
    tile_index: int,
    attributes: int,
    x: int,
) -> None:
    """Write one synthetic OAM sprite entry in raw NES byte order."""
    base = sprite_index * BYTES_PER_SPRITE
    oam[base + 0] = y
    oam[base + 1] = tile_index
    oam[base + 2] = attributes
    oam[base + 3] = x


def make_offscreen_oam() -> bytearray:
    """
    Create a full OAM buffer where unused sprites are safely offscreen but point to
    tile 0.

    Do not fill OAM with 0xFF for these tests: that would also set tile_index=255
    for every unused sprite and require a full 4096-byte pattern table.
    """
    oam = bytearray(OAM_SIZE)

    for sprite_index in range(OAM_SPRITE_COUNT):
        write_oam_sprite(
            oam,
            sprite_index,
            y=0xFF,
            tile_index=0,
            attributes=0,
            x=0xFF,
        )

    return oam


def test_render_oam_sprites_renders_multiple_oam_entries():
    """
    Objective:
    The all-sprite renderer should visit OAM entries and render more than one
    sprite into the framebuffer.
    """
    oam = make_offscreen_oam()
    write_oam_sprite(oam, 0, y=1, tile_index=0, attributes=0, x=1)
    write_oam_sprite(oam, 1, y=2, tile_index=1, attributes=0, x=2)

    pattern_table = make_single_pixel_tile(1) + make_single_pixel_tile(2)
    framebuffer = Framebuffer(width=16, height=16)

    render_oam_sprites_to_framebuffer(
        framebuffer,
        oam,
        pattern_table,
        make_sprite_palettes(),
    )

    assert framebuffer.get_pixel(1, 1) == (10, 0, 0)
    assert framebuffer.get_pixel(2, 2) == (20, 0, 0)


def test_render_oam_sprites_draws_lower_oam_index_in_front_when_overlapping():
    """
    Objective:
    Lower OAM index has higher sprite priority. Since rendering mutates the
    framebuffer, sprite 0 must be drawn after sprite 1.
    """
    oam = make_offscreen_oam()
    write_oam_sprite(oam, 0, y=0, tile_index=0, attributes=0, x=0)
    write_oam_sprite(oam, 1, y=0, tile_index=1, attributes=0, x=0)

    pattern_table = make_single_pixel_tile(1) + make_single_pixel_tile(2)
    framebuffer = Framebuffer(width=8, height=8)

    render_oam_sprites_to_framebuffer(
        framebuffer,
        oam,
        pattern_table,
        make_sprite_palettes(),
    )

    assert framebuffer.get_pixel(0, 0) == (10, 0, 0)


def test_render_oam_sprites_accepts_bytearray_oam_source():
    """
    Objective:
    PPU.oam is mutable bytearray data, so the all-sprite renderer should accept
    bytearray OAM directly.
    """
    oam = make_offscreen_oam()
    write_oam_sprite(oam, 0, y=0, tile_index=0, attributes=0, x=0)
    framebuffer = Framebuffer(width=8, height=8)

    render_oam_sprites_to_framebuffer(
        framebuffer,
        oam,
        make_single_pixel_tile(3),
        make_sprite_palettes(),
    )

    assert framebuffer.get_pixel(0, 0) == (30, 0, 0)


def test_render_oam_sprites_accepts_bytes_oam_source():
    """
    Objective:
    The renderer can also observe immutable bytes OAM snapshots.
    """
    oam = make_offscreen_oam()
    write_oam_sprite(oam, 0, y=0, tile_index=0, attributes=0, x=0)
    framebuffer = Framebuffer(width=8, height=8)

    render_oam_sprites_to_framebuffer(
        framebuffer,
        bytes(oam),
        make_single_pixel_tile(1),
        make_sprite_palettes(),
    )

    assert framebuffer.get_pixel(0, 0) == (10, 0, 0)


def test_render_oam_sprites_rejects_short_oam():
    """
    Objective:
    All-sprite rendering requires a full 256-byte OAM buffer.
    """
    framebuffer = Framebuffer(width=8, height=8)

    with pytest.raises(ValueError, match="OAM must contain 256 bytes"):
        render_oam_sprites_to_framebuffer(
            framebuffer,
            bytearray(OAM_SIZE - 1),
            make_single_pixel_tile(1),
            make_sprite_palettes(),
        )


def test_render_oam_sprites_visits_last_valid_oam_entry():
    """
    Objective:
    Sprite index 63 is included in the all-sprite loop.
    """
    oam = make_offscreen_oam()
    write_oam_sprite(
        oam,
        OAM_SPRITE_COUNT - 1,
        y=3,
        tile_index=0,
        attributes=0,
        x=4,
    )
    framebuffer = Framebuffer(width=16, height=16)

    render_oam_sprites_to_framebuffer(
        framebuffer,
        oam,
        make_single_pixel_tile(1),
        make_sprite_palettes(),
    )

    assert framebuffer.get_pixel(4, 3) == (10, 0, 0)


def test_render_oam_sprites_uses_existing_one_sprite_behaviors():
    """
    Objective:
    All-sprite rendering should preserve one-sprite behavior such as palette
    selection, transparency, and clipping by delegating to the existing renderer.
    """
    oam = make_offscreen_oam()
    write_oam_sprite(oam, 0, y=0, tile_index=0, attributes=0b0000_0010, x=0)
    framebuffer = Framebuffer(width=1, height=1)

    render_oam_sprites_to_framebuffer(
        framebuffer,
        oam,
        make_single_pixel_tile(2),
        make_sprite_palettes(),
    )

    assert framebuffer.get_pixel(0, 0) == (0, 0, 20)


def test_render_oam_sprites_does_not_import_pygame_or_implement_sprite_flags():
    """
    Objective:
    This step renders all sprites as pure framebuffer data. It should not add
    frontend dependencies or timing flags such as sprite 0 hit/overflow.
    """
    source = Path("emulator/rendering/sprite_renderer.py").read_text()

    assert "import pygame" not in source
    assert "SPRITE_ZERO_HIT" not in source
    assert "SPRITE_OVERFLOW" not in source
