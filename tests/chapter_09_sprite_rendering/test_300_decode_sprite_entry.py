"""
Decode one sprite entry from OAM bytes.

File to update:
    emulator/rendering/sprite_renderer.py

Why this step exists:
The previous step defined SpriteEntry. Now we add the small decoder that converts
raw PPU OAM bytes into one SpriteEntry.

Raw OAM layout:

    sprite 0 -> bytes 0, 1, 2, 3
    sprite 1 -> bytes 4, 5, 6, 7
    ...
    sprite 63 -> bytes 252, 253, 254, 255

Suggested implementation example:

    def decode_sprite_entry(oam: bytes | bytearray, sprite_index: int) -> SpriteEntry:
        if len(oam) < OAM_SIZE:
            raise ValueError("OAM must contain 256 bytes")

        if not 0 <= sprite_index < OAM_SPRITE_COUNT:
            raise ValueError("sprite_index must be in range 0..63")

        base = sprite_index * BYTES_PER_SPRITE

        return SpriteEntry(
            y=oam[base],
            tile_index=oam[base + 1],
            attributes=oam[base + 2],
            x=oam[base + 3],
        )

Important NES detail:
The raw Y byte has special rendering semantics on real hardware. Sprites appear one
scanline below the stored Y value. Do not adjust it in this decoder. This function
returns raw OAM data only.

Out of scope:
    - sprite attribute bit decoding
    - sprite palettes
    - rendering pixels
    - sprite 0 hit
    - sprite overflow
    - pygame
"""

import pytest

from emulator.rendering.sprite_renderer import SpriteEntry, decode_sprite_entry


def test_decode_sprite_entry_reads_sprite_zero_bytes_in_oam_order():
    """
    Objective:
    Sprite index 0 reads OAM bytes 0..3 as y, tile_index, attributes, x.
    """
    oam = bytearray(256)
    oam[0:4] = bytes([12, 34, 0b1010_0001, 56])

    entry = decode_sprite_entry(oam, 0)

    assert entry == SpriteEntry(
        y=12,
        tile_index=34,
        attributes=0b1010_0001,
        x=56,
    )


def test_decode_sprite_entry_reads_sprite_one_from_next_four_bytes():
    """
    Objective:
    Sprite index 1 starts at byte 4, not byte 1.
    """
    oam = bytearray(256)
    oam[4:8] = bytes([20, 21, 22, 23])

    entry = decode_sprite_entry(oam, 1)

    assert entry == SpriteEntry(y=20, tile_index=21, attributes=22, x=23)


def test_decode_sprite_entry_reads_last_valid_sprite():
    """
    Objective:
    Sprite index 63 is the last valid sprite and reads bytes 252..255.
    """
    oam = bytearray(256)
    oam[252:256] = bytes([1, 2, 3, 4])

    entry = decode_sprite_entry(oam, 63)

    assert entry == SpriteEntry(y=1, tile_index=2, attributes=3, x=4)


def test_decode_sprite_entry_accepts_immutable_bytes_as_oam_source():
    """
    Objective:
    The decoder can read from bytes or bytearray because it only observes OAM data.
    """
    oam = bytearray(256)
    oam[8:12] = bytes([7, 8, 9, 10])

    entry = decode_sprite_entry(bytes(oam), 2)

    assert entry == SpriteEntry(y=7, tile_index=8, attributes=9, x=10)


def test_decode_sprite_entry_rejects_short_oam():
    """
    Objective:
    The decoder should fail clearly if it is not given a full 256-byte OAM buffer.
    """
    with pytest.raises(ValueError, match="OAM must contain 256 bytes"):
        decode_sprite_entry(bytearray(255), 0)


def test_decode_sprite_entry_rejects_invalid_sprite_indexes():
    """
    Objective:
    Valid sprite indexes are 0 through 63 inclusive.
    """
    oam = bytearray(256)

    with pytest.raises(ValueError, match="sprite_index must be in range 0..63"):
        decode_sprite_entry(oam, -1)

    with pytest.raises(ValueError, match="sprite_index must be in range 0..63"):
        decode_sprite_entry(oam, 64)
