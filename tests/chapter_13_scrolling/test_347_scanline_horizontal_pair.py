"""
Select the horizontal logical nametable pair for one recorded scanline.

File to update:
    emulator/rendering/ppu_background_renderer.py

References:
    https://www.nesdev.org/wiki/PPU_scrolling
    https://www.nesdev.org/wiki/PPU_nametables

Why this step exists:
The completed timed frame stores one effective vram_addr and fine X value for each
visible scanline. Before a later renderer can copy that scanline's pixels, it must
know which two horizontally adjacent logical nametables form the source pair.

The nametable-select fields inside vram_addr are:

    bit 10: horizontal nametable position inside a 512-pixel-wide pair
    bit 11: vertical nametable row that selects the pair

Pair selection therefore uses only bit 11:

    bit 11 clear: ($2000, $2400)
    bit 11 set:   ($2800, $2C00)

Intuitive model:

    upper logical row:  $2000 | $2400
    lower logical row:  $2800 | $2C00

The helper chooses one complete row. A later step will use bit 10, coarse X, and fine
X to choose the horizontal pixel position within that row.

Important invariants:
    - only vram_addr bit 11 affects the selected pair
    - bit 10 does not change the pair
    - coarse X, coarse Y, fine Y, and fine X do not change the pair
    - returned values are logical PPU nametable addresses
    - cartridge mirroring remains PpuBus behavior
    - the helper is pure and performs no rendering or memory access

Common misconception:
Bit 10 does not select between the upper and lower horizontal pairs. It identifies
the left or right horizontal nametable within the pair and will become part of the
viewport-X calculation in the next lesson.

Out of scope:
    - decoding horizontal viewport X
    - reading nametable or pattern-table bytes
    - applying cartridge mirroring
    - composing framebuffer rows
    - selecting completed timed data versus the old fallback

Complete example implementation:

    # emulator/rendering/ppu_background_renderer.py

    # --- UPDATED LINES: IMPORT THE RECORDED SCANLINE VALUE ---
    from emulator.ppu.ppu import (
        BackgroundScanlineState,
        CTRL_BACKGROUND_PATTERN_TABLE,
        PPU,
    )

    ...

    # --- NEW BLOCK: SELECT ONE SCANLINE'S LOGICAL HORIZONTAL PAIR ---
    def _scanline_horizontal_pair(
        state: BackgroundScanlineState,
    ) -> tuple[int, int]:
        nametable_y = (state.vram_addr >> 11) & 1
        left_base = BASE_NAMETABLE_ADDR + nametable_y * 0x0800

        return left_base, left_base + 0x0400
"""

import pytest

from emulator.ppu.ppu import BackgroundScanlineState
from emulator.rendering.ppu_background_renderer import _scanline_horizontal_pair


@pytest.mark.parametrize(
    ("nametable_y", "expected_pair"),
    [
        (0, (0x2000, 0x2400)),
        (1, (0x2800, 0x2C00)),
    ],
)
def test_vertical_nametable_bit_selects_logical_horizontal_pair(
    nametable_y,
    expected_pair,
):
    """
    Objective:
    Map each vertical logical nametable row to its two adjacent source addresses.
    """
    state = BackgroundScanlineState(
        vram_addr=nametable_y << 11,
        fine_x=0,
    )

    assert _scanline_horizontal_pair(state) == expected_pair


@pytest.mark.parametrize(
    ("nametable_y", "expected_pair"),
    [
        (0, (0x2000, 0x2400)),
        (1, (0x2800, 0x2C00)),
    ],
)
def test_horizontal_nametable_bit_does_not_change_selected_pair(
    nametable_y,
    expected_pair,
):
    """
    Objective:
    Keep bit 10 for later viewport-X decoding instead of treating it as pair choice.
    """
    left_state = BackgroundScanlineState(
        vram_addr=nametable_y << 11,
        fine_x=0,
    )
    right_state = BackgroundScanlineState(
        vram_addr=(nametable_y << 11) | (1 << 10),
        fine_x=0,
    )

    assert _scanline_horizontal_pair(left_state) == expected_pair
    assert _scanline_horizontal_pair(right_state) == expected_pair


@pytest.mark.parametrize(
    ("nametable_y", "expected_pair"),
    [
        (0, (0x2000, 0x2400)),
        (1, (0x2800, 0x2C00)),
    ],
)
def test_other_scroll_fields_do_not_affect_logical_pair(
    nametable_y,
    expected_pair,
):
    """
    Objective:
    Isolate pair selection from coarse position, fine position, and horizontal state.
    """
    noisy_vram_addr = (
        (7 << 12)       # fine Y
        | (nametable_y << 11)
        | (1 << 10)    # horizontal nametable
        | (29 << 5)    # coarse Y
        | 31           # coarse X
    )
    state = BackgroundScanlineState(
        vram_addr=noisy_vram_addr,
        fine_x=7,
    )

    assert _scanline_horizontal_pair(state) == expected_pair
