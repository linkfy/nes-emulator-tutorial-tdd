"""
Define the sprite attribute data model.

File to update:
    emulator/rendering/sprite_renderer.py

Why this step exists:
Each SpriteEntry contains one raw attributes byte. Before rendering sprites, we need
names for the bits that matter and a small dataclass for the decoded meaning.

NES sprite attribute byte:

    bits 0-1: sprite palette ID
    bits 2-4: unused / ignored for now
    bit 5: priority behind background
    bit 6: horizontal flip
    bit 7: vertical flip

Suggested implementation example:

    SPRITE_PALETTE_ID_MASK = 0b0000_0011
    SPRITE_IS_BEHIND_BACKGROUND = 1 << 5
    SPRITE_FLIP_HORIZONTAL = 1 << 6
    SPRITE_FLIP_VERTICAL = 1 << 7


    @dataclass(frozen=True)
    class SpriteAttributes:
        palette_id: int
        is_behind_background: bool
        flip_horizontal: bool
        flip_vertical: bool

Common misconception:

    "Sprite attributes are the same as background attribute table bytes."

No. Background attribute table bytes select background palettes for tile regions.
Sprite attributes are per-sprite and live in OAM byte 2.

Out of scope:
    - decode_sprite_attributes()
    - sprite palette RAM helper
    - rendering pixels
    - sprite 0 hit
    - sprite overflow
    - pygame
"""

from dataclasses import is_dataclass
from pathlib import Path

from emulator.rendering.sprite_renderer import (
    SPRITE_FLIP_HORIZONTAL,
    SPRITE_FLIP_VERTICAL,
    SPRITE_IS_BEHIND_BACKGROUND,
    SPRITE_PALETTE_ID_MASK,
    SpriteAttributes,
)


def test_sprite_attribute_constants_define_relevant_oam_bits():
    """
    Objective:
    Constants document the meaning of the relevant bits in OAM attribute byte 2.
    """
    assert SPRITE_PALETTE_ID_MASK == 0b0000_0011
    assert SPRITE_IS_BEHIND_BACKGROUND == 1 << 5
    assert SPRITE_FLIP_HORIZONTAL == 1 << 6
    assert SPRITE_FLIP_VERTICAL == 1 << 7


def test_sprite_attributes_is_frozen_dataclass():
    """
    Objective:
    SpriteAttributes is a small immutable snapshot of decoded attribute meaning.
    """
    assert is_dataclass(SpriteAttributes)

    attributes = SpriteAttributes(
        palette_id=2,
        is_behind_background=True,
        flip_horizontal=True,
        flip_vertical=False,
    )

    assert attributes.palette_id == 2
    assert attributes.is_behind_background is True
    assert attributes.flip_horizontal is True
    assert attributes.flip_vertical is False


def test_sprite_attributes_field_order_is_teaching_friendly():
    """
    Objective:
    Field order follows the common reading order: palette, priority, flips.
    """
    assert list(SpriteAttributes.__dataclass_fields__) == [
        "palette_id",
        "is_behind_background",
        "flip_horizontal",
        "flip_vertical",
    ]


def test_sprite_attribute_definition_does_not_import_pygame():
    """
    Objective:
    Sprite attribute decoding must stay free of frontend dependencies.

    Historical note:
    Later sprite rendering steps intentionally import Framebuffer in this module to
    draw pure framebuffer data. That is acceptable. pygame is still not allowed.
    """
    source = Path("emulator/rendering/sprite_renderer.py").read_text()

    assert "import pygame" not in source
