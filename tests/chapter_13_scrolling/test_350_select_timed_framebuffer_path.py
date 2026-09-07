"""
Select timed framebuffer composition only when one complete frame is available.

File to update:
    emulator/rendering/ppu_background_renderer.py

References:
    https://www.nesdev.org/wiki/PPU_rendering
    https://www.nesdev.org/wiki/PPU_scrolling

Why this step exists:
The private timed compositor requires one BackgroundScanlineState for every visible
row. That evidence is unavailable during startup and may be absent after an incomplete
frame, so the public adapter needs an explicit compatibility boundary:

    exactly 240 completed states -> use timed row composition
    any other tuple length       -> use the existing t + fine-X snapshot path

Why require exact length instead of truthiness?
An empty tuple is false, but a partial one-entry or 239-entry tuple is true. Partial
timing data still leaves unknown rows and must not enter a compositor that requires
all 240 states. The structural invariant, not whether the tuple is non-empty, decides
which mechanism is safe.

Why preserve the old path?
A new PPU has no completed frame. Historical callers and startup rendering already
have deterministic behavior based on temp_vram_addr plus fine_x. Keeping that body
unchanged provides a safe fallback until the first complete timed frame is published.

Control flow:

    ppu_background_viewport_to_framebuffer(ppu)
                         |
                         v
             completed length == 240?
                    /             \
                  yes              no
                   |                |
                   v                v
          timed row helper    existing snapshot path
                   |                |
                   +------ return --+

Important invariants:
    - exactly 240 entries select the timed helper
    - timed composition returns immediately
    - the old source renderer and full-frame compositor do not also run
    - empty, partial, and oversized tuples select the established fallback
    - the fallback still decodes ppu.temp_vram_addr and ppu.fine_x
    - opacity-mask selection remains unchanged in this lesson

Common misconception:
Do not catch the timed helper's ValueError and silently retry the fallback. The public
gate owns expected availability; an error after the complete-frame gate indicates a
broken invariant that should remain visible during debugging.

Out of scope:
    - timed opacity-mask composition
    - sprite/background priority correction
    - sprite-zero-hit mask integration
    - full vertical source-row scrolling

Complete example implementation:

    # emulator/rendering/ppu_background_renderer.py

    def ppu_background_viewport_to_framebuffer(ppu: PPU) -> Framebuffer:
        # --- NEW BLOCK: USE TIMED DATA ONLY WHEN THE FRAME IS COMPLETE ---
        if (
            len(ppu.completed_scanline_scroll_states)
            == NAMETABLE_PIXEL_HEIGHT
        ):
            return _timed_scanlines_to_framebuffer(ppu)

        # Existing temp_vram_addr + fine_x fallback remains unchanged below.
        viewport_x, _ = decode_background_viewport_position(
            temp_vram_addr=ppu.temp_vram_addr,
            fine_x=ppu.fine_x,
        )
        ...

Manual checkpoint after this lesson:
With your own legal Super Mario Bros. ROM, you can now play far enough to try to catch
a mushroom while observing the timed horizontal background. At this exact milestone,
the mushroom may appear in front of a solid background tile that should visually
occlude it. That symptom is expected: RGB framebuffer rows now use timed scanline
states, but the background opacity mask used for sprite priority still uses one old
frame-level snapshot. The next lesson will compose opacity-mask rows from the same
timed states so color and priority decisions use identical screen coordinates.
"""

import pytest

from emulator.ppu.ppu import BackgroundScanlineState, PPU
from emulator.rendering.background_viewport import NAMETABLE_PIXEL_HEIGHT
from emulator.rendering.framebuffer import Framebuffer
from emulator.rendering import ppu_background_renderer
from emulator.rendering.ppu_background_renderer import (
    ppu_background_viewport_to_framebuffer,
)


def make_states(length: int) -> tuple[BackgroundScanlineState, ...]:
    """Create a tuple whose length controls only public path selection."""
    state = BackgroundScanlineState(vram_addr=0, fine_x=0)
    return (state,) * length


def forbidden_fallback_call(*args, **kwargs):
    """Fail if the complete timed branch continues into old snapshot work."""
    raise AssertionError("Complete timed frame must not execute snapshot fallback")


def test_exactly_240_states_return_timed_framebuffer_without_fallback(monkeypatch):
    """
    Objective:
    Activate the new renderer at its exact structural boundary and return its result.
    """
    ppu = PPU()
    ppu.completed_scanline_scroll_states = make_states(
        NAMETABLE_PIXEL_HEIGHT
    )
    expected = Framebuffer()
    timed_calls: list[PPU] = []

    def fake_timed_compositor(ppu_argument):
        timed_calls.append(ppu_argument)
        return expected

    monkeypatch.setattr(
        ppu_background_renderer,
        "_timed_scanlines_to_framebuffer",
        fake_timed_compositor,
    )
    monkeypatch.setattr(
        ppu_background_renderer,
        "decode_background_viewport_position",
        forbidden_fallback_call,
    )
    monkeypatch.setattr(
        ppu_background_renderer,
        "ppu_background_to_framebuffer",
        forbidden_fallback_call,
    )
    monkeypatch.setattr(
        ppu_background_renderer,
        "compose_horizontal_framebuffer_viewport",
        forbidden_fallback_call,
    )

    result = ppu_background_viewport_to_framebuffer(ppu)

    assert result is expected
    assert timed_calls == [ppu]


@pytest.mark.parametrize("noncomplete_length", [0, 1, 239, 241])
def test_noncomplete_tuples_use_existing_snapshot_fallback(
    monkeypatch,
    noncomplete_length,
):
    """
    Objective:
    Preserve deterministic startup and incomplete-frame behavior without guessing rows.
    """
    ppu = PPU()
    ppu.completed_scanline_scroll_states = make_states(noncomplete_length)
    ppu.temp_vram_addr = (1 << 11) | 5
    ppu.fine_x = 3

    expected = Framebuffer()
    source = Framebuffer()
    rendered_bases: list[int] = []
    decoded_arguments: list[tuple[int, int]] = []
    composed_viewports: list[int] = []

    def forbidden_timed_call(*args, **kwargs):
        raise AssertionError("Incomplete frame must not use timed composition")

    def fake_decode(*, temp_vram_addr, fine_x):
        decoded_arguments.append((temp_vram_addr, fine_x))
        return 43, 0

    def fake_render_one(ppu_argument, base_nametable_addr):
        assert ppu_argument is ppu
        rendered_bases.append(base_nametable_addr)
        return source

    def fake_compose(*, left, right, viewport_x):
        assert left is source
        assert right is source
        composed_viewports.append(viewport_x)
        return expected

    monkeypatch.setattr(
        ppu_background_renderer,
        "_timed_scanlines_to_framebuffer",
        forbidden_timed_call,
    )
    monkeypatch.setattr(
        ppu_background_renderer,
        "decode_background_viewport_position",
        fake_decode,
    )
    monkeypatch.setattr(
        ppu_background_renderer,
        "ppu_background_to_framebuffer",
        fake_render_one,
    )
    monkeypatch.setattr(
        ppu_background_renderer,
        "compose_horizontal_framebuffer_viewport",
        fake_compose,
    )

    result = ppu_background_viewport_to_framebuffer(ppu)

    assert result is expected
    assert decoded_arguments == [(ppu.temp_vram_addr, ppu.fine_x)]
    assert rendered_bases == [0x2800, 0x2C00]
    assert composed_viewports == [43]
