"""
Reverse one horizontal background-fetch increment on a copied address.

File to update:
    emulator/ppu/ppu.py

References:
    https://www.nesdev.org/wiki/PPU_scrolling#Details

Why this step exists:
Dots 321-336 prefetch the first two background tiles for the next scanline. Each tile
fetch advances horizontal v, so at dot 1 the address is already two tile columns ahead
of the pixels stored in the background shifters:

    intended visible coarse X = 5
    prefetch tile 5 -> v advances to 6
    prefetch tile 6 -> v advances to 7

    dot 1:
        shifters begin displaying tile 5
        v already contains coarse X 7

Later scanline recording will copy v and rewind that copy twice:

    7 -> 6 -> 5

This helper reverses one increment. It is not a timed PPU operation, and it must never
move the real PPU.vram_addr backward.

Normal behavior:

    coarse X 31 -> 30
    coarse X 7  -> 6
    coarse X 1  -> 0

Boundary behavior:

    coarse X 0 -> 31 and toggle horizontal nametable

Important invariants:
    - only coarse X and, at wrapping, horizontal nametable may change
    - every vertical and unrelated field remains unchanged
    - decrement is the inverse of the tested horizontal increment
    - the function is pure and does not mutate PPU

Common misconception:
The NES PPU does not perform this decrement during rendering. It exists only to
translate the ahead-of-display fetch address into a visible viewport address for the
existing high-level renderer.

Out of scope:
    - calling the helper from PPU.step()
    - recording 240 scanline positions
    - framebuffer or opacity-mask changes

Complete example implementation:

    # emulator/ppu/ppu.py

    # --- NEW BLOCK: REVERSE ONE HORIZONTAL FETCH INCREMENT ---
    def decrement_horizontal_vram_addr(vram_addr: int) -> int:
        coarse_x = vram_addr & 0b1_1111

        if coarse_x == 0:
            vram_addr = (
                (vram_addr & ~0b1_1111)
                | 0b1_1111
            )
            vram_addr ^= 0b000_01_00000_00000
            return vram_addr

        return vram_addr - 1
"""

import pytest

from emulator.ppu.ppu import (
    HORIZONTAL_SCROLL_BITS,
    PPU,
    decrement_horizontal_vram_addr,
    increment_horizontal_vram_addr,
)


COARSE_X_MASK = 0x001F
HORIZONTAL_NAMETABLE_BIT = 0x0400


@pytest.mark.parametrize("coarse_x", range(1, 32))
@pytest.mark.parametrize("nametable_x", [0, 1])
def test_nonzero_coarse_x_decrements_without_changing_nametable(
    coarse_x,
    nametable_x,
):
    """
    Objective:
    Reverse ordinary horizontal fetch increments without borrowing into other fields.
    """
    vertical_fields = 0x7BE0
    original = vertical_fields | (nametable_x << 10) | coarse_x

    result = decrement_horizontal_vram_addr(original)

    assert result & COARSE_X_MASK == coarse_x - 1
    assert result & HORIZONTAL_NAMETABLE_BIT == nametable_x << 10
    assert result & ~HORIZONTAL_SCROLL_BITS == original & ~HORIZONTAL_SCROLL_BITS


@pytest.mark.parametrize("nametable_x", [0, 1])
def test_coarse_x_zero_wraps_to_31_and_toggles_horizontal_nametable(
    nametable_x,
):
    """
    Objective:
    Reverse a fetch increment that crossed a logical horizontal nametable boundary.
    """
    vertical_fields = 0x7BE0
    original = vertical_fields | (nametable_x << 10)

    result = decrement_horizontal_vram_addr(original)

    assert result & COARSE_X_MASK == 31
    assert result & HORIZONTAL_NAMETABLE_BIT == (nametable_x ^ 1) << 10
    assert result & ~HORIZONTAL_SCROLL_BITS == original & ~HORIZONTAL_SCROLL_BITS


@pytest.mark.parametrize("coarse_x", range(32))
@pytest.mark.parametrize("nametable_x", [0, 1])
def test_decrement_reverses_horizontal_increment(coarse_x, nametable_x):
    """
    Objective:
    Prove the rewind operation is the inverse of one previously tested fetch increment.
    """
    original = 0x7BE0 | (nametable_x << 10) | coarse_x

    incremented = increment_horizontal_vram_addr(original)
    restored = decrement_horizontal_vram_addr(incremented)

    assert restored == original


@pytest.mark.parametrize("coarse_x", range(32))
@pytest.mark.parametrize("nametable_x", [0, 1])
def test_increment_reverses_horizontal_decrement(coarse_x, nametable_x):
    """
    Objective:
    Check the inverse relationship in the opposite operation order as well.
    """
    original = 0x7BE0 | (nametable_x << 10) | coarse_x

    decremented = decrement_horizontal_vram_addr(original)
    restored = increment_horizontal_vram_addr(decremented)

    assert restored == original


def test_rewind_preserves_unrelated_high_bit():
    """
    Objective:
    Preserve internal fields outside coarse X and horizontal nametable selection.
    """
    original = 0x8000 | 0x7BE0

    result = decrement_horizontal_vram_addr(original)

    assert result & 0x8000
    assert result & 0x7BE0 == original & 0x7BE0


def test_helper_is_pure_and_does_not_mutate_ppu_vram_addr():
    """
    Objective:
    Rewind only a copied value rather than the PPU's active rendering address.
    """
    ppu = PPU()
    ppu.vram_addr = HORIZONTAL_NAMETABLE_BIT | 7

    result = decrement_horizontal_vram_addr(ppu.vram_addr)

    assert result & COARSE_X_MASK == 6
    assert ppu.vram_addr == HORIZONTAL_NAMETABLE_BIT | 7
