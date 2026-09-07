"""
Compose one framebuffer from 240 completed timed scanline states.

File to update:
    emulator/rendering/ppu_background_renderer.py

References:
    https://www.nesdev.org/wiki/PPU_rendering
    https://www.nesdev.org/wiki/PPU_scrolling

Why this step exists:
The completed frame can contain a different horizontal viewport position for every
visible row. A single end-of-frame t snapshot cannot represent both a fixed status
area and a moving gameplay area, so the high-level renderer must compose each row
from its matching BackgroundScanlineState.

For each destination row:

    state = completed_scanline_scroll_states[screen_y]
    left_base, right_base = logical pair selected by state
    viewport_x = horizontal pixel position decoded from state

For each destination pixel:

    logical_x = (viewport_x + screen_x) % 512

    logical X 0-255:   read the left source framebuffer
    logical X 256-511: read the right source framebuffer after subtracting 256

The source row remains screen_y for this horizontal milestone. Full vertical
source-row selection is separate future work.

Why cache source pairs?
Rows can have different viewport X values while reading the same two nametables.
Rendering both complete source nametables again for every row would perform as many
as 480 source renders. A local dictionary instead stores each logical pair once for
this composition:

    $2000 key -> rendered ($2000, $2400) pair
    $2800 key -> rendered ($2800, $2C00) pair

The cache is intentionally local. Nametable, pattern, attribute, or palette data may
change before a later frame, so cross-frame caching would require explicit and
error-prone invalidation rules.

Important invariants:
    - input contains exactly 240 completed states
    - output dimensions are exactly 256x240
    - state index, destination row, and source row are the same screen_y
    - every destination row receives exactly 256 pixels
    - horizontal selection wraps across the 512-pixel logical pair
    - each logical source pair is rendered at most once per composition
    - viewport X changes do not invalidate or duplicate a cached pair
    - cartridge mirroring remains PpuBus behavior inside source rendering

Common misconception:
Do not invoke the existing full-frame horizontal viewport compositor once per row.
That would construct 240 temporary 256x240 framebuffers to retain only one row from
each. This helper writes each destination row directly into one result framebuffer.

Testing strategy:
These tests replace nametable rendering with synthetic source framebuffers whose RGB
tuples encode logical base, source X, and source Y. This isolates row-composition
mechanics from pattern decoding, palette selection, PPU memory, and mirroring.

Out of scope:
    - changing the public viewport adapter
    - fallback behavior for an unavailable timed frame
    - opacity-mask composition
    - full vertical source-row scrolling
    - persistent rendering caches

Complete example implementation:

    # emulator/rendering/ppu_background_renderer.py

    # --- UPDATED LINES: IMPORT FRAMEBUFFER DIMENSIONS ---
    from emulator.rendering.background_viewport import (
        NAMETABLE_PIXEL_HEIGHT,
        NAMETABLE_PIXEL_WIDTH,
        ...
    )

    # --- NEW BLOCK: COMPOSE COMPLETED TIMED SCANLINES ---
    def _timed_scanlines_to_framebuffer(ppu: PPU) -> Framebuffer:
        states = ppu.completed_scanline_scroll_states

        if len(states) != NAMETABLE_PIXEL_HEIGHT:
            raise ValueError(
                "Timed framebuffer requires exactly 240 scanline states"
            )

        result = Framebuffer(
            width=NAMETABLE_PIXEL_WIDTH,
            height=NAMETABLE_PIXEL_HEIGHT,
        )
        pair_cache: dict[int, tuple[Framebuffer, Framebuffer]] = {}
        logical_width = NAMETABLE_PIXEL_WIDTH * 2

        for screen_y, state in enumerate(states):
            left_base, right_base = _scanline_horizontal_pair(state)

            if left_base not in pair_cache:
                pair_cache[left_base] = (
                    ppu_background_to_framebuffer(
                        ppu,
                        base_nametable_addr=left_base,
                    ),
                    ppu_background_to_framebuffer(
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
                result.pixels[destination_index] = source.pixels[source_index]

        return result
"""

from collections import Counter

import pytest

from emulator.ppu.ppu import BackgroundScanlineState, PPU
from emulator.rendering.background_viewport import (
    NAMETABLE_PIXEL_HEIGHT,
    NAMETABLE_PIXEL_WIDTH,
)
from emulator.rendering.framebuffer import BLACK, Framebuffer
from emulator.rendering import ppu_background_renderer
from emulator.rendering.ppu_background_renderer import (
    _timed_scanlines_to_framebuffer,
)


SOURCE_TAGS = {
    0x2000: 1,
    0x2400: 2,
    0x2800: 3,
    0x2C00: 4,
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


def make_source_framebuffer(base_nametable_addr: int) -> Framebuffer:
    """Encode source base, X, and Y in every synthetic RGB pixel."""
    tag = SOURCE_TAGS[base_nametable_addr]
    pixels = [
        (tag, source_x, source_y)
        for source_y in range(NAMETABLE_PIXEL_HEIGHT)
        for source_x in range(NAMETABLE_PIXEL_WIDTH)
    ]
    return Framebuffer(
        width=NAMETABLE_PIXEL_WIDTH,
        height=NAMETABLE_PIXEL_HEIGHT,
        pixels=pixels,
    )


def install_fake_source_renderer(monkeypatch):
    """Return a call log while replacing PPU memory rendering with pure test data."""
    calls: list[int] = []

    def fake_renderer(ppu, base_nametable_addr=0x2000):
        calls.append(base_nametable_addr)
        return make_source_framebuffer(base_nametable_addr)

    monkeypatch.setattr(
        ppu_background_renderer,
        "ppu_background_to_framebuffer",
        fake_renderer,
    )
    return calls


@pytest.mark.parametrize("wrong_length", [0, 1, 239, 241])
def test_timed_compositor_requires_exactly_240_states(wrong_length):
    """
    Objective:
    Fail explicitly instead of returning a silently partial or oversized framebuffer.
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
        _timed_scanlines_to_framebuffer(ppu)


def test_result_has_nes_dimensions_and_populates_every_pixel(monkeypatch):
    """
    Objective:
    Produce one complete framebuffer rather than sparse row fragments.
    """
    install_fake_source_renderer(monkeypatch)
    ppu = PPU()
    ppu.completed_scanline_scroll_states = tuple(
        make_state(0)
        for _ in range(NAMETABLE_PIXEL_HEIGHT)
    )

    result = _timed_scanlines_to_framebuffer(ppu)

    assert result.width == NAMETABLE_PIXEL_WIDTH
    assert result.height == NAMETABLE_PIXEL_HEIGHT
    assert len(result.pixels) == NAMETABLE_PIXEL_WIDTH * NAMETABLE_PIXEL_HEIGHT
    assert all(pixel != BLACK for pixel in result.pixels)


def test_each_output_row_uses_its_matching_recorded_state(monkeypatch):
    """
    Objective:
    Allow a fixed upper region and differently scrolled lower region in one frame.
    """
    install_fake_source_renderer(monkeypatch)
    ppu = PPU()
    ppu.completed_scanline_scroll_states = tuple(
        make_state(0 if screen_y < 32 else 40)
        for screen_y in range(NAMETABLE_PIXEL_HEIGHT)
    )

    result = _timed_scanlines_to_framebuffer(ppu)

    assert result.get_pixel(0, 0) == (1, 0, 0)
    assert result.get_pixel(0, 31) == (1, 0, 31)
    assert result.get_pixel(0, 32) == (1, 40, 32)
    assert result.get_pixel(0, 239) == (1, 40, 239)


def test_horizontal_selection_wraps_from_right_source_to_left(monkeypatch):
    """
    Objective:
    Wrap logical positions 510, 511, then 0 across the pair boundary.
    """
    install_fake_source_renderer(monkeypatch)
    ppu = PPU()
    ppu.completed_scanline_scroll_states = tuple(
        make_state(510)
        for _ in range(NAMETABLE_PIXEL_HEIGHT)
    )

    result = _timed_scanlines_to_framebuffer(ppu)

    assert result.get_pixel(0, 17) == (2, 254, 17)
    assert result.get_pixel(1, 17) == (2, 255, 17)
    assert result.get_pixel(2, 17) == (1, 0, 17)


def test_different_viewport_x_values_reuse_one_source_pair(monkeypatch):
    """
    Objective:
    Cache source images independently from each row's pixel-selection offset.
    """
    calls = install_fake_source_renderer(monkeypatch)
    ppu = PPU()
    ppu.completed_scanline_scroll_states = tuple(
        make_state((screen_y * 3) % 512)
        for screen_y in range(NAMETABLE_PIXEL_HEIGHT)
    )

    _timed_scanlines_to_framebuffer(ppu)

    assert Counter(calls) == Counter({0x2000: 1, 0x2400: 1})


def test_each_logical_pair_is_rendered_once_when_both_are_used(monkeypatch):
    """
    Objective:
    Bound source rendering to the two possible horizontal pairs in one composition.
    """
    calls = install_fake_source_renderer(monkeypatch)
    ppu = PPU()
    ppu.completed_scanline_scroll_states = tuple(
        make_state(
            viewport_x=0,
            nametable_y=0 if screen_y < 120 else 1,
        )
        for screen_y in range(NAMETABLE_PIXEL_HEIGHT)
    )

    result = _timed_scanlines_to_framebuffer(ppu)

    assert Counter(calls) == Counter(
        {
            0x2000: 1,
            0x2400: 1,
            0x2800: 1,
            0x2C00: 1,
        }
    )
    assert result.get_pixel(0, 119) == (1, 0, 119)
    assert result.get_pixel(0, 120) == (3, 0, 120)
