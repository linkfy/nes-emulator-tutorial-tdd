"""
Compose one background opacity mask from 240 completed scanline states.

File to update:
    emulator/rendering/ppu_background_renderer.py

References:
    https://www.nesdev.org/wiki/PPU_rendering
    https://www.nesdev.org/wiki/PPU_scrolling

Why this step exists:
Timed framebuffer rows can show a fixed status area and a differently scrolled
gameplay area in one frame. Sprite priority and sprite-zero-hit decisions also need
background opacity at those exact screen coordinates. If RGB pixels use timed states
while opacity uses one final t snapshot, sprites can appear in front of solid tiles
that should occlude them.

A BackgroundOpaqueMask is a flat 256x240 list of Boolean values:

    True:  the decoded background pattern pixel is nonzero
    False: the decoded background pattern pixel is transparent

Opacity is pattern information, not an RGB-color test. A visible pattern pixel can
use a black palette color, while a transparent pattern pixel displays the universal
background color.

The mask compositor must mirror framebuffer coordinate selection exactly:

    state = completed_scanline_scroll_states[screen_y]
    logical_x = (viewport_x + screen_x) % 512

    logical X 0-255:   read the left source mask
    logical X 256-511: read the right source mask after subtracting 256

For this horizontal milestone, source Y remains screen_y.

Why cache source masks?
Viewport X may change on every scanline without changing the logical source pair.
The local cache builds each pair once per composition:

    $2000 key -> masks for ($2000, $2400)
    $2800 key -> masks for ($2800, $2C00)

Important invariants:
    - input contains exactly 240 completed states
    - output contains exactly 256 * 240 Boolean entries
    - state index, source row, and destination row use the same screen_y
    - horizontal coordinates wrap across the complete 512-pixel pair
    - each logical pair is built at most once per composition
    - viewport-X changes reuse the existing source pair
    - opacity-mask code never calls framebuffer rendering
    - framebuffer and opacity-mask coordinate mappings remain identical

Common misconception:
Do not derive this mask from rendered RGB values. Sprite priority depends on whether
the original background pattern value was zero, which cannot be reconstructed
reliably from its final palette color.

Testing strategy:
These tests replace PPU-backed mask construction with synthetic masks. Each Boolean
value is a deterministic function of logical base address, source X, and source Y.
That makes wrong pair selection, wrong row indexing, and horizontal-wrap errors
observable without involving CHR decoding, palettes, or cartridge mirroring.

Out of scope:
    - activating this helper in the public opacity-mask adapter
    - fallback selection for startup or incomplete frames
    - sprite-zero-hit integration
    - full vertical source-row scrolling

Complete example implementation (Very similar logic to _timed_scanlines_to_framebuffer):

    # emulator/rendering/ppu_background_renderer.py

    # --- NEW BLOCK: COMPOSE COMPLETED TIMED OPACITY ROWS ---
    def _timed_scanlines_to_opaque_mask(
        ppu: PPU,
    ) -> BackgroundOpaqueMask:
        states = ppu.completed_scanline_scroll_states

        if len(states) != NAMETABLE_PIXEL_HEIGHT:
            raise ValueError(
                "Timed opacity mask requires exactly 240 scanline states"
            )

        result: BackgroundOpaqueMask = [False] * (
            NAMETABLE_PIXEL_WIDTH * NAMETABLE_PIXEL_HEIGHT
        )
        pair_cache: dict[
            int,
            tuple[BackgroundOpaqueMask, BackgroundOpaqueMask],
        ] = {}
        logical_width = NAMETABLE_PIXEL_WIDTH * 2

        for screen_y, state in enumerate(states):
            left_base, right_base = _scanline_horizontal_pair(state)

            if left_base not in pair_cache:
                pair_cache[left_base] = (
                    ppu_background_to_opaque_mask(
                        ppu,
                        base_nametable_addr=left_base,
                    ),
                    ppu_background_to_opaque_mask(
                        ppu,
                        base_nametable_addr=right_base,
                    ),
                )

            left, right = pair_cache[left_base]
            viewport_x = _scanline_viewport_x(state)
            destination_row = screen_y * NAMETABLE_PIXEL_WIDTH

            for screen_x in range(NAMETABLE_PIXEL_WIDTH):
                logical_x = (viewport_x + screen_x) % logical_width

                if logical_x < NAMETABLE_PIXEL_WIDTH:
                    source = left
                    source_x = logical_x
                else:
                    source = right
                    source_x = logical_x - NAMETABLE_PIXEL_WIDTH

                destination_index = destination_row + screen_x
                source_index = destination_row + source_x
                result[destination_index] = source[source_index]

        return result
"""

from collections import Counter

import pytest

from emulator.ppu.ppu import BackgroundScanlineState, PPU
from emulator.rendering.background_viewport import (
    NAMETABLE_PIXEL_HEIGHT,
    NAMETABLE_PIXEL_WIDTH,
)
from emulator.rendering import ppu_background_renderer
from emulator.rendering.ppu_background_renderer import (
    _timed_scanlines_to_opaque_mask,
)


SOURCE_PHASES = {
    0x2000: 0,
    0x2400: 1,
    0x2800: 2,
    0x2C00: 3,
}


def make_state(
    viewport_x: int,
    *,
    nametable_y: int = 0,
) -> BackgroundScanlineState:
    """Encode horizontal pixel X and vertical pair selection into one state."""
    nametable_x, pair_x = divmod(viewport_x, NAMETABLE_PIXEL_WIDTH)
    coarse_x, fine_x = divmod(pair_x, 8)
    vram_addr = (
        coarse_x
        | ((nametable_x & 1) << 10)
        | ((nametable_y & 1) << 11)
    )
    return BackgroundScanlineState(vram_addr=vram_addr, fine_x=fine_x)


def source_value(
    base_nametable_addr: int,
    source_x: int,
    source_y: int,
) -> bool:
    """Produce distinguishable Boolean patterns for logical source coordinates."""
    phase = SOURCE_PHASES[base_nametable_addr]
    return (phase + source_x + source_y) % 5 in (0, 1)


def make_source_mask(base_nametable_addr: int) -> list[bool]:
    """Build one synthetic logical nametable mask."""
    return [
        source_value(base_nametable_addr, source_x, source_y)
        for source_y in range(NAMETABLE_PIXEL_HEIGHT)
        for source_x in range(NAMETABLE_PIXEL_WIDTH)
    ]


def install_fake_mask_renderer(monkeypatch):
    """Replace PPU-backed mask construction and return its logical-address call log."""
    calls: list[int] = []

    def fake_renderer(ppu, base_nametable_addr=0x2000):
        calls.append(base_nametable_addr)
        return make_source_mask(base_nametable_addr)

    monkeypatch.setattr(
        ppu_background_renderer,
        "ppu_background_to_opaque_mask",
        fake_renderer,
    )
    return calls


@pytest.mark.parametrize("wrong_length", [0, 1, 239, 241])
def test_timed_mask_compositor_requires_exactly_240_states(wrong_length):
    """
    Objective:
    Reject missing or oversized coordinate evidence instead of producing a partial mask.
    """
    ppu = PPU()
    ppu.completed_scanline_scroll_states = tuple(
        make_state(0)
        for _ in range(wrong_length)
    )

    with pytest.raises(
        ValueError,
        match="exactly 240 scanline states",
    ):
        _timed_scanlines_to_opaque_mask(ppu)


def test_result_contains_one_boolean_for_every_screen_pixel(monkeypatch):
    """
    Objective:
    Preserve the flat mask contract expected by sprite-priority consumers.
    """
    install_fake_mask_renderer(monkeypatch)
    ppu = PPU()
    ppu.completed_scanline_scroll_states = tuple(
        make_state(0)
        for _ in range(NAMETABLE_PIXEL_HEIGHT)
    )

    result = _timed_scanlines_to_opaque_mask(ppu)

    assert len(result) == NAMETABLE_PIXEL_WIDTH * NAMETABLE_PIXEL_HEIGHT
    assert all(isinstance(value, bool) for value in result)


def test_each_mask_row_uses_its_matching_recorded_state(monkeypatch):
    """
    Objective:
    Align opacity with a fixed upper area and a differently scrolled lower area.
    """
    install_fake_mask_renderer(monkeypatch)
    ppu = PPU()
    ppu.completed_scanline_scroll_states = tuple(
        make_state(0 if screen_y < 32 else 40)
        for screen_y in range(NAMETABLE_PIXEL_HEIGHT)
    )

    result = _timed_scanlines_to_opaque_mask(ppu)

    assert result[0 * NAMETABLE_PIXEL_WIDTH] == source_value(0x2000, 0, 0)
    assert result[31 * NAMETABLE_PIXEL_WIDTH] == source_value(0x2000, 0, 31)
    assert result[32 * NAMETABLE_PIXEL_WIDTH] == source_value(0x2000, 40, 32)
    assert result[239 * NAMETABLE_PIXEL_WIDTH] == source_value(0x2000, 40, 239)


def test_mask_selection_wraps_from_right_source_to_left(monkeypatch):
    """
    Objective:
    Match framebuffer wrapping across logical positions 510, 511, then 0.
    """
    install_fake_mask_renderer(monkeypatch)
    ppu = PPU()
    ppu.completed_scanline_scroll_states = tuple(
        make_state(510)
        for _ in range(NAMETABLE_PIXEL_HEIGHT)
    )

    result = _timed_scanlines_to_opaque_mask(ppu)
    row = 17 * NAMETABLE_PIXEL_WIDTH

    assert result[row] == source_value(0x2400, 254, 17)
    assert result[row + 1] == source_value(0x2400, 255, 17)
    assert result[row + 2] == source_value(0x2000, 0, 17)


def test_different_viewport_x_values_reuse_one_mask_pair(monkeypatch):
    """
    Objective:
    Keep per-row pixel selection independent from expensive source-mask construction.
    """
    calls = install_fake_mask_renderer(monkeypatch)
    ppu = PPU()
    ppu.completed_scanline_scroll_states = tuple(
        make_state((screen_y * 3) % 512)
        for screen_y in range(NAMETABLE_PIXEL_HEIGHT)
    )

    _timed_scanlines_to_opaque_mask(ppu)

    assert Counter(calls) == Counter({0x2000: 1, 0x2400: 1})


def test_each_logical_mask_pair_is_built_once_when_both_are_used(monkeypatch):
    """
    Objective:
    Bound source work while preserving vertical logical-pair selection per row.
    """
    calls = install_fake_mask_renderer(monkeypatch)
    ppu = PPU()
    ppu.completed_scanline_scroll_states = tuple(
        make_state(
            viewport_x=0,
            nametable_y=0 if screen_y < 120 else 1,
        )
        for screen_y in range(NAMETABLE_PIXEL_HEIGHT)
    )

    result = _timed_scanlines_to_opaque_mask(ppu)

    assert Counter(calls) == Counter(
        {
            0x2000: 1,
            0x2400: 1,
            0x2800: 1,
            0x2C00: 1,
        }
    )
    assert result[119 * NAMETABLE_PIXEL_WIDTH] == source_value(0x2000, 0, 119)
    assert result[120 * NAMETABLE_PIXEL_WIDTH] == source_value(0x2800, 0, 120)


def test_timed_mask_composition_never_renders_rgb_framebuffers(monkeypatch):
    """
    Objective:
    Keep Boolean opacity production independent from RGB rendering and palette colors.
    """
    install_fake_mask_renderer(monkeypatch)
    ppu = PPU()
    ppu.completed_scanline_scroll_states = tuple(
        make_state(0)
        for _ in range(NAMETABLE_PIXEL_HEIGHT)
    )

    def forbidden_framebuffer_call(*args, **kwargs):
        raise AssertionError("Opacity composition must not render RGB framebuffers")

    monkeypatch.setattr(
        ppu_background_renderer,
        "ppu_background_to_framebuffer",
        forbidden_framebuffer_call,
    )

    result = _timed_scanlines_to_opaque_mask(ppu)

    assert len(result) == NAMETABLE_PIXEL_WIDTH * NAMETABLE_PIXEL_HEIGHT
