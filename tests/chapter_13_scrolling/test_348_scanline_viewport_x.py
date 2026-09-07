"""
Decode horizontal viewport X from one recorded scanline state.

File to update:
    emulator/rendering/ppu_background_renderer.py

Reference:
    https://www.nesdev.org/wiki/PPU_scrolling

Why this step exists:
Step 347 selected the two logical nametables that form a horizontal source pair. A
later row compositor also needs the exact pixel where this scanline begins inside
that 512-pixel-wide pair.

The recorded address uses the same packed scrolling layout as t:

    yyy NN YYYYY XXXXX

Horizontal viewport X uses:

    XXXXX          coarse X tile column
    low N bit      horizontal nametable selection, vram_addr bit 10
    state.fine_x   pixel offset inside the first tile

Pixel conversion:

    viewport_x = nametable_x * 256 + coarse_x * 8 + fine_x

Example:

    nametable X = 1
    coarse X    = 5
    fine X      = 3

    viewport X = 1 * 256 + 5 * 8 + 3 = 299

Why reuse decode_background_viewport_position?
The existing pure decoder already owns the packed scrolling-field conversion. Both
t and recorded v have the same bit layout, so repeating masks and dimensions in this
renderer would create two implementations that could drift apart.

Important invariants:
    - horizontal nametable bit 10 contributes 256 pixels
    - coarse X contributes eight pixels per tile
    - fine X contributes the final 0-7 pixel offset
    - vertical nametable, coarse Y, and fine Y do not affect viewport X
    - the result remains inside the logical horizontal range 0-511
    - the recorded address is not rewound again
    - the helper performs no rendering or memory access

Common misconception:
The recorded address does not need another two-tile correction. Step 345 already
rewound a copy of v twice before constructing BackgroundScanlineState. Repeating the
rewind here would incorrectly shift every rendered row sixteen pixels left.

Out of scope:
    - selecting logical nametable addresses
    - composing framebuffer rows
    - applying horizontal wrap to destination pixels
    - opacity-mask composition
    - choosing timed data versus the old frame-level fallback

Complete example implementation:

    # emulator/rendering/ppu_background_renderer.py

    # --- NEW BLOCK: DECODE ONE SCANLINE'S HORIZONTAL VIEWPORT ---
    def _scanline_viewport_x(state: BackgroundScanlineState) -> int:
        viewport_x, _ = decode_background_viewport_position(
            temp_vram_addr=state.vram_addr,
            fine_x=state.fine_x,
        )

        return viewport_x
"""

import pytest

from emulator.ppu.ppu import BackgroundScanlineState
from emulator.rendering.ppu_background_renderer import _scanline_viewport_x


def make_scanline_state(
    *,
    coarse_x: int = 0,
    coarse_y: int = 0,
    nametable_x: int = 0,
    nametable_y: int = 0,
    fine_y: int = 0,
    fine_x: int = 0,
) -> BackgroundScanlineState:
    """Pack scrolling fields into one immutable recorded scanline value."""
    vram_addr = (
        (coarse_x & 0b1_1111)
        | ((coarse_y & 0b1_1111) << 5)
        | ((nametable_x & 1) << 10)
        | ((nametable_y & 1) << 11)
        | ((fine_y & 0b111) << 12)
    )
    return BackgroundScanlineState(vram_addr=vram_addr, fine_x=fine_x)


def test_zero_recorded_scroll_starts_at_left_edge():
    """
    Objective:
    Establish the origin of the 512-pixel horizontal logical pair.
    """
    state = make_scanline_state()

    assert _scanline_viewport_x(state) == 0


@pytest.mark.parametrize("coarse_x", [0, 1, 5, 17, 31])
def test_coarse_x_converts_tile_columns_to_pixels(coarse_x):
    """
    Objective:
    Convert each selected tile column into its eight-pixel horizontal position.
    """
    state = make_scanline_state(coarse_x=coarse_x)

    assert _scanline_viewport_x(state) == coarse_x * 8


@pytest.mark.parametrize("fine_x", range(8))
def test_fine_x_adds_offset_inside_the_first_tile(fine_x):
    """
    Objective:
    Preserve pixel-level scrolling after coarse tile selection.
    """
    state = make_scanline_state(coarse_x=5, fine_x=fine_x)

    assert _scanline_viewport_x(state) == 40 + fine_x


def test_horizontal_nametable_bit_selects_right_half_of_logical_pair():
    """
    Objective:
    Include bit 10 as a 256-pixel offset rather than treating it as pair selection.
    """
    state = make_scanline_state(
        nametable_x=1,
        coarse_x=5,
        fine_x=3,
    )

    assert _scanline_viewport_x(state) == 299


def test_maximum_horizontal_fields_reach_last_logical_pixel():
    """
    Objective:
    Prove the complete horizontal state covers exactly pixel positions 0 through 511.
    """
    state = make_scanline_state(
        nametable_x=1,
        coarse_x=31,
        fine_x=7,
    )

    assert _scanline_viewport_x(state) == 511


def test_vertical_fields_do_not_change_horizontal_viewport_x():
    """
    Objective:
    Keep horizontal row positioning independent from vertical scrolling fields.
    """
    horizontal_only = make_scanline_state(
        nametable_x=1,
        coarse_x=9,
        fine_x=6,
    )
    with_vertical_fields = make_scanline_state(
        nametable_x=1,
        coarse_x=9,
        fine_x=6,
        nametable_y=1,
        coarse_y=29,
        fine_y=7,
    )

    assert _scanline_viewport_x(horizontal_only) == 334
    assert _scanline_viewport_x(with_vertical_fields) == 334
