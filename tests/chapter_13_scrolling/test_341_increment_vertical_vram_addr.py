"""
Increment the vertical component of current rendering address v.

File to update:
    emulator/ppu/ppu.py

References:
    https://www.nesdev.org/wiki/PPU_scrolling#Y_increment
    https://www.nesdev.org/wiki/PPU_scrolling#Wrapping_around

Why this step exists:
At dot 256, the PPU advances the rendering address by one pixel row. Unlike the
horizontal increment, vertical movement first advances fine Y inside the current
8-pixel tile:

    yyy NN YYYYY XXXXX
    +++    +++++
     |       +---- coarse Y: bits 5-9
     +------------ fine Y: bits 12-14

    vertical nametable: bit 11

Fine-Y behavior:

    0 -> 1 -> 2 -> ... -> 7

When fine Y is already 7, it wraps to 0 and coarse Y advances.

Coarse-Y behavior after fine-Y wrapping:

    coarse Y 0-28 -> increment by one
    coarse Y 29   -> 0 and toggle vertical nametable
    coarse Y 30   -> 31 through the normal increment branch
    coarse Y 31   -> 0 without toggling vertical nametable

Rows 0-29 are the 30 visible tile rows of a nametable. Values 30 and 31 are not normal
visible rows, but they can exist because coarse Y is a five-bit field and CPU address
operations can load those values.

Why add $1000 for a normal fine-Y increment?
Fine Y begins at bit 12, so adding `1 << 12` increments that packed field by one. This
does not conceptually mean moving 4096 bytes through PPU memory.

Important invariants:
    - horizontal coarse X and nametable selection remain unchanged
    - unrelated internal address bits remain unchanged
    - vertical nametable toggles only for row-29 wrapping
    - the helper is pure and does not mutate PPU

Common misconception:
Vertical increment is not simply symmetrical with horizontal increment. Horizontal
movement advances one tile column; vertical movement advances one fine pixel row and
only sometimes advances the coarse tile row.

Out of scope:
    - calling this helper at dot 256
    - vertical t-to-v copying
    - pre-render timing
    - scanline viewport recording
    - framebuffer rendering

Complete example implementation:

    # emulator/ppu/ppu.py

    # --- NEW BLOCK: PURE VERTICAL v INCREMENT ---
    def increment_vertical_vram_addr(vram_addr: int) -> int:
        fine_y = (vram_addr >> 12) & 0b111

        if fine_y < 7:
            return vram_addr + (1 << 12)

        vram_addr &= ~0b111_00_00000_00000
        coarse_y = (vram_addr >> 5) & 0b1_1111

        if coarse_y == 29:
            coarse_y = 0
            vram_addr ^= 0b000_10_00000_00000
        elif coarse_y == 31:
            coarse_y = 0
        else:
            coarse_y += 1

        return (
            (vram_addr & ~0b000_00_11111_00000)
            | (coarse_y << 5)
        )
"""

import pytest

from emulator.ppu.ppu import PPU, increment_vertical_vram_addr


FINE_Y_MASK = 0x7000
COARSE_Y_MASK = 0x03E0
VERTICAL_NAMETABLE_BIT = 0x0800
VERTICAL_FIELDS_MASK = FINE_Y_MASK | COARSE_Y_MASK | VERTICAL_NAMETABLE_BIT
HORIZONTAL_FIELDS_MASK = 0x041F


def make_vram_addr(
    *,
    coarse_y: int,
    fine_y: int,
    nametable_y: int = 0,
    horizontal_fields: int = 0,
    unrelated_fields: int = 0,
) -> int:
    """Pack the fields needed for focused vertical-address tests."""
    return (
        ((fine_y & 0b111) << 12)
        | ((nametable_y & 1) << 11)
        | ((coarse_y & 0b1_1111) << 5)
        | (horizontal_fields & HORIZONTAL_FIELDS_MASK)
        | unrelated_fields
    )


@pytest.mark.parametrize("fine_y", range(7))
def test_fine_y_zero_through_six_increments_without_changing_coarse_y(fine_y):
    """
    Objective:
    Advance one pixel row inside the current tile before touching coarse Y.
    """
    original = make_vram_addr(
        coarse_y=12,
        fine_y=fine_y,
        nametable_y=1,
        horizontal_fields=0x0415,
        unrelated_fields=0x8000,
    )

    result = increment_vertical_vram_addr(original)

    assert (result & FINE_Y_MASK) >> 12 == fine_y + 1
    assert result & ~FINE_Y_MASK == original & ~FINE_Y_MASK


@pytest.mark.parametrize(
    ("coarse_y", "expected_coarse_y"),
    [
        (0, 1),
        (1, 2),
        (28, 29),
        (30, 31),
    ],
)
def test_fine_y_seven_wraps_and_normally_increments_coarse_y(
    coarse_y,
    expected_coarse_y,
):
    """
    Objective:
    Use the normal coarse-Y increment for every value except hardware-special rows 29
    and 31. This includes the representable out-of-range value 30.
    """
    original = make_vram_addr(
        coarse_y=coarse_y,
        fine_y=7,
        nametable_y=0,
        horizontal_fields=0x0412,
    )

    result = increment_vertical_vram_addr(original)

    assert (result & FINE_Y_MASK) == 0
    assert (result & COARSE_Y_MASK) >> 5 == expected_coarse_y
    assert (result & VERTICAL_NAMETABLE_BIT) == 0
    assert result & HORIZONTAL_FIELDS_MASK == original & HORIZONTAL_FIELDS_MASK


@pytest.mark.parametrize("starting_nametable_y", [0, 1])
def test_row_29_wraps_to_zero_and_toggles_vertical_nametable(
    starting_nametable_y,
):
    """
    Objective:
    Cross the normal 240-pixel nametable boundary after visible row 29.
    """
    original = make_vram_addr(
        coarse_y=29,
        fine_y=7,
        nametable_y=starting_nametable_y,
        horizontal_fields=0x0407,
    )

    result = increment_vertical_vram_addr(original)

    assert (result & FINE_Y_MASK) == 0
    assert (result & COARSE_Y_MASK) == 0
    assert (result & VERTICAL_NAMETABLE_BIT) == (
        (starting_nametable_y ^ 1) << 11
    )
    assert result & HORIZONTAL_FIELDS_MASK == original & HORIZONTAL_FIELDS_MASK


@pytest.mark.parametrize("starting_nametable_y", [0, 1])
def test_row_31_wraps_to_zero_without_toggling_vertical_nametable(
    starting_nametable_y,
):
    """
    Objective:
    Preserve the documented row-31 hardware rule independently of normal visible
    row-29 wrapping.
    """
    original = make_vram_addr(
        coarse_y=31,
        fine_y=7,
        nametable_y=starting_nametable_y,
        horizontal_fields=0x001F,
    )

    result = increment_vertical_vram_addr(original)

    assert (result & FINE_Y_MASK) == 0
    assert (result & COARSE_Y_MASK) == 0
    assert (result & VERTICAL_NAMETABLE_BIT) == (
        starting_nametable_y << 11
    )
    assert result & HORIZONTAL_FIELDS_MASK == original & HORIZONTAL_FIELDS_MASK


def test_vertical_increment_preserves_unrelated_high_bit():
    """
    Objective:
    Keep internal address bits outside the named vertical fields unchanged.
    """
    original = make_vram_addr(
        coarse_y=5,
        fine_y=7,
        unrelated_fields=0x8000,
    )

    result = increment_vertical_vram_addr(original)

    assert result & 0x8000


def test_helper_is_pure_and_does_not_mutate_ppu_vram_addr():
    """
    Objective:
    Keep vertical arithmetic independently testable before timing integration.
    """
    ppu = PPU()
    ppu.vram_addr = make_vram_addr(coarse_y=8, fine_y=3)

    result = increment_vertical_vram_addr(ppu.vram_addr)

    assert (result & FINE_Y_MASK) >> 12 == 4
    assert ppu.vram_addr == make_vram_addr(coarse_y=8, fine_y=3)
