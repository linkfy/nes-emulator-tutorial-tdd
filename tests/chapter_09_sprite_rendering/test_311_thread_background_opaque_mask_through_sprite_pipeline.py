"""
Thread the background opacity mask through the sprite rendering pipeline.

Files to update:
    emulator/rendering/frame_compositor.py
    emulator/rendering/sprite_renderer.py

Why this step exists:
Step 310 created a BackgroundOpaqueMask. Before we apply sprite priority behavior,
we first make the relevant functions accept and forward that mask.

This keeps the tutorial incremental:

    Step 310 -> build the mask
    Step 311 -> thread the mask through function signatures
    Step 312 -> use the mask to enforce sprite priority bit 5

Required API shape:

    def composite_background_and_sprites(
        background: Framebuffer,
        oam: bytes | bytearray,
        pattern_table: bytes,
        sprite_palettes: SpritePalettes,
        # --- ADD THIS NEW LINE ---
        background_opaque_mask: BackgroundOpaqueMask | None = None,
    ) -> Framebuffer:
        ...
        render_oam_sprites_to_framebuffer(
            framebuffer,
            oam,
            pattern_table,
            sprite_palettes,
            # --- ADD THIS NEW LINE ---
            background_opaque_mask,
        )
        ...


    def render_oam_sprites_to_framebuffer(
        framebuffer: Framebuffer,
        oam: bytes | bytearray,
        pattern_table: bytes,
        sprite_palettes: SpritePalettes,
        # --- ADD THIS NEW LINE ---
        background_opaque_mask: BackgroundOpaqueMask | None = None,
    ) -> None:
        ...
        render_sprite_8x8_to_framebuffer(
            framebuffer,
            sprite,
            pattern_table,
            sprite_palettes,
            # --- ADD THIS NEW LINE ---
            background_opaque_mask,
        )


    def render_sprite_8x8_to_framebuffer(
        framebuffer: Framebuffer,
        sprite: SpriteEntry,
        pattern_table: bytes,
        sprite_palettes: SpritePalettes,
        # --- ADD THIS NEW LINE ---
        background_opaque_mask: BackgroundOpaqueMask | None = None,
    ) -> None:
        ...

Also add the type import where needed:

    # --- ADD THIS NEW LINE ---
    from emulator.rendering.nametable_renderer import BackgroundOpaqueMask

Important:
This step does not require using the mask yet. The next step will add the rule:

    if sprite is behind background and background_opaque_mask[pixel] is True:
        skip drawing this sprite pixel

Why optional None?
Older tests and older tutorial steps already call these rendering helpers without a
background mask. Keeping the argument optional preserves backward compatibility
while we evolve the pipeline.

Out of scope:
    - applying sprite priority bit 5
    - changing Console.render_framebuffer()
    - building the mask from PPU state
    - sprite 0 hit
    - sprite overflow
    - pygame
"""

import inspect

from emulator.rendering import frame_compositor
from emulator.rendering.frame_compositor import composite_background_and_sprites
from emulator.rendering.framebuffer import Framebuffer
from emulator.rendering.nametable_renderer import BackgroundOpaqueMask
from emulator.rendering.sprite_renderer import (
    OAM_SIZE,
    render_oam_sprites_to_framebuffer,
    render_sprite_8x8_to_framebuffer,
)


def test_compositor_accepts_optional_background_opaque_mask_parameter():
    """
    Objective:
    The top-level compositor can receive a background opacity mask without breaking
    older calls that do not pass one.
    """
    signature = inspect.signature(composite_background_and_sprites)

    parameter = signature.parameters["background_opaque_mask"]

    assert parameter.default is None


def test_oam_sprite_renderer_accepts_optional_background_opaque_mask_parameter():
    """
    Objective:
    The all-OAM sprite renderer can receive the same optional mask and preserve old
    callers.
    """
    signature = inspect.signature(render_oam_sprites_to_framebuffer)

    parameter = signature.parameters["background_opaque_mask"]

    assert parameter.default is None


def test_single_sprite_renderer_accepts_optional_background_opaque_mask_parameter():
    """
    Objective:
    The one-sprite renderer is the eventual pixel-level decision point, so it must
    also accept the optional mask.
    """
    signature = inspect.signature(render_sprite_8x8_to_framebuffer)

    parameter = signature.parameters["background_opaque_mask"]

    assert parameter.default is None


def test_compositor_forwards_background_opaque_mask_to_oam_renderer(monkeypatch):
    """
    Objective:
    The compositor should not swallow the mask. It should pass it down to the OAM
    sprite renderer.
    """
    background = Framebuffer(width=2, height=2)
    oam = bytes([0] * OAM_SIZE)
    pattern_table = bytes([0] * 0x1000)
    sprite_palettes = [[(0, 0, 0)] * 4 for _ in range(4)]
    mask: BackgroundOpaqueMask = [False, True, False, True]

    captured = {}

    def fake_render_oam_sprites_to_framebuffer(
        framebuffer,
        received_oam,
        received_pattern_table,
        received_sprite_palettes,
        received_background_opaque_mask=None,
    ):
        captured["framebuffer"] = framebuffer
        captured["oam"] = received_oam
        captured["pattern_table"] = received_pattern_table
        captured["sprite_palettes"] = received_sprite_palettes
        captured["background_opaque_mask"] = received_background_opaque_mask

    monkeypatch.setattr(
        frame_compositor,
        "render_oam_sprites_to_framebuffer",
        fake_render_oam_sprites_to_framebuffer,
    )

    result = composite_background_and_sprites(
        background=background,
        oam=oam,
        pattern_table=pattern_table,
        sprite_palettes=sprite_palettes,
        background_opaque_mask=mask,
    )

    assert result is captured["framebuffer"]
    assert captured["oam"] is oam
    assert captured["pattern_table"] is pattern_table
    assert captured["sprite_palettes"] is sprite_palettes
    assert captured["background_opaque_mask"] is mask


def test_oam_renderer_forwards_background_opaque_mask_to_single_sprite_renderer(monkeypatch):
    """
    Objective:
    The OAM renderer should pass the mask to each individual sprite render call.
    """
    framebuffer = Framebuffer(width=8, height=8)
    oam = bytes([0] * OAM_SIZE)
    pattern_table = bytes([0] * 0x1000)
    sprite_palettes = [[(0, 0, 0)] * 4 for _ in range(4)]
    mask: BackgroundOpaqueMask = [False] * (framebuffer.width * framebuffer.height)

    captured_masks = []

    import emulator.rendering.sprite_renderer as sprite_renderer_module

    def fake_render_sprite_8x8_to_framebuffer(
        received_framebuffer,
        sprite,
        received_pattern_table,
        received_sprite_palettes,
        received_background_opaque_mask=None,
    ):
        captured_masks.append(received_background_opaque_mask)

    monkeypatch.setattr(
        sprite_renderer_module,
        "render_sprite_8x8_to_framebuffer",
        fake_render_sprite_8x8_to_framebuffer,
    )

    render_oam_sprites_to_framebuffer(
        framebuffer=framebuffer,
        oam=oam,
        pattern_table=pattern_table,
        sprite_palettes=sprite_palettes,
        background_opaque_mask=mask,
    )

    assert len(captured_masks) == 64
    assert all(captured_mask is mask for captured_mask in captured_masks)


def test_step_311_does_not_require_console_wiring_yet():
    """
    Objective:
    This step is intentionally about API plumbing only. It should not require
    Console.render_framebuffer() to build or pass a real background mask yet.

    Later steps may use the mask inside the sprite renderer, so this older test must
    not forbid that evolution.
    """
    import emulator.console as console_module

    source = inspect.getsource(console_module.Console.render_framebuffer)

    assert "build_background_opaque_mask" not in source
