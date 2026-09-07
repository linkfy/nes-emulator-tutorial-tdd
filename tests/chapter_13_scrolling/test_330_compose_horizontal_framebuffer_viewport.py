"""
Compose a 256x240 horizontal viewport from two adjacent nametable framebuffers.

File to update:
    emulator/rendering/background_viewport.py

Reference documentation:
    https://www.nesdev.org/wiki/PPU_scrolling
    https://www.nesdev.org/wiki/PPU_nametables

Why this step exists:
Each rendered nametable is 256 pixels wide, but horizontal scrolling can make one
screen contain pixels from two adjacent nametables. This step treats them as one
logical 512x240 background and selects a 256x240 viewport from it.

Coordinate model:

    left framebuffer:  logical X   0-255
    right framebuffer: logical X 256-511

For each destination screen X:

    logical X = (viewport X + screen X) modulo 512

The modulo operation wraps the right edge of the logical pair back to its left edge.

Example seam:

    viewport X = 200

    screen X   0-55  <- left X 200-255
    screen X  56-255 <- right X   0-199

Invariants:
    - both source framebuffers are exactly 256x240
    - the returned framebuffer is exactly 256x240
    - neither source framebuffer is mutated
    - every output pixel comes from the same Y row in one source framebuffer

Common misconception:
This function does not implement cartridge nametable mirroring. PpuBus owns address
mirroring; this function only composes already-rendered logical neighbors.

Out of scope:
    - vertical scrolling
    - background opacity-mask composition
    - PPU or PpuBus reads
    - nametable tile rendering
    - Console integration
    - pygame
    - exact dot-timed v/t transfers

Complete example implementation:

    # emulator/rendering/background_viewport.py

    from emulator.rendering.framebuffer import Framebuffer


    def compose_horizontal_framebuffer_viewport(
        left: Framebuffer,
        right: Framebuffer,
        viewport_x: int,
    ) -> Framebuffer:
        expected_size = (
            NAMETABLE_PIXEL_WIDTH,
            NAMETABLE_PIXEL_HEIGHT,
        )

        if (left.width, left.height) != expected_size:
            raise ValueError("Left nametable framebuffer must be 256x240")

        if (right.width, right.height) != expected_size:
            raise ValueError("Right nametable framebuffer must be 256x240")

        logical_width = NAMETABLE_PIXEL_WIDTH * 2
        result = Framebuffer(
            width=NAMETABLE_PIXEL_WIDTH,
            height=NAMETABLE_PIXEL_HEIGHT,
        )

        for screen_y in range(NAMETABLE_PIXEL_HEIGHT):
            for screen_x in range(NAMETABLE_PIXEL_WIDTH):
                logical_x = (viewport_x + screen_x) % logical_width

                if logical_x < NAMETABLE_PIXEL_WIDTH:
                    source = left
                    source_x = logical_x
                else:
                    source = right
                    source_x = logical_x - NAMETABLE_PIXEL_WIDTH

                color = source.get_pixel(source_x, screen_y)
                result.set_pixel(screen_x, screen_y, color)

        return result
"""

import pytest

from emulator.rendering.background_viewport import (
    NAMETABLE_PIXEL_HEIGHT,
    NAMETABLE_PIXEL_WIDTH,
    compose_horizontal_framebuffer_viewport,
)
from emulator.rendering.framebuffer import Framebuffer, RGBColor


LEFT_COLOR: RGBColor = (10, 20, 30)
RIGHT_COLOR: RGBColor = (40, 50, 60)


def solid_nametable_framebuffer(color: RGBColor) -> Framebuffer:
    """Create one rendered nametable whose source is easy to identify."""
    return Framebuffer(
        width=NAMETABLE_PIXEL_WIDTH,
        height=NAMETABLE_PIXEL_HEIGHT,
        pixels=[color] * (NAMETABLE_PIXEL_WIDTH * NAMETABLE_PIXEL_HEIGHT),
    )


def coordinate_nametable_framebuffer(source_id: int) -> Framebuffer:
    """Encode source identity and coordinates into each RGB pixel."""
    return Framebuffer(
        width=NAMETABLE_PIXEL_WIDTH,
        height=NAMETABLE_PIXEL_HEIGHT,
        pixels=[
            (source_id, x, y)
            for y in range(NAMETABLE_PIXEL_HEIGHT)
            for x in range(NAMETABLE_PIXEL_WIDTH)
        ],
    )


def test_viewport_at_zero_uses_the_entire_left_nametable():
    """
    Objective:
    With no horizontal offset, the visible screen is the left logical nametable.
    """
    left = solid_nametable_framebuffer(LEFT_COLOR)
    right = solid_nametable_framebuffer(RIGHT_COLOR)

    result = compose_horizontal_framebuffer_viewport(left, right, viewport_x=0)

    assert result.width == NAMETABLE_PIXEL_WIDTH
    assert result.height == NAMETABLE_PIXEL_HEIGHT
    assert result.pixels == left.pixels
    assert result is not left


def test_viewport_at_256_uses_the_entire_right_nametable():
    """
    Objective:
    Logical X 256 is the first pixel column of the right nametable.
    """
    left = solid_nametable_framebuffer(LEFT_COLOR)
    right = solid_nametable_framebuffer(RIGHT_COLOR)

    result = compose_horizontal_framebuffer_viewport(left, right, viewport_x=256)

    assert result.pixels == right.pixels
    assert result is not right


def test_viewport_at_200_crosses_the_nametable_seam_on_every_row():
    """
    Objective:
    Compose 56 columns from the end of the left nametable and 200 columns from the
    beginning of the right nametable without changing Y rows.
    """
    left = coordinate_nametable_framebuffer(source_id=1)
    right = coordinate_nametable_framebuffer(source_id=2)

    result = compose_horizontal_framebuffer_viewport(left, right, viewport_x=200)

    expected_pixels: list[RGBColor] = []
    for y in range(NAMETABLE_PIXEL_HEIGHT):
        row_start = y * NAMETABLE_PIXEL_WIDTH
        row_end = row_start + NAMETABLE_PIXEL_WIDTH
        expected_pixels.extend(left.pixels[row_start + 200:row_end])
        expected_pixels.extend(right.pixels[row_start:row_start + 200])

    assert result.pixels == expected_pixels


def test_viewport_wraps_from_right_nametable_back_to_left():
    """
    Objective:
    A viewport beginning at logical X 300 consumes 212 right-hand columns before
    wrapping to 44 columns from the left nametable.
    """
    left = coordinate_nametable_framebuffer(source_id=1)
    right = coordinate_nametable_framebuffer(source_id=2)

    result = compose_horizontal_framebuffer_viewport(left, right, viewport_x=300)

    assert result.get_pixel(0, 0) == right.get_pixel(44, 0)
    assert result.get_pixel(211, 0) == right.get_pixel(255, 0)
    assert result.get_pixel(212, 0) == left.get_pixel(0, 0)
    assert result.get_pixel(255, 239) == left.get_pixel(43, 239)


def test_composition_does_not_mutate_either_source_framebuffer():
    """
    Objective:
    Keep viewport composition pure so source nametables can be reused and failures
    remain local to the returned framebuffer.
    """
    left = coordinate_nametable_framebuffer(source_id=1)
    right = coordinate_nametable_framebuffer(source_id=2)
    left_before = list(left.pixels)
    right_before = list(right.pixels)

    result = compose_horizontal_framebuffer_viewport(left, right, viewport_x=200)

    assert left.pixels == left_before
    assert right.pixels == right_before
    assert result is not left
    assert result is not right


def test_rejects_left_framebuffer_with_wrong_dimensions():
    """
    Objective:
    Reject an invalid left source at the function boundary instead of failing during
    pixel indexing.
    """
    left = Framebuffer(width=255, height=240)
    right = solid_nametable_framebuffer(RIGHT_COLOR)

    with pytest.raises(ValueError, match="Left nametable framebuffer"):
        compose_horizontal_framebuffer_viewport(left, right, viewport_x=0)


def test_rejects_right_framebuffer_with_wrong_dimensions():
    """
    Objective:
    Apply the same explicit dimension invariant to the right source.
    """
    left = solid_nametable_framebuffer(LEFT_COLOR)
    right = Framebuffer(width=256, height=239)

    with pytest.raises(ValueError, match="Right nametable framebuffer"):
        compose_horizontal_framebuffer_viewport(left, right, viewport_x=0)
