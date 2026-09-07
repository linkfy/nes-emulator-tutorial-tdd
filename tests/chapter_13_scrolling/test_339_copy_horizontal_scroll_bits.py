"""
Copy horizontal scrolling fields from temporary address t into current address v.

File to update:
    emulator/ppu/ppu.py

References:
    https://www.nesdev.org/wiki/PPU_scrolling#During_rendering
    https://www.nesdev.org/wiki/PPU_scrolling#At_dot_257_of_each_scanline

Why this step exists:
CPU writes prepare scrolling fields in temporary address t, but background rendering
uses current address v. The PPU transfers only the horizontal fields at the horizontal
reload point:

    yyy NN YYYYY XXXXX
        ||       +++++-- coarse X: bits 0-4
        |+-------------- horizontal nametable: bit 10
        +--------------- vertical nametable: bit 11, not copied here

Horizontal mask:

    0b000_01_00000_11111 = 0x041F

Required result:

    coarse X                    <- t
    horizontal nametable       <- t
    coarse Y                    <- original v
    fine Y                      <- original v
    vertical nametable         <- original v
    every other unrelated bit  <- original v

Minimal example:

    v: coarse X 3,  horizontal nametable 0, vertical state A
    t: coarse X 20, horizontal nametable 1, vertical state B

    result: coarse X 20, horizontal nametable 1, vertical state A

Common misconception:
The horizontal reload is not `v = t`. Copying all of t would replace vertical state
at the wrong time. A later step will apply this already-tested operation at dot 257.

Out of scope:
    - modifying PPU.step()
    - dot-257 timing
    - horizontal address increments
    - vertical t-to-v copies
    - framebuffer rendering

Complete example implementation:

    # emulator/ppu/ppu.py

    # --- NEW LINE: COARSE X AND HORIZONTAL NAMETABLE FIELDS ---
    HORIZONTAL_SCROLL_BITS = 0b000_01_00000_11111


    # --- NEW BLOCK: PURE HORIZONTAL t-TO-v COPY ---
    def copy_horizontal_scroll_bits(
        vram_addr: int,
        temp_vram_addr: int,
    ) -> int:
        return (
            (vram_addr & ~HORIZONTAL_SCROLL_BITS)
            | (temp_vram_addr & HORIZONTAL_SCROLL_BITS)
        )
"""

import pytest

from emulator.ppu.ppu import (
    HORIZONTAL_SCROLL_BITS,
    PPU,
    copy_horizontal_scroll_bits,
)


COARSE_X_MASK = 0x001F
HORIZONTAL_NAMETABLE_BIT = 0x0400
VERTICAL_FIELDS_MASK = 0x7BE0


def test_horizontal_scroll_mask_selects_coarse_x_and_bit_10_only():
    """
    Objective:
    Prevent accidentally selecting vertical nametable bit 11 instead of horizontal
    nametable bit 10.
    """
    assert HORIZONTAL_SCROLL_BITS == 0x041F
    assert HORIZONTAL_SCROLL_BITS & COARSE_X_MASK == COARSE_X_MASK
    assert HORIZONTAL_SCROLL_BITS & HORIZONTAL_NAMETABLE_BIT
    assert (HORIZONTAL_SCROLL_BITS & 0x0800) == 0


@pytest.mark.parametrize("coarse_x", [0, 1, 15, 30, 31])
@pytest.mark.parametrize("nametable_x", [0, 1])
def test_copy_uses_horizontal_fields_from_temp_address(coarse_x, nametable_x):
    """
    Objective:
    Copy representative coarse-X values and both logical horizontal nametables from t.
    """
    vram_addr = HORIZONTAL_NAMETABLE_BIT | 7
    temp_vram_addr = coarse_x | (nametable_x << 10)

    result = copy_horizontal_scroll_bits(vram_addr, temp_vram_addr)

    assert result & COARSE_X_MASK == coarse_x
    assert (result & HORIZONTAL_NAMETABLE_BIT) == (nametable_x << 10)


def test_copy_preserves_vertical_fields_from_current_address():
    """
    Objective:
    The horizontal reload must not import coarse Y, fine Y, or vertical nametable from
    temporary address t.
    """
    vertical_v = 0x7BE0
    horizontal_t = HORIZONTAL_NAMETABLE_BIT | 20
    vram_addr = vertical_v | 3
    temp_vram_addr = horizontal_t

    result = copy_horizontal_scroll_bits(vram_addr, temp_vram_addr)

    assert result & VERTICAL_FIELDS_MASK == vertical_v
    assert result & HORIZONTAL_SCROLL_BITS == horizontal_t


def test_copy_ignores_vertical_fields_present_in_temp_address():
    """
    Objective:
    Vertical bits in t remain deferred to the later vertical reload operation.
    """
    vram_addr = 0x0020
    temp_vram_addr = VERTICAL_FIELDS_MASK | HORIZONTAL_NAMETABLE_BIT | 12

    result = copy_horizontal_scroll_bits(vram_addr, temp_vram_addr)

    assert result & VERTICAL_FIELDS_MASK == vram_addr & VERTICAL_FIELDS_MASK
    assert result & HORIZONTAL_SCROLL_BITS == HORIZONTAL_NAMETABLE_BIT | 12


def test_copy_preserves_unrelated_high_bits_from_current_address():
    """
    Objective:
    Preserve internal address bits outside both named horizontal fields.
    """
    vram_addr = 0x8000 | VERTICAL_FIELDS_MASK
    temp_vram_addr = HORIZONTAL_NAMETABLE_BIT | 31

    result = copy_horizontal_scroll_bits(vram_addr, temp_vram_addr)

    assert result & 0x8000


def test_helper_is_pure_and_does_not_mutate_ppu_addresses():
    """
    Objective:
    Keep field-copy arithmetic independent before introducing timing behavior.
    """
    ppu = PPU()
    ppu.vram_addr = 3
    ppu.temp_vram_addr = HORIZONTAL_NAMETABLE_BIT | 20

    result = copy_horizontal_scroll_bits(
        ppu.vram_addr,
        ppu.temp_vram_addr,
    )

    assert result & HORIZONTAL_SCROLL_BITS == HORIZONTAL_NAMETABLE_BIT | 20
    assert ppu.vram_addr == 3
    assert ppu.temp_vram_addr == HORIZONTAL_NAMETABLE_BIT | 20
