"""
Increment the horizontal component of the current rendering address v.

File to update:
    emulator/ppu/ppu.py

References:
    https://www.nesdev.org/wiki/PPU_scrolling#Coarse_X_increment
    https://www.nesdev.org/wiki/PPU_scrolling#During_rendering

Why this step exists:
During background fetches, the PPU advances through one 8-pixel tile column at a
time. The current rendering address v stores both the coarse X tile column and the
horizontal nametable selection:

    v: yyy NN YYYYY XXXXX
                       |
                       +-- coarse X, bits 0-4

    horizontal nametable selection: bit 10

Normal behavior:

    coarse X 0  -> 1
    coarse X 30 -> 31

Boundary behavior:

    coarse X 31, horizontal nametable 0
        -> coarse X 0, horizontal nametable 1

    coarse X 31, horizontal nametable 1
        -> coarse X 0, horizontal nametable 0

The boundary toggle moves rendering across the logical left/right nametable seam.
PpuBus later applies cartridge mirroring when those logical addresses are read.

Important invariants:
    - only coarse X and, at wrapping, horizontal nametable may change
    - coarse Y, fine Y, and vertical nametable remain unchanged
    - fine X is separate and is not an argument to this operation
    - the helper returns a value and does not mutate PPU

Common misconception:
This does not move one pixel. It advances one tile column, which represents 8 pixels.
Fine X supplies the separate 0-7 pixel offset inside the first tile.

Out of scope:
    - calling the helper from PPU.step()
    - choosing background-fetch dots
    - copying horizontal t bits into v
    - vertical increments
    - framebuffer rendering

Complete example implementation:

    # emulator/ppu/ppu.py

    # --- NEW BLOCK: PURE HORIZONTAL v INCREMENT ---
    def increment_horizontal_vram_addr(vram_addr: int) -> int:
        # Advance v by one background tile column.
        coarse_x = vram_addr & 0b1_1111

        if coarse_x == 31:
            vram_addr &= ~0b1_1111
            vram_addr ^= 0b100_0000_0000
            return vram_addr

        return vram_addr + 1
"""

import pytest

from emulator.ppu.ppu import PPU, increment_horizontal_vram_addr


COARSE_X_MASK = 0x001F
HORIZONTAL_NAMETABLE_BIT = 0x0400
HORIZONTAL_FIELDS_MASK = COARSE_X_MASK | HORIZONTAL_NAMETABLE_BIT


@pytest.mark.parametrize("coarse_x", range(31))
def test_normal_increment_advances_only_coarse_x(coarse_x):
    """
    Objective:
    Coarse X values 0-30 increment without changing the selected nametable.
    """
    preserved_fields = 0x7BE0 | 0x8000
    original = preserved_fields | HORIZONTAL_NAMETABLE_BIT | coarse_x

    result = increment_horizontal_vram_addr(original)

    assert result & COARSE_X_MASK == coarse_x + 1
    assert result & HORIZONTAL_NAMETABLE_BIT
    assert result & ~HORIZONTAL_FIELDS_MASK == original & ~HORIZONTAL_FIELDS_MASK


def test_coarse_x_31_wraps_to_zero_and_selects_right_nametable():
    """
    Objective:
    Crossing the right edge of logical nametable X=0 continues at logical nametable
    X=1.
    """
    original = 31

    result = increment_horizontal_vram_addr(original)

    assert result & COARSE_X_MASK == 0
    assert result & HORIZONTAL_NAMETABLE_BIT


def test_coarse_x_31_wraps_to_zero_and_selects_left_nametable():
    """
    Objective:
    Crossing the right edge of logical nametable X=1 wraps around to logical
    nametable X=0.
    """
    original = HORIZONTAL_NAMETABLE_BIT | 31

    result = increment_horizontal_vram_addr(original)

    assert result & COARSE_X_MASK == 0
    assert (result & HORIZONTAL_NAMETABLE_BIT) == 0


def test_wrapping_preserves_every_non_horizontal_field():
    """
    Objective:
    Horizontal wrapping must not silently damage vertical scrolling or unrelated
    internal address bits.
    """
    preserved_fields = 0x7BE0 | 0x8000
    original = preserved_fields | HORIZONTAL_NAMETABLE_BIT | 31

    result = increment_horizontal_vram_addr(original)

    assert result & ~HORIZONTAL_FIELDS_MASK == original & ~HORIZONTAL_FIELDS_MASK


def test_helper_is_pure_and_does_not_mutate_ppu_vram_addr():
    """
    Objective:
    Keep address arithmetic independently testable before timing integration.
    """
    ppu = PPU()
    ppu.vram_addr = 14

    result = increment_horizontal_vram_addr(ppu.vram_addr)

    assert result == 15
    assert ppu.vram_addr == 14
