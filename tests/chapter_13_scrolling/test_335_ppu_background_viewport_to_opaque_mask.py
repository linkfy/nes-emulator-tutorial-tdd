"""
Compose the horizontal opacity-mask viewport from current PPU scroll state.

File to update:
    emulator/rendering/ppu_background_renderer.py

References:
    https://www.nesdev.org/wiki/PPU_scrolling
    https://www.nesdev.org/wiki/PPU_nametables

Why this looks similar to Step 334:
The opacity-mask adapter intentionally copies the framebuffer adapter's addressing
structure:

    decode the same viewport X
    select the same horizontal logical pair
    process the same left and right bases
    compose using the same viewport X

The important difference is that every data-producing operation must use the
opacity-mask path:

    ppu_background_to_opaque_mask()
    compose_horizontal_opaque_mask_viewport()

It must not accidentally call:

    ppu_background_to_framebuffer()
    compose_horizontal_framebuffer_viewport()

This deliberate copy keeps both paths easy to read. Their parity tests protect the
small duplicated addressing mechanism from drifting.

The resulting mask will later be shared by sprite priority and sprite-zero-hit
detection. This step only constructs it; it does not integrate either consumer.

Out of scope:
    - framebuffer composition
    - Console integration
    - sprite-zero-hit integration
    - vertical pixel scrolling
    - pygame

Complete example implementation:

    # emulator/rendering/ppu_background_renderer.py

    # --- NEW BLOCK: COPY FRAMEBUFFER ADDRESSING FOR THE OPACITY-MASK PATH ---
    def ppu_background_viewport_to_opaque_mask(
        ppu: PPU,
    ) -> BackgroundOpaqueMask:
        viewport_x, _ = decode_background_viewport_position(
            temp_vram_addr=ppu.temp_vram_addr,
            fine_x=ppu.fine_x,
        )

        nametable_y = (ppu.temp_vram_addr >> 11) & 1
        left_base = BASE_NAMETABLE_ADDR + nametable_y * 0x0800
        right_base = left_base + 0x0400

        # Same addresses, but call the opacity-mask producer.
        left = ppu_background_to_opaque_mask(
            ppu,
            base_nametable_addr=left_base,
        )
        right = ppu_background_to_opaque_mask(
            ppu,
            base_nametable_addr=right_base,
        )

        # Use the opacity-mask compositor, not the framebuffer compositor.
        return compose_horizontal_opaque_mask_viewport(
            left=left,
            right=right,
            viewport_x=viewport_x,
        )
"""

import pytest

from emulator.ppu.ppu import PPU
from emulator.rendering.framebuffer import Framebuffer
from emulator.rendering.nametable_renderer import BackgroundOpaqueMask
import emulator.rendering.ppu_background_renderer as background_renderer
from emulator.rendering.ppu_background_renderer import (
    ppu_background_viewport_to_opaque_mask,
)


@pytest.mark.parametrize(
    ("nametable_y", "expected_left_base", "expected_right_base"),
    [
        (0, 0x2000, 0x2400),
        (1, 0x2800, 0x2C00),
    ],
)
def test_opaque_mask_viewport_copies_framebuffer_addressing_with_mask_functions(
    monkeypatch,
    nametable_y,
    expected_left_base,
    expected_right_base,
):
    """
    Objective:
    Use the same PPU coordinate and logical-pair mapping as framebuffer composition,
    while calling only opacity-mask production and composition functions.
    """
    ppu = PPU()
    ppu.temp_vram_addr = (
        (1 << 10)          # nametable X = 1
        | (nametable_y << 11)
        | 5                # coarse X = 5
    )
    ppu.fine_x = 3

    left: BackgroundOpaqueMask = [False, True]
    right: BackgroundOpaqueMask = [True, False]
    expected_result: BackgroundOpaqueMask = [True, True]
    sources = {
        expected_left_base: left,
        expected_right_base: right,
    }
    rendered_bases: list[int] = []
    captured = {}

    def fake_build_one(ppu_argument, base_nametable_addr):
        assert ppu_argument is ppu
        rendered_bases.append(base_nametable_addr)
        return sources[base_nametable_addr]

    def fake_compose(*, left, right, viewport_x):
        captured["left"] = left
        captured["right"] = right
        captured["viewport_x"] = viewport_x
        return expected_result

    def forbidden_framebuffer_call(*args, **kwargs):
        raise AssertionError("Opacity viewport must not render framebuffers")

    monkeypatch.setattr(
        background_renderer,
        "ppu_background_to_opaque_mask",
        fake_build_one,
    )
    monkeypatch.setattr(
        background_renderer,
        "compose_horizontal_opaque_mask_viewport",
        fake_compose,
    )
    monkeypatch.setattr(
        background_renderer,
        "ppu_background_to_framebuffer",
        forbidden_framebuffer_call,
    )
    monkeypatch.setattr(
        background_renderer,
        "compose_horizontal_framebuffer_viewport",
        forbidden_framebuffer_call,
    )

    result = ppu_background_viewport_to_opaque_mask(ppu)

    assert rendered_bases == [expected_left_base, expected_right_base]
    assert captured["left"] is left
    assert captured["right"] is right
    assert captured["viewport_x"] == 299
    assert result is expected_result


def test_framebuffer_and_mask_adapters_decode_the_same_viewport_x(monkeypatch):
    """
    Objective:
    Protect the duplicated coordinate path from drifting between framebuffer and
    opacity-mask behavior.
    """
    ppu = PPU()
    ppu.temp_vram_addr = (1 << 10) | 5
    ppu.fine_x = 3
    captured = {}

    monkeypatch.setattr(
        background_renderer,
        "ppu_background_to_framebuffer",
        lambda ppu_argument, base_nametable_addr: object(),
    )
    monkeypatch.setattr(
        background_renderer,
        "ppu_background_to_opaque_mask",
        lambda ppu_argument, base_nametable_addr: [False],
    )

    def capture_framebuffer_x(*, left, right, viewport_x):
        captured["framebuffer_x"] = viewport_x
        return Framebuffer()

    def capture_mask_x(*, left, right, viewport_x):
        captured["mask_x"] = viewport_x
        return [False]

    monkeypatch.setattr(
        background_renderer,
        "compose_horizontal_framebuffer_viewport",
        capture_framebuffer_x,
    )
    monkeypatch.setattr(
        background_renderer,
        "compose_horizontal_opaque_mask_viewport",
        capture_mask_x,
    )

    background_renderer.ppu_background_viewport_to_framebuffer(ppu)
    ppu_background_viewport_to_opaque_mask(ppu)

    assert captured["framebuffer_x"] == 299
    assert captured["mask_x"] == 299
