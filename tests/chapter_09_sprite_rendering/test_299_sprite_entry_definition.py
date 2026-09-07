"""
Define the basic OAM sprite entry data model.

File to create:
    emulator/rendering/sprite_renderer.py

Why this step exists:
OAMDMA already copies 256 bytes into PPU.oam. Before rendering sprites, we need a
small data model for one sprite entry.

What is OAM?
OAM means Object Attribute Memory. It is the PPU's internal sprite memory:

    64 sprites * 4 bytes = 256 bytes

Each sprite entry uses four bytes:

    byte 0: Y position
    byte 1: tile index
    byte 2: attributes
    byte 3: X position

This first sprite-rendering step only creates constants and the SpriteEntry
dataclass. It does not decode from OAM yet and does not render pixels.

Suggested implementation example:

    from dataclasses import dataclass


    OAM_SPRITE_COUNT = 64
    BYTES_PER_SPRITE = 4
    OAM_SIZE = OAM_SPRITE_COUNT * BYTES_PER_SPRITE


    @dataclass(frozen=True)
    class SpriteEntry:
        y: int
        tile_index: int
        attributes: int
        x: int

Common misconception:

    "OAMDMA means sprites are visible."

No. OAMDMA only fills PPU.oam. Rendering those entries into pixels is a later
chapter 09 step.

Out of scope:
    - decode_sprite_entry()
    - sprite attribute bit decoding
    - sprite palettes
    - rendering pixels
    - sprite 0 hit
    - sprite overflow
    - pygame
"""

from dataclasses import is_dataclass
from pathlib import Path

from emulator.rendering.sprite_renderer import (
    BYTES_PER_SPRITE,
    OAM_SIZE,
    OAM_SPRITE_COUNT,
    SpriteEntry,
)


def test_sprite_renderer_file_exists():
    """
    Objective:
    Sprite rendering starts in a pure emulator rendering module.
    """
    assert Path("emulator/rendering/sprite_renderer.py").exists()


def test_oam_sprite_constants_define_standard_nes_oam_layout():
    """
    Objective:
    Constants document the standard NES sprite memory shape.
    """
    assert OAM_SPRITE_COUNT == 64
    assert BYTES_PER_SPRITE == 4
    assert OAM_SIZE == 256
    assert OAM_SIZE == OAM_SPRITE_COUNT * BYTES_PER_SPRITE


def test_sprite_entry_is_frozen_dataclass_snapshot():
    """
    Objective:
    SpriteEntry is a small immutable snapshot of four OAM bytes.
    """
    assert is_dataclass(SpriteEntry)

    entry = SpriteEntry(y=10, tile_index=20, attributes=30, x=40)

    assert entry.y == 10
    assert entry.tile_index == 20
    assert entry.attributes == 30
    assert entry.x == 40


def test_sprite_entry_field_order_matches_oam_byte_order():
    """
    Objective:
    The dataclass field order should match the raw OAM byte order:

        y, tile_index, attributes, x
    """
    assert list(SpriteEntry.__dataclass_fields__) == [
        "y",
        "tile_index",
        "attributes",
        "x",
    ]


def test_sprite_entry_definition_does_not_import_pygame():
    """
    Objective:
    The sprite renderer must stay free of frontend dependencies.

    Historical note:
    This test originally also checked that Framebuffer was not imported because the
    first sprite step was data-only. Later steps intentionally render one sprite
    into a pure Framebuffer, so Framebuffer is now allowed. pygame is still not
    allowed.
    """
    source = Path("emulator/rendering/sprite_renderer.py").read_text()

    assert "import pygame" not in source
