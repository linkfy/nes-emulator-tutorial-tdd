"""
Build a background opacity mask from current PPU background memory.

File to update:
    emulator/rendering/ppu_background_renderer.py

Why this step exists:
Step 310 added the pure helper:

    build_background_opaque_mask(pattern_table, nametable)

That helper works from raw bytes. This step adds the PPU-level sibling of:

    ppu_background_to_framebuffer(ppu)

The new helper should be:

    ppu_background_to_opaque_mask(ppu)

It is very similar to ppu_background_to_framebuffer(), but it needs less
information.

ppu_background_to_framebuffer() needs:
    - visible nametable bytes
    - attribute table bytes
    - selected background pattern table bytes
    - palette RAM bytes

because it produces RGB pixels.

ppu_background_to_opaque_mask() only needs:
    - visible nametable bytes
    - selected background pattern table bytes

because opacity depends only on:

    CHR color index != 0

Attribute table and palette RAM do not affect opacity.

Example implementation:

    def ppu_background_to_opaque_mask(ppu: PPU) -> BackgroundOpaqueMask:
        nametable_bytes = bytes(
            ppu.ppu_bus.read(BASE_NAMETABLE_ADDR + offset)
            for offset in range(NAMETABLE_SIZE)
        )

        pattern_table_base = (
            PATTERN_TABLE_1_ADDR
            if ppu.ctrl & CTRL_BACKGROUND_PATTERN_TABLE
            else PATTERN_TABLE_0_ADDR
        )

        pattern_table_bytes = bytes(
            ppu.ppu_bus.read(pattern_table_base + offset)
            for offset in range(PATTERN_TABLE_SIZE)
        )

        return build_background_opaque_mask(
            pattern_table=pattern_table_bytes,
            nametable=nametable_bytes,
        )

Important:
This step does not modify Console.render_framebuffer() yet. The next step will wire
Console to call this helper and pass the mask to the compositor.

Out of scope:
    - changing emulator/console.py
    - passing the mask to composite_background_and_sprites()
    - sprite 0 hit
    - sprite overflow
    - pygame
"""

import inspect

from emulator.ppu.chr_decoder import PATTERN_TABLE_SIZE
from emulator.ppu.ppu import CTRL_BACKGROUND_PATTERN_TABLE, PPU
from emulator.rendering.nametable_renderer import (
    NAMETABLE_SIZE,
    build_background_opaque_mask,
)
from emulator.rendering.ppu_background_renderer import (
    BASE_NAMETABLE_ADDR,
    PATTERN_TABLE_0_ADDR,
    PATTERN_TABLE_1_ADDR,
    ppu_background_to_opaque_mask,
)


def set_tile_row_to_color_index_in_ppu(
    ppu: PPU,
    pattern_table_base: int,
    tile_id: int,
    row: int,
    color_index: int,
) -> None:
    """Write one synthetic CHR tile row into PPU pattern-table memory."""
    tile_offset = tile_id * 16
    low_bit = color_index & 0b01
    high_bit = (color_index >> 1) & 0b01

    ppu.ppu_bus.write(pattern_table_base + tile_offset + row, 0xFF if low_bit else 0x00)
    ppu.ppu_bus.write(pattern_table_base + tile_offset + 8 + row, 0xFF if high_bit else 0x00)


def read_bytes_from_ppu(ppu: PPU, start: int, size: int) -> bytes:
    """Read a byte range from PPU memory through PpuBus."""
    return bytes(ppu.ppu_bus.read(start + offset) for offset in range(size))


def test_ppu_background_to_opaque_mask_function_exists():
    """
    Objective:
    Expose one helper for converting current PPU background memory into an opacity
    mask.
    """
    assert callable(ppu_background_to_opaque_mask)


def test_ppu_background_to_opaque_mask_returns_one_entry_per_visible_pixel():
    """
    Objective:
    The PPU-level helper should return the same per-pixel mask shape as the pure
    nametable helper.
    """
    ppu = PPU()

    mask = ppu_background_to_opaque_mask(ppu)

    assert len(mask) == 256 * 240


def test_ppu_background_to_opaque_mask_reads_visible_nametable_tile_ids():
    """
    Objective:
    The helper should read tile IDs from visible nametable memory at $2000-$23BF.
    """
    ppu = PPU()
    ppu.ppu_bus.write(BASE_NAMETABLE_ADDR, 1)
    set_tile_row_to_color_index_in_ppu(
        ppu=ppu,
        pattern_table_base=PATTERN_TABLE_0_ADDR,
        tile_id=1,
        row=0,
        color_index=1,
    )

    mask = ppu_background_to_opaque_mask(ppu)

    assert mask[0] is True


def test_ppu_background_to_opaque_mask_uses_pattern_table_zero_when_background_bit_is_clear():
    """
    Objective:
    If PPUCTRL bit 4 is clear, opacity comes from background pattern table $0000.
    """
    ppu = PPU()
    assert (ppu.ctrl & CTRL_BACKGROUND_PATTERN_TABLE) == 0

    ppu.ppu_bus.write(BASE_NAMETABLE_ADDR, 1)
    set_tile_row_to_color_index_in_ppu(
        ppu=ppu,
        pattern_table_base=PATTERN_TABLE_0_ADDR,
        tile_id=1,
        row=0,
        color_index=1,
    )
    set_tile_row_to_color_index_in_ppu(
        ppu=ppu,
        pattern_table_base=PATTERN_TABLE_1_ADDR,
        tile_id=1,
        row=0,
        color_index=0,
    )

    mask = ppu_background_to_opaque_mask(ppu)

    assert mask[0] is True


def test_ppu_background_to_opaque_mask_uses_pattern_table_one_when_background_bit_is_set():
    """
    Objective:
    If PPUCTRL bit 4 is set, opacity comes from background pattern table $1000.
    """
    ppu = PPU()
    ppu.write_register(0x2000, CTRL_BACKGROUND_PATTERN_TABLE)

    ppu.ppu_bus.write(BASE_NAMETABLE_ADDR, 1)
    set_tile_row_to_color_index_in_ppu(
        ppu=ppu,
        pattern_table_base=PATTERN_TABLE_0_ADDR,
        tile_id=1,
        row=0,
        color_index=0,
    )
    set_tile_row_to_color_index_in_ppu(
        ppu=ppu,
        pattern_table_base=PATTERN_TABLE_1_ADDR,
        tile_id=1,
        row=0,
        color_index=1,
    )

    mask = ppu_background_to_opaque_mask(ppu)

    assert mask[0] is True


def test_ppu_background_to_opaque_mask_matches_manual_extraction_and_pure_helper():
    """
    Objective:
    ppu_background_to_opaque_mask is an extraction/delegation helper, not a second
    opacity algorithm.
    """
    ppu = PPU()
    ppu.ppu_bus.write(BASE_NAMETABLE_ADDR + 2, 1)
    set_tile_row_to_color_index_in_ppu(
        ppu=ppu,
        pattern_table_base=PATTERN_TABLE_0_ADDR,
        tile_id=1,
        row=0,
        color_index=3,
    )

    extracted_nametable = read_bytes_from_ppu(ppu, BASE_NAMETABLE_ADDR, NAMETABLE_SIZE)
    extracted_pattern_table = read_bytes_from_ppu(
        ppu,
        PATTERN_TABLE_0_ADDR,
        PATTERN_TABLE_SIZE,
    )

    manual = build_background_opaque_mask(
        pattern_table=extracted_pattern_table,
        nametable=extracted_nametable,
    )
    from_ppu = ppu_background_to_opaque_mask(ppu)

    assert from_ppu == manual


def test_ppu_background_to_opaque_mask_does_not_need_attributes_or_palette_ram():
    """
    Objective:
    Opacity depends on CHR color index only, so this helper should be smaller than
    ppu_background_to_framebuffer().
    """
    source = inspect.getsource(ppu_background_to_opaque_mask)

    assert "BASE_ATTR_TABLE_ADDR" not in source
    assert "ATTR_TABLE_SIZE" not in source
    assert "PALETTE_RAM_ADDR" not in source
    assert "PALETTE_RAM_SIZE" not in source
