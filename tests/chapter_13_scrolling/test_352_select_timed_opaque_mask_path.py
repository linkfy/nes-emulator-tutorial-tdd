"""
Select timed opacity-mask composition only when one complete frame is available.

File to update:
    emulator/rendering/ppu_background_renderer.py

References:
    https://www.nesdev.org/wiki/PPU_rendering
    https://www.nesdev.org/wiki/PPU_scrolling

Why this step exists:
Step 351 built the mechanism for composing Boolean background-opacity rows from the
same timed states as RGB framebuffer rows. The public mask adapter must now activate
that mechanism without breaking startup or incomplete-frame behavior.

Selection boundary:

    exactly 240 completed states -> timed opacity-mask composition
    any other tuple length       -> existing t + fine-X snapshot fallback

This exact gate matches the framebuffer adapter. A truthiness check is insufficient
because a partial one-entry or 239-entry tuple is nonempty but cannot describe all
visible rows.

Why keep the fallback?
A new PPU starts with an empty completed tuple. The established snapshot path remains
a deterministic compatibility mechanism until the first complete timed frame is
published. It also contains the previously tested logical-pair and mirroring boundary.

Control flow:

    ppu_background_viewport_to_opaque_mask(ppu)
                         |
                         v
             completed length == 240?
                    /             \
                  yes              no
                   |                |
                   v                v
          timed mask helper   existing snapshot mask
                   |                |
                   +------ return --+

Important invariants:
    - exactly 240 entries select the timed helper
    - the timed branch returns immediately
    - old source-mask construction and full-frame composition do not also execute
    - empty, partial, and oversized tuples select the old fallback
    - fallback still reads ppu.temp_vram_addr and ppu.fine_x
    - framebuffer path and sprite-zero-hit code remain unchanged

Common misconception:
Do not catch errors from the timed helper and silently retry the fallback. The gate
handles expected data availability. Once a complete frame selects the timed helper,
an exception represents a violated invariant that should remain observable.

What changes in practice?
Console already uses this viewport-aware mask for sprite/background composition. RGB
and visual sprite priority can now use identical timed coordinates, correcting cases
such as a mushroom incorrectly appearing in front of an opaque tile. The separate
sprite-zero-hit helper still uses its older mask dependency and will be aligned in a
later lesson.

Out of scope:
    - changing timed row composition
    - changing the framebuffer gate
    - changing sprite-zero-hit mask consumption
    - full vertical source-row scrolling

Complete example implementation:

    # emulator/rendering/ppu_background_renderer.py

    def ppu_background_viewport_to_opaque_mask(
        ppu: PPU,
    ) -> BackgroundOpaqueMask:
        # --- NEW BLOCK: USE TIMED DATA ONLY FOR A COMPLETE FRAME ---
        if (
            len(ppu.completed_scanline_scroll_states)
            == NAMETABLE_PIXEL_HEIGHT
        ):
            return _timed_scanlines_to_opaque_mask(ppu)

        # Existing temp_vram_addr + fine_x fallback remains unchanged below.
        viewport_x, _ = decode_background_viewport_position(
            temp_vram_addr=ppu.temp_vram_addr,
            fine_x=ppu.fine_x,
        )
        ...
"""

import pytest


from emulator.ppu.ppu import BackgroundScanlineState, PPU
from emulator.rendering.background_viewport import NAMETABLE_PIXEL_HEIGHT
from emulator.rendering import ppu_background_renderer
from emulator.rendering.ppu_background_renderer import (
    ppu_background_viewport_to_opaque_mask,
)


def make_states(length: int) -> tuple[BackgroundScanlineState, ...]:
    """Create a tuple whose length controls only public path selection."""
    state = BackgroundScanlineState(vram_addr=0, fine_x=0)
    return (state,) * length


def forbidden_fallback_call(*args, **kwargs):
    """Fail if complete timed selection continues into old snapshot work."""
    raise AssertionError("Complete timed mask must not execute snapshot fallback")


def test_exactly_240_states_return_timed_mask_without_fallback(monkeypatch):
    """
    Objective:
    Activate the timed mask at its exact boundary and return its list unchanged.
    """
    ppu = PPU()
    ppu.completed_scanline_scroll_states = make_states(
        NAMETABLE_PIXEL_HEIGHT
    )
    expected = [True, False, True]
    timed_calls: list[PPU] = []

    def fake_timed_compositor(ppu_argument):
        timed_calls.append(ppu_argument)
        return expected

    monkeypatch.setattr(
        ppu_background_renderer,
        "_timed_scanlines_to_opaque_mask",
        fake_timed_compositor,
    )
    monkeypatch.setattr(
        ppu_background_renderer,
        "decode_background_viewport_position",
        forbidden_fallback_call,
    )
    monkeypatch.setattr(
        ppu_background_renderer,
        "ppu_background_to_opaque_mask",
        forbidden_fallback_call,
    )
    monkeypatch.setattr(
        ppu_background_renderer,
        "compose_horizontal_opaque_mask_viewport",
        forbidden_fallback_call,
    )

    result = ppu_background_viewport_to_opaque_mask(ppu)

    assert result is expected
    assert timed_calls == [ppu]


@pytest.mark.parametrize("noncomplete_length", [0, 1, 239, 241])
def test_noncomplete_tuples_use_existing_mask_fallback(
    monkeypatch,
    noncomplete_length,
):
    """
    Objective:
    Preserve deterministic startup and incomplete-frame mask behavior.
    """
    ppu = PPU()
    ppu.completed_scanline_scroll_states = make_states(noncomplete_length)
    ppu.temp_vram_addr = (1 << 11) | 5
    ppu.fine_x = 3

    expected = [True, False]
    source = [False, True]
    rendered_bases: list[int] = []
    decoded_arguments: list[tuple[int, int]] = []
    composed_viewports: list[int] = []

    def forbidden_timed_call(*args, **kwargs):
        raise AssertionError("Incomplete frame must not use timed mask composition")

    def fake_decode(*, temp_vram_addr, fine_x):
        decoded_arguments.append((temp_vram_addr, fine_x))
        return 43, 0


    def fake_build_one(ppu_argument, base_nametable_addr):
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
        "_timed_scanlines_to_opaque_mask",
        forbidden_timed_call,
    )
    monkeypatch.setattr(
        ppu_background_renderer,
        "decode_background_viewport_position",
        fake_decode,
    )
    monkeypatch.setattr(
        ppu_background_renderer,
        "ppu_background_to_opaque_mask",
        fake_build_one,
    )
    monkeypatch.setattr(
        ppu_background_renderer,
        "compose_horizontal_opaque_mask_viewport",
        fake_compose,
    )

    result = ppu_background_viewport_to_opaque_mask(ppu)

    assert result is expected
    assert decoded_arguments == [(ppu.temp_vram_addr, ppu.fine_x)]
    assert rendered_bases == [0x2800, 0x2C00]
    assert composed_viewports == [43]
