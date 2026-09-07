"""
Decode a raw sprite attributes byte.

File to update:
    emulator/rendering/sprite_renderer.py

Why this step exists:
The previous step defined SpriteAttributes. Now we convert the raw OAM attribute
byte into that decoded structure.

Suggested implementation example:

    def decode_sprite_attributes(attributes: int) -> SpriteAttributes:
        attributes &= 0xFF

        return SpriteAttributes(
            palette_id=attributes & SPRITE_PALETTE_ID_MASK,
            is_behind_background=(attributes & SPRITE_IS_BEHIND_BACKGROUND) != 0,
            flip_horizontal=(attributes & SPRITE_FLIP_HORIZONTAL) != 0,
            flip_vertical=(attributes & SPRITE_FLIP_VERTICAL) != 0,
        )

Example:

    attributes = 0b1110_0011

Means:

    palette_id = 3
    is_behind_background = True
    flip_horizontal = True
    flip_vertical = True

Bits 2-4:
Ignored for now. Do not raise if they are set.

Out of scope:
    - sprite palette RAM helper
    - rendering pixels
    - sprite 0 hit
    - sprite overflow
    - pygame
"""

from emulator.rendering.sprite_renderer import SpriteAttributes, decode_sprite_attributes


def test_decode_sprite_attributes_extracts_palette_id_0_to_3():
    """
    Objective:
    Bits 0-1 select one of four sprite palettes.
    """
    assert decode_sprite_attributes(0b0000_0000).palette_id == 0
    assert decode_sprite_attributes(0b0000_0001).palette_id == 1
    assert decode_sprite_attributes(0b0000_0010).palette_id == 2
    assert decode_sprite_attributes(0b0000_0011).palette_id == 3


def test_decode_sprite_attributes_detects_priority_behind_background_bit():
    """
    Objective:
    Bit 5 marks the sprite as behind background pixels for later compositing.
    """
    assert decode_sprite_attributes(0b0000_0000).is_behind_background is False
    assert decode_sprite_attributes(0b0010_0000).is_behind_background is True


def test_decode_sprite_attributes_detects_horizontal_and_vertical_flip_bits():
    """
    Objective:
    Bit 6 controls horizontal flip and bit 7 controls vertical flip.
    """
    no_flip = decode_sprite_attributes(0b0000_0000)
    horizontal = decode_sprite_attributes(0b0100_0000)
    vertical = decode_sprite_attributes(0b1000_0000)
    both = decode_sprite_attributes(0b1100_0000)

    assert no_flip.flip_horizontal is False
    assert no_flip.flip_vertical is False

    assert horizontal.flip_horizontal is True
    assert horizontal.flip_vertical is False

    assert vertical.flip_horizontal is False
    assert vertical.flip_vertical is True

    assert both.flip_horizontal is True
    assert both.flip_vertical is True


def test_decode_sprite_attributes_decodes_all_relevant_bits_together():
    """
    Objective:
    A realistic attribute byte can combine palette, priority, and flip bits.
    """
    decoded = decode_sprite_attributes(0b1110_0011)

    assert decoded == SpriteAttributes(
        palette_id=3,
        is_behind_background=True,
        flip_horizontal=True,
        flip_vertical=True,
    )


def test_decode_sprite_attributes_ignores_bits_2_to_4():
    """
    Objective:
    Bits 2-4 are ignored for now. They should not affect decoded fields.
    """
    decoded = decode_sprite_attributes(0b0001_1100)

    assert decoded == SpriteAttributes(
        palette_id=0,
        is_behind_background=False,
        flip_horizontal=False,
        flip_vertical=False,
    )


def test_decode_sprite_attributes_masks_input_to_one_byte():
    """
    Objective:
    The decoder treats input as an 8-bit hardware register value.
    """
    decoded = decode_sprite_attributes(0x1C3)

    assert decoded == decode_sprite_attributes(0xC3)
