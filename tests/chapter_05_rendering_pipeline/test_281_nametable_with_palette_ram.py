"""
Render nametable background using attribute table and PPU palette RAM bytes.

File to update:
    emulator/rendering/nametable_renderer.py

Why this step exists:
The previous steps built the pieces separately:

    attribute table
        -> palette ID for each tile coordinate

    palette RAM bytes
        -> four RGB background palettes

    nametable + attributes + background palettes
        -> framebuffer

This step composes those pieces into one pure rendering helper:

    nametable_with_palette_ram_to_framebuffer(
        nametable_bytes,
        attribute_table,
        pattern_table_bytes,
        palette_ram,
    )

What it should do:

    background_palettes = build_background_palettes_from_palette_ram(palette_ram)

    return nametable_with_attributes_to_framebuffer(
        nametable_bytes,
        attribute_table,
        pattern_table_bytes,
        background_palettes,
    )

Why this is useful:
This helper accepts data shaped closer to real PPU rendering inputs while staying
fully testable:

    nametable visible tile bytes
    attribute table bytes
    pattern table CHR bytes
    background palette RAM bytes

Still pure data:
No PPU bus reads, no pygame, no window, no frame loop.

Important hardware model:

    CHR pixel color index 0-3
        -> attribute table selects background palette ID 0-3
        -> palette RAM selects NES color index $00-$3F
        -> NES RGB palette converts to RGB
        -> framebuffer pixel

Suggested implementation example:

    from emulator.rendering.palette_ram import build_background_palettes_from_palette_ram


    def nametable_with_palette_ram_to_framebuffer(
        nametable_bytes: bytes,
        attribute_table: bytes,
        pattern_table_bytes: bytes,
        palette_ram: bytes,
    ) -> Framebuffer:
        background_palettes = build_background_palettes_from_palette_ram(palette_ram)

        return nametable_with_attributes_to_framebuffer(
            nametable_bytes,
            attribute_table,
            pattern_table_bytes,
            background_palettes,
        )

Out of scope:
    - reading nametable/palette bytes from PPU bus
    - palette RAM mirroring
    - scrolling
    - sprites
    - OAMDMA
    - pygame display
"""

from emulator.ppu.chr_decoder import PATTERN_TABLE_SIZE
from emulator.rendering.attribute_table import TABLE_SIZE
from emulator.rendering.nametable_renderer import (
    NAMETABLE_SIZE,
    nametable_with_attributes_to_framebuffer,
    nametable_with_palette_ram_to_framebuffer,
)
from emulator.rendering.nes_palette import get_nes_rgb_color
from emulator.rendering.palette_ram import build_background_palettes_from_palette_ram


def pack_attribute_byte(
    topleft: int,
    topright: int,
    bottomleft: int,
    bottomright: int,
) -> int:
    """Pack four 2-bit palette IDs into one NES attribute byte."""
    return (
        (bottomright << 6)
        | (bottomleft << 4)
        | (topright << 2)
        | (topleft << 0)
    )


def make_empty_pattern_table() -> bytearray:
    """Create one synthetic 4096-byte pattern table."""
    return bytearray(PATTERN_TABLE_SIZE)


def make_empty_nametable() -> bytearray:
    """Create the visible 960-byte nametable tile-ID area."""
    return bytearray(NAMETABLE_SIZE)


def make_empty_attribute_table() -> bytearray:
    """Create one synthetic 64-byte attribute table."""
    return bytearray(TABLE_SIZE)


def make_background_palette_ram() -> bytes:
    """
    Create synthetic $3F00-$3F0F background palette RAM bytes.

    Values are NES color indexes, not RGB colors.
    """
    return bytes([
        0x0F, 0x01, 0x02, 0x03,
        0x04, 0x11, 0x12, 0x13,
        0x08, 0x21, 0x22, 0x23,
        0x0C, 0x31, 0x32, 0x33,
    ])


def set_tile_row_to_color_index(
    pattern_table: bytearray,
    tile_id: int,
    row: int,
    color_index: int,
) -> None:
    """Set one synthetic tile row to a constant CHR color index."""
    tile_offset = tile_id * 16
    low_bit = color_index & 0b01
    high_bit = (color_index >> 1) & 0b01

    pattern_table[tile_offset + row] = 0xFF if low_bit else 0x00
    pattern_table[tile_offset + 8 + row] = 0xFF if high_bit else 0x00


def test_nametable_with_palette_ram_to_framebuffer_function_exists():
    """
    Objective:
    Expose one pure helper for rendering background bytes using palette RAM bytes.
    """
    assert callable(nametable_with_palette_ram_to_framebuffer)


def test_nametable_with_palette_ram_returns_256_by_240_framebuffer():
    """
    Objective:
    The composed helper keeps the normal NES visible background dimensions.
    """
    framebuffer = nametable_with_palette_ram_to_framebuffer(
        bytes(make_empty_nametable()),
        bytes(make_empty_attribute_table()),
        bytes(make_empty_pattern_table()),
        make_background_palette_ram(),
    )

    assert framebuffer.width == 256
    assert framebuffer.height == 240
    assert len(framebuffer.pixels) == 256 * 240


def test_color_index_zero_uses_backdrop_color_from_palette_ram():
    """
    Objective:
    Empty CHR bytes decode to color index 0. Background color index 0 uses the
    shared backdrop color from palette RAM entry $3F00.
    """
    framebuffer = nametable_with_palette_ram_to_framebuffer(
        bytes(make_empty_nametable()),
        bytes(make_empty_attribute_table()),
        bytes(make_empty_pattern_table()),
        make_background_palette_ram(),
    )

    assert framebuffer.get_pixel(0, 0) == get_nes_rgb_color(0x0F)
    assert framebuffer.get_pixel(255, 239) == get_nes_rgb_color(0x0F)


def test_attribute_selected_palette_uses_palette_ram_entries_for_final_rgb():
    """
    Objective:
    Validate the full lookup chain:

        tile coordinate (2, 0)
            -> top-right attribute quadrant
            -> palette ID 1

        CHR pixel color index 3
            -> background palette 1 entry 3
            -> palette RAM value $13
            -> get_nes_rgb_color($13)
    """
    nametable = make_empty_nametable()
    nametable[2] = 1

    attribute_table = make_empty_attribute_table()
    attribute_table[0] = pack_attribute_byte(
        topleft=0,
        topright=1,
        bottomleft=2,
        bottomright=3,
    )

    pattern_table = make_empty_pattern_table()
    set_tile_row_to_color_index(pattern_table, tile_id=1, row=0, color_index=3)

    framebuffer = nametable_with_palette_ram_to_framebuffer(
        bytes(nametable),
        bytes(attribute_table),
        bytes(pattern_table),
        make_background_palette_ram(),
    )

    assert framebuffer.get_pixel(16, 0) == get_nes_rgb_color(0x13)


def test_each_attribute_quadrant_can_select_different_palette_ram_entries():
    """
    Objective:
    One attribute byte can select four different background palettes, and those
    palettes are resolved from palette RAM.
    """
    nametable = make_empty_nametable()
    nametable[0] = 1
    nametable[2] = 1
    nametable[2 * 32] = 1
    nametable[(2 * 32) + 2] = 1

    attribute_table = make_empty_attribute_table()
    attribute_table[0] = pack_attribute_byte(0, 1, 2, 3)

    pattern_table = make_empty_pattern_table()
    set_tile_row_to_color_index(pattern_table, tile_id=1, row=0, color_index=2)

    framebuffer = nametable_with_palette_ram_to_framebuffer(
        bytes(nametable),
        bytes(attribute_table),
        bytes(pattern_table),
        make_background_palette_ram(),
    )

    assert framebuffer.get_pixel(0, 0) == get_nes_rgb_color(0x02)
    assert framebuffer.get_pixel(16, 0) == get_nes_rgb_color(0x12)
    assert framebuffer.get_pixel(0, 16) == get_nes_rgb_color(0x22)
    assert framebuffer.get_pixel(16, 16) == get_nes_rgb_color(0x32)


def test_palette_ram_helper_matches_manual_composition():
    """
    Objective:
    nametable_with_palette_ram_to_framebuffer is a convenience composition helper,
    not a separate rendering algorithm.

    It should match:
        build_background_palettes_from_palette_ram(...)
        nametable_with_attributes_to_framebuffer(..., background_palettes)
    """
    nametable = make_empty_nametable()
    nametable[2] = 1

    attribute_table = make_empty_attribute_table()
    attribute_table[0] = pack_attribute_byte(0, 1, 2, 3)

    pattern_table = make_empty_pattern_table()
    set_tile_row_to_color_index(pattern_table, tile_id=1, row=0, color_index=3)

    palette_ram = make_background_palette_ram()
    background_palettes = build_background_palettes_from_palette_ram(palette_ram)

    manual = nametable_with_attributes_to_framebuffer(
        bytes(nametable),
        bytes(attribute_table),
        bytes(pattern_table),
        background_palettes,
    )
    composed = nametable_with_palette_ram_to_framebuffer(
        bytes(nametable),
        bytes(attribute_table),
        bytes(pattern_table),
        palette_ram,
    )

    assert composed.width == manual.width
    assert composed.height == manual.height
    assert composed.pixels == manual.pixels
