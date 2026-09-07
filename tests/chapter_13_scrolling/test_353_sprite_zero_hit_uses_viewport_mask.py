"""
Use viewport-aware background opacity for sprite-zero-hit overlap detection.

File to update:
    emulator/rendering/sprite_zero_hit.py

References:
    https://www.nesdev.org/wiki/PPU_rendering
    https://www.nesdev.org/wiki/PPU_scrolling

Why this step exists:
Sprite zero hit is a PPU status signal produced when an opaque pixel from OAM sprite
entry 0 overlaps an opaque background pixel. Games can poll this signal to time a
mid-frame register change, such as separating a fixed status area from scrolling
gameplay.

The overlap helper indexes background opacity using screen coordinates:

    mask_index = screen_y * 256 + screen_x

That mask must therefore describe the background actually visible at those same
coordinates. After timed scrolling, screen X may map to a different coarse-X column
or logical nametable on each row. The old fixed-$2000 mask can inspect a different
background pixel even though sprite 0 remains at the same screen position.

Example:

    sprite 0 screen X:       100
    scanline viewport X:      40
    visible background X:    140

    fixed mask inspects X:   100
    viewport mask inspects X: 140

If source X 140 is opaque and source X 100 is transparent, the fixed mask misses the
overlap. The viewport-aware adapter selects timed composition for a complete frame
and retains the previously tested snapshot fallback when timed data is unavailable.

Why use an import alias?
Historical sprite-zero-hit tests monkeypatch the module-local name
ppu_background_to_opaque_mask. Changing every call to a new local name would break
that stable testing seam. Importing the viewport-aware adapter under the historical
name changes production behavior while preserving old tests unchanged:

    new viewport-aware function as old module-local name

Important invariants:
    - sprite-zero-hit consumes the viewport-aware opacity adapter
    - the historical local dependency name remains monkeypatchable
    - the selected mask is passed unchanged to the pure overlap helper
    - sprite CHR pattern-table selection remains independent from background masking
    - rendering code does not set PPUSTATUS directly
    - Console and PPU timing continue scheduling and setting the hit

Common misconception:
Sprite zero hit is not gameplay collision detection and does not mean that Mario hit
an enemy or block. It is a rendering overlap involving only sprite entry 0 and an
opaque background pattern pixel, commonly used by software as a timing signal.

Testing strategy:
One test checks the production dependency identity so the old fixed producer cannot
silently return. Another follows a complete timed frame through the real viewport
adapter while replacing only its expensive row compositor, then verifies that the
resulting mask reaches the existing pure overlap boundary unchanged.

Out of scope:
    - changing the pure overlap search
    - changing sprite pattern-table selection
    - changing Console frame scheduling
    - exact left-edge, X=255, and OAM Y+1 hardware behavior
    - full vertical source-row scrolling

Complete example implementation:

    # emulator/rendering/sprite_zero_hit.py

    # --- UPDATED BLOCK: VIEWPORT MASK WITH HISTORICAL LOCAL NAME ---
    from emulator.rendering.ppu_background_renderer import (
        PATTERN_TABLE_0_ADDR,
        PATTERN_TABLE_1_ADDR,
        ppu_background_viewport_to_opaque_mask as ppu_background_to_opaque_mask,
    )

    ...
"""

from emulator.ppu.ppu import BackgroundScanlineState, PPU
from emulator.rendering import ppu_background_renderer
from emulator.rendering.ppu_background_renderer import (
    ppu_background_viewport_to_opaque_mask,
)
from emulator.rendering import sprite_zero_hit as sprite_zero_hit_module
from emulator.rendering.sprite_zero_hit import ppu_sprite_zero_hit_position


def make_complete_states() -> tuple[BackgroundScanlineState, ...]:
    """Publish enough immutable state to select the timed mask adapter branch."""
    state = BackgroundScanlineState(vram_addr=0, fine_x=0)
    return (state,) * 240


def test_historical_local_mask_name_resolves_to_viewport_aware_adapter():
    """
    Objective:
    Replace the fixed-$2000 production dependency without breaking the old local seam.
    """
    assert (
        sprite_zero_hit_module.ppu_background_to_opaque_mask
        is ppu_background_viewport_to_opaque_mask
    )


def test_complete_timed_mask_reaches_sprite_zero_overlap_helper_unchanged(
    monkeypatch,
):
    """
    Objective:
    Follow complete scanline evidence through the viewport adapter into hit detection.
    """
    ppu = PPU()
    ppu.completed_scanline_scroll_states = make_complete_states()
    expected_mask = [False, True, False]
    expected_position = (123, 45)
    timed_calls: list[PPU] = []
    captured = {}

    def fake_timed_mask(ppu_argument):
        timed_calls.append(ppu_argument)
        return expected_mask

    def fake_find_sprite_zero_hit_position(**kwargs):
        captured.update(kwargs)
        return expected_position

    monkeypatch.setattr(
        ppu_background_renderer,
        "_timed_scanlines_to_opaque_mask",
        fake_timed_mask,
    )
    monkeypatch.setattr(
        sprite_zero_hit_module,
        "find_sprite_zero_hit_position",
        fake_find_sprite_zero_hit_position,
    )

    result = ppu_sprite_zero_hit_position(ppu)

    assert result == expected_position
    assert timed_calls == [ppu]
    assert captured["background_opaque_mask"] is expected_mask
