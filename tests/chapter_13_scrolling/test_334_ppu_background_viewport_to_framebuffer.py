"""
Compose the horizontal background framebuffer from current PPU scroll state.

File to update:
    emulator/rendering/ppu_background_renderer.py

References:
    https://www.nesdev.org/wiki/PPU_scrolling
    https://www.nesdev.org/wiki/PPU_nametables

Why this step exists:
Previous steps can render one selected logical nametable and can compose two existing
framebuffers. This adapter connects those mechanisms to current PPU scroll state.

Horizontal flow:

    temp_vram_addr + fine_x
              |
              v
        decode viewport X
              |
              v
    select horizontal logical pair
              |
              v
    render left and right nametables
              |
              v
    compose one 256x240 framebuffer

Logical pair selection:

    nametable Y = 0 -> left $2000, right $2400
    nametable Y = 1 -> left $2800, right $2C00

Nametable X remains part of decoded viewport X. For example, nametable X=1,
coarse X=5, and fine X=3 produce viewport X 299.

Compatibility:
The existing ppu_background_to_framebuffer() function continues rendering one
selected nametable. This new adapter calls it twice and then composes the results.

Out of scope:
    - opacity-mask composition
    - Console integration
    - sprite-zero-hit integration
    - vertical pixel scrolling
    - pygame

Complete example implementation:

    # emulator/rendering/ppu_background_renderer.py

    # --- NEW LINES: HORIZONTAL VIEWPORT OPERATIONS ---
    from emulator.rendering.background_viewport import (
        compose_horizontal_framebuffer_viewport,
        compose_horizontal_opaque_mask_viewport,
        decode_background_viewport_position,
    )

    ...

    # --- NEW BLOCK: COMPOSE THE HORIZONTAL FRAMEBUFFER VIEWPORT ---
    def ppu_background_viewport_to_framebuffer(ppu: PPU) -> Framebuffer:
        viewport_x, _ = decode_background_viewport_position(
            temp_vram_addr=ppu.temp_vram_addr,
            fine_x=ppu.fine_x,
        )

        nametable_y = (ppu.temp_vram_addr >> 11) & 1
        left_base = BASE_NAMETABLE_ADDR + nametable_y * 0x0800
        right_base = left_base + 0x0400

        left = ppu_background_to_framebuffer(
            ppu,
            base_nametable_addr=left_base,
        )
        right = ppu_background_to_framebuffer(
            ppu,
            base_nametable_addr=right_base,
        )

        return compose_horizontal_framebuffer_viewport(
            left=left,
            right=right,
            viewport_x=viewport_x,
        )
"""

import pytest

from emulator.ppu.ppu import PPU
from emulator.rendering.framebuffer import Framebuffer
import emulator.rendering.ppu_background_renderer as background_renderer
from emulator.rendering.ppu_background_renderer import (
    ppu_background_viewport_to_framebuffer,
)


@pytest.mark.parametrize(
    ("nametable_y", "expected_left_base", "expected_right_base"),
    [
        (0, 0x2000, 0x2400),
        (1, 0x2800, 0x2C00),
    ],
)
def test_framebuffer_viewport_renders_and_composes_selected_horizontal_pair(
    monkeypatch,
    nametable_y,
    expected_left_base,
    expected_right_base,
):
    """
    Objective:
    Decode viewport X, select the logical row, render both horizontal neighbors, and
    pass those exact framebuffers to the pure compositor.
    """
    ppu = PPU()
    ppu.temp_vram_addr = (
        (1 << 10)          # nametable X = 1
        | (nametable_y << 11)
        | 5                # coarse X = 5
    )
    ppu.fine_x = 3

    left = Framebuffer()
    right = Framebuffer()
    expected_result = Framebuffer()
    sources = {
        expected_left_base: left,
        expected_right_base: right,
    }
    rendered_bases: list[int] = []
    captured = {}

    def fake_render_one(ppu_argument, base_nametable_addr):
        assert ppu_argument is ppu
        rendered_bases.append(base_nametable_addr)
        return sources[base_nametable_addr]

    def fake_compose(*, left, right, viewport_x):
        captured["left"] = left
        captured["right"] = right
        captured["viewport_x"] = viewport_x
        return expected_result

    monkeypatch.setattr(
        background_renderer,
        "ppu_background_to_framebuffer",
        fake_render_one,
    )
    monkeypatch.setattr(
        background_renderer,
        "compose_horizontal_framebuffer_viewport",
        fake_compose,
    )

    result = ppu_background_viewport_to_framebuffer(ppu)

    assert rendered_bases == [expected_left_base, expected_right_base]
    assert captured["left"] is left
    assert captured["right"] is right
    assert captured["viewport_x"] == 299
    assert result is expected_result


def test_framebuffer_viewport_does_not_build_opacity_masks(monkeypatch):
    """
    Objective:
    Keep the framebuffer adapter focused on RGB rendering and composition.
    """
    ppu = PPU()
    source = Framebuffer()
    expected_result = Framebuffer()

    monkeypatch.setattr(
        background_renderer,
        "ppu_background_to_framebuffer",
        lambda ppu_argument, base_nametable_addr: source,
    )
    monkeypatch.setattr(
        background_renderer,
        "compose_horizontal_framebuffer_viewport",
        lambda **kwargs: expected_result,
    )

    def forbidden_mask_call(*args, **kwargs):
        raise AssertionError("Framebuffer viewport must not build opacity masks")

    monkeypatch.setattr(
        background_renderer,
        "ppu_background_to_opaque_mask",
        forbidden_mask_call,
    )

    assert ppu_background_viewport_to_framebuffer(ppu) is expected_result
