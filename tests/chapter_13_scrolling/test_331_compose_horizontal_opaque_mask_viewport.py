"""
Compose a scrolled opacity mask from two adjacent nametable masks.

File to update:
    emulator/rendering/background_viewport.py

Reference documentation:
    https://www.nesdev.org/wiki/PPU_scrolling
    https://www.nesdev.org/wiki/PPU_nametables

Existing flow:
    build_background_opaque_mask() converts one nametable into a 256x240 list[bool].
    Sprite priority and sprite-zero-hit detection index that mask using screen
    coordinates.

New behavior:
    This step does not replace the existing mask builder. It composes two already
    constructed masks into the same horizontal viewport introduced for framebuffers
    in Step 330.

Coordinate model:

    left mask:  logical X   0-255
    right mask: logical X 256-511

    logical X = (viewport X + screen X) modulo 512

For viewport X 200:

    screen X   0-55  <- left X 200-255
    screen X  56-255 <- right X   0-199

Invariants:
    - each source contains exactly 256 * 240 Boolean entries
    - the result is a new 256 * 240 entry list
    - source masks remain unchanged
    - Y rows do not move
    - mask mapping exactly matches framebuffer mapping

Common misconception:
The mask does not derive opacity from final RGB colors. It preserves whether the
original background pattern color index was nonzero.

Out of scope:
    - building a mask from CHR or nametable bytes
    - reading PPU memory
    - Console integration
    - sprite-zero-hit integration
    - vertical scrolling
    - pygame

Complete example implementation:

    # emulator/rendering/background_viewport.py

    from emulator.rendering.nametable_renderer import BackgroundOpaqueMask


    def compose_horizontal_opaque_mask_viewport(
        left: BackgroundOpaqueMask,
        right: BackgroundOpaqueMask,
        viewport_x: int,
    ) -> BackgroundOpaqueMask:
        expected_size = NAMETABLE_PIXEL_WIDTH * NAMETABLE_PIXEL_HEIGHT

        if len(left) != expected_size:
            raise ValueError(
                f"Left background opacity mask must contain {expected_size} entries"
            )

        if len(right) != expected_size:
            raise ValueError(
                f"Right background opacity mask must contain {expected_size} entries"
            )

        logical_width = NAMETABLE_PIXEL_WIDTH * 2
        result = [False] * expected_size

        for screen_y in range(NAMETABLE_PIXEL_HEIGHT):
            row_start = screen_y * NAMETABLE_PIXEL_WIDTH

            for screen_x in range(NAMETABLE_PIXEL_WIDTH):
                logical_x = (viewport_x + screen_x) % logical_width

                if logical_x < NAMETABLE_PIXEL_WIDTH:
                    source = left
                    source_x = logical_x
                else:
                    source = right
                    source_x = logical_x - NAMETABLE_PIXEL_WIDTH

                destination_index = row_start + screen_x
                source_index = row_start + source_x
                result[destination_index] = source[source_index]

        return result
"""

import pytest

from emulator.rendering.background_viewport import (
    NAMETABLE_PIXEL_HEIGHT,
    NAMETABLE_PIXEL_WIDTH,
    compose_horizontal_framebuffer_viewport,
    compose_horizontal_opaque_mask_viewport,
)
from emulator.rendering.framebuffer import BLACK, Framebuffer, RGBColor
from emulator.rendering.nametable_renderer import BackgroundOpaqueMask


MASK_SIZE = NAMETABLE_PIXEL_WIDTH * NAMETABLE_PIXEL_HEIGHT
OPAQUE_COLOR: RGBColor = (255, 255, 255)


def patterned_mask(offset: int) -> BackgroundOpaqueMask:
    """Create row- and column-sensitive Boolean data for mapping tests."""
    return [
        ((x * 3 + y * 5 + offset) % 7) < 3
        for y in range(NAMETABLE_PIXEL_HEIGHT)
        for x in range(NAMETABLE_PIXEL_WIDTH)
    ]


def mask_to_framebuffer(mask: BackgroundOpaqueMask) -> Framebuffer:
    """Represent mask entries as colors so both viewport mappings can be compared."""
    return Framebuffer(
        width=NAMETABLE_PIXEL_WIDTH,
        height=NAMETABLE_PIXEL_HEIGHT,
        pixels=[OPAQUE_COLOR if value else BLACK for value in mask],
    )


def test_viewport_at_zero_uses_the_entire_left_mask():
    """
    Objective:
    With no horizontal offset, the visible opacity data is the left mask.
    """
    left = patterned_mask(offset=0)
    right = patterned_mask(offset=1)

    result = compose_horizontal_opaque_mask_viewport(left, right, viewport_x=0)

    assert result == left
    assert result is not left


def test_viewport_at_256_uses_the_entire_right_mask():
    """
    Objective:
    Logical X 256 begins at the first column of the right mask.
    """
    left = patterned_mask(offset=0)
    right = patterned_mask(offset=1)

    result = compose_horizontal_opaque_mask_viewport(left, right, viewport_x=256)

    assert result == right
    assert result is not right


def test_viewport_at_200_crosses_the_mask_seam_on_every_row():
    """
    Objective:
    Compose 56 columns from the left mask and 200 columns from the right mask while
    preserving every source Y row.
    """
    left = patterned_mask(offset=0)
    right = patterned_mask(offset=1)

    result = compose_horizontal_opaque_mask_viewport(left, right, viewport_x=200)

    expected: BackgroundOpaqueMask = []
    for y in range(NAMETABLE_PIXEL_HEIGHT):
        row_start = y * NAMETABLE_PIXEL_WIDTH
        row_end = row_start + NAMETABLE_PIXEL_WIDTH
        expected.extend(left[row_start + 200:row_end])
        expected.extend(right[row_start:row_start + 200])

    assert result == expected


def test_viewport_wraps_from_right_mask_back_to_left_mask():
    """
    Objective:
    A viewport beginning at logical X 300 consumes 212 right columns and then wraps
    to 44 left columns.
    """
    left = patterned_mask(offset=0)
    right = patterned_mask(offset=1)

    result = compose_horizontal_opaque_mask_viewport(left, right, viewport_x=300)

    expected: BackgroundOpaqueMask = []
    for y in range(NAMETABLE_PIXEL_HEIGHT):
        row_start = y * NAMETABLE_PIXEL_WIDTH
        row_end = row_start + NAMETABLE_PIXEL_WIDTH
        expected.extend(right[row_start + 44:row_end])
        expected.extend(left[row_start:row_start + 44])

    assert result == expected


def test_composition_does_not_mutate_source_masks():
    """
    Objective:
    Preserve source masks so framebuffer rendering, sprite priority, and hit detection
    can reuse deterministic source data.
    """
    left = patterned_mask(offset=0)
    right = patterned_mask(offset=1)
    left_before = list(left)
    right_before = list(right)

    result = compose_horizontal_opaque_mask_viewport(left, right, viewport_x=200)

    assert left == left_before
    assert right == right_before
    assert result is not left
    assert result is not right


def test_mask_and_framebuffer_compositors_use_identical_mapping():
    """
    Objective:
    Prevent visual background pixels from drifting away from the opacity information
    used for sprite priority and sprite-zero-hit decisions.
    """
    left_mask = patterned_mask(offset=0)
    right_mask = patterned_mask(offset=1)
    left_framebuffer = mask_to_framebuffer(left_mask)
    right_framebuffer = mask_to_framebuffer(right_mask)

    composed_mask = compose_horizontal_opaque_mask_viewport(
        left_mask,
        right_mask,
        viewport_x=200,
    )
    composed_framebuffer = compose_horizontal_framebuffer_viewport(
        left_framebuffer,
        right_framebuffer,
        viewport_x=200,
    )

    opacity_derived_from_pixels = [
        color == OPAQUE_COLOR
        for color in composed_framebuffer.pixels
    ]

    assert composed_mask == opacity_derived_from_pixels


def test_rejects_left_mask_with_wrong_entry_count():
    """
    Objective:
    Detect malformed left masks at the boundary rather than during coordinate lookup.
    """
    left = [False] * (MASK_SIZE - 1)
    right = [False] * MASK_SIZE

    with pytest.raises(ValueError, match="Left background opacity mask"):
        compose_horizontal_opaque_mask_viewport(left, right, viewport_x=0)


def test_rejects_right_mask_with_wrong_entry_count():
    """
    Objective:
    Apply the same fixed-size invariant to the right source mask.
    """
    left = [False] * MASK_SIZE
    right = [False] * (MASK_SIZE + 1)

    with pytest.raises(ValueError, match="Right background opacity mask"):
        compose_horizontal_opaque_mask_viewport(left, right, viewport_x=0)
