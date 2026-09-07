"""
Copy vertical scrolling fields from temporary address t into current address v.

File to update:
    emulator/ppu/ppu.py

References:
    https://www.nesdev.org/wiki/PPU_scrolling#During_dots_280_to_304_of_the_pre-render_scanline_(end_of_vblank)

Why this step exists:
CPU writes prepare vertical scrolling fields in temporary address t, while rendering
uses current address v. During the pre-render scanline, the PPU selectively refreshes
the vertical fields:

    yyy NN YYYYY XXXXX
    ||| |  |||||
    ||| |  +++++-- coarse Y: bits 5-9
    ||| +--------- vertical nametable: bit 11
    +++----------- fine Y: bits 12-14

Vertical mask:

    0b111_10_11111_00000 = 0x7BE0

Required result:

    fine Y                       <- t
    vertical nametable           <- t
    coarse Y                     <- t
    coarse X                     <- original v
    horizontal nametable         <- original v
    every other unrelated bit    <- original v

Minimal example:

    v: horizontal state A, vertical state B
    t: horizontal state C, vertical state D

    result: horizontal state A, vertical state D

Common misconception:
The vertical reload is not `v = t`. Copying all of t would overwrite horizontal state
after it was independently prepared by the horizontal reload.

Out of scope:
    - modifying PPU.step()
    - dot-256 vertical increment
    - pre-render dots 280-304
    - scanline state recording
    - framebuffer rendering

Complete example implementation:

    # emulator/ppu/ppu.py

    # --- NEW LINE: FINE Y, VERTICAL NAMETABLE, AND COARSE Y ---
    VERTICAL_SCROLL_BITS = 0b111_10_11111_00000


    # --- NEW BLOCK: PURE VERTICAL t-TO-v COPY ---
    def copy_vertical_scroll_bits(
        vram_addr: int,
        temp_vram_addr: int,
    ) -> int:
        return (
            (vram_addr & ~VERTICAL_SCROLL_BITS)
            | (temp_vram_addr & VERTICAL_SCROLL_BITS)
        )
"""

import pytest

from emulator.ppu.ppu import (
    HORIZONTAL_SCROLL_BITS,
    PPU,
    VERTICAL_SCROLL_BITS,
    copy_vertical_scroll_bits,
)


FINE_Y_MASK = 0x7000
VERTICAL_NAMETABLE_BIT = 0x0800
HORIZONTAL_NAMETABLE_BIT = 0x0400
COARSE_Y_MASK = 0x03E0
COARSE_X_MASK = 0x001F


def make_vertical_fields(
    *,
    fine_y: int,
    nametable_y: int,
    coarse_y: int,
) -> int:
    """Pack only the vertical scrolling fields used by this operation."""
    return (
        ((fine_y & 0b111) << 12)
        | ((nametable_y & 1) << 11)
        | ((coarse_y & 0b1_1111) << 5)
    )


def test_vertical_scroll_mask_selects_only_vertical_fields():
    """
    Objective:
    Select fine Y, vertical nametable, and coarse Y without selecting horizontal
    nametable bit 10 or coarse X.
    """
    assert VERTICAL_SCROLL_BITS == 0x7BE0
    assert VERTICAL_SCROLL_BITS & FINE_Y_MASK == FINE_Y_MASK
    assert VERTICAL_SCROLL_BITS & VERTICAL_NAMETABLE_BIT
    assert VERTICAL_SCROLL_BITS & COARSE_Y_MASK == COARSE_Y_MASK
    assert (VERTICAL_SCROLL_BITS & HORIZONTAL_NAMETABLE_BIT) == 0
    assert (VERTICAL_SCROLL_BITS & COARSE_X_MASK) == 0


@pytest.mark.parametrize(
    ("fine_y", "nametable_y", "coarse_y"),
    [
        (0, 0, 0),
        (3, 1, 12),
        (7, 0, 29),
        (6, 1, 31),
    ],
)
def test_copy_uses_all_vertical_fields_from_temp_address(
    fine_y,
    nametable_y,
    coarse_y,
):
    """
    Objective:
    Copy representative values across the complete packed vertical state.
    """
    vram_addr = HORIZONTAL_NAMETABLE_BIT | 17
    temp_vertical = make_vertical_fields(
        fine_y=fine_y,
        nametable_y=nametable_y,
        coarse_y=coarse_y,
    )

    result = copy_vertical_scroll_bits(vram_addr, temp_vertical)

    assert result & VERTICAL_SCROLL_BITS == temp_vertical


def test_copy_preserves_horizontal_fields_from_current_address():
    """
    Objective:
    Keep coarse X and horizontal nametable from v while replacing vertical fields.
    """
    horizontal_v = HORIZONTAL_NAMETABLE_BIT | 23
    vram_addr = horizontal_v | make_vertical_fields(
        fine_y=1,
        nametable_y=0,
        coarse_y=2,
    )
    temp_vram_addr = make_vertical_fields(
        fine_y=6,
        nametable_y=1,
        coarse_y=28,
    )

    result = copy_vertical_scroll_bits(vram_addr, temp_vram_addr)

    assert result & HORIZONTAL_SCROLL_BITS == horizontal_v
    assert result & VERTICAL_SCROLL_BITS == temp_vram_addr


def test_copy_ignores_horizontal_fields_present_in_temp_address():
    """
    Objective:
    Horizontal values in t must remain deferred to the horizontal reload operation.
    """
    horizontal_v = HORIZONTAL_NAMETABLE_BIT | 5
    temp_horizontal = 30
    temp_vertical = make_vertical_fields(
        fine_y=4,
        nametable_y=1,
        coarse_y=10,
    )

    result = copy_vertical_scroll_bits(
        horizontal_v,
        temp_vertical | temp_horizontal,
    )

    assert result & HORIZONTAL_SCROLL_BITS == horizontal_v
    assert result & VERTICAL_SCROLL_BITS == temp_vertical


def test_copy_preserves_unrelated_high_bit_from_current_address():
    """
    Objective:
    Preserve internal bits outside the named vertical scrolling fields.
    """
    vram_addr = 0x8000 | HORIZONTAL_NAMETABLE_BIT | 7
    temp_vram_addr = make_vertical_fields(
        fine_y=7,
        nametable_y=1,
        coarse_y=31,
    )

    result = copy_vertical_scroll_bits(vram_addr, temp_vram_addr)

    assert result & 0x8000


def test_helper_is_pure_and_does_not_mutate_ppu_addresses():
    """
    Objective:
    Keep vertical field arithmetic independent before timing integration.
    """
    ppu = PPU()
    ppu.vram_addr = HORIZONTAL_NAMETABLE_BIT | 7
    ppu.temp_vram_addr = make_vertical_fields(
        fine_y=5,
        nametable_y=1,
        coarse_y=20,
    )

    original_v = ppu.vram_addr
    original_t = ppu.temp_vram_addr
    result = copy_vertical_scroll_bits(
        ppu.vram_addr,
        ppu.temp_vram_addr,
    )

    assert result & VERTICAL_SCROLL_BITS == original_t
    assert ppu.vram_addr == original_v
    assert ppu.temp_vram_addr == original_t
