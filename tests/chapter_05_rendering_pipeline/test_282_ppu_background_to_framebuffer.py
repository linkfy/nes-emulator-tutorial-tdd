"""
Render the current PPU background memory into a framebuffer.

File to create:
    emulator/rendering/ppu_background_renderer.py

Why this step exists:
The renderer can now produce a background framebuffer from explicit byte arrays:

    nametable bytes
    attribute table bytes
    pattern table bytes
    palette RAM bytes

But the emulator's current state stores those bytes behind the PPU/PpuBus memory
interface. This step creates a thin extraction helper:

    ppu_background_to_framebuffer(ppu)

It reads the relevant PPU memory regions, then delegates to the pure renderer.

Memory regions used in this simplified renderer:

    $2000-$23BF -> visible nametable tile IDs, 960 bytes
    $23C0-$23FF -> attribute table, 64 bytes
    $0000-$0FFF -> pattern table 0, if PPUCTRL bit 4 is clear
    $1000-$1FFF -> pattern table 1, if PPUCTRL bit 4 is set
    $3F00-$3F0F -> background palette RAM, 16 bytes

Suggested implementation example:

    def ppu_background_to_framebuffer(ppu: PPU) -> Framebuffer:
        nametable_bytes = bytes(
            ppu.ppu_bus.read(BASE_NAMETABLE_ADDR + offset)
            for offset in range(NAMETABLE_SIZE)
        )

        attribute_table = bytes(
            ppu.ppu_bus.read(BASE_ATTR_TABLE_ADDR + offset)
            for offset in range(ATTR_TABLE_SIZE)
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

        palette_ram = bytes(
            ppu.ppu_bus.read(PALETTE_RAM_ADDR + offset)
            for offset in range(PALETTE_RAM_SIZE)
        )

        return nametable_with_palette_ram_to_framebuffer(
            nametable_bytes,
            attribute_table,
            pattern_table_bytes,
            palette_ram,
        )

Architecture rule:
This helper extracts data from PPU memory. It should not duplicate nametable,
attribute, CHR, or palette rendering logic.

Important simplification:
This renders only the base nametable at $2000. It does not apply scrolling or
PPUCTRL nametable-selection bits yet.

Out of scope:
    - scrolling
    - PPUCTRL base nametable selection
    - sprites
    - OAMDMA
    - pygame display
    - full frame loop
"""

from pathlib import Path

from emulator.ppu.chr_decoder import PATTERN_TABLE_SIZE
from emulator.ppu.ppu import CTRL_BACKGROUND_PATTERN_TABLE, PPU
from emulator.rendering.framebuffer import Framebuffer
from emulator.rendering.nametable_renderer import (
    NAMETABLE_SIZE,
    nametable_with_palette_ram_to_framebuffer,
)
from emulator.rendering.nes_palette import get_nes_rgb_color
from emulator.rendering.palette_ram import PALETTE_RAM_SIZE
from emulator.rendering.ppu_background_renderer import (
    ATTR_TABLE_SIZE,
    BASE_ATTR_TABLE_ADDR,
    BASE_NAMETABLE_ADDR,
    PALETTE_RAM_ADDR,
    PATTERN_TABLE_0_ADDR,
    PATTERN_TABLE_1_ADDR,
    ppu_background_to_framebuffer,
)


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


def write_background_palette_ram(ppu: PPU) -> bytes:
    """
    Write synthetic $3F00-$3F0F background palette RAM bytes and return the same
    bytes for manual-composition comparisons.
    """
    palette_ram = bytes([
        0x0F, 0x01, 0x02, 0x03,
        0x04, 0x11, 0x12, 0x13,
        0x08, 0x21, 0x22, 0x23,
        0x0C, 0x31, 0x32, 0x33,
    ])

    for offset, value in enumerate(palette_ram):
        ppu.ppu_bus.write(PALETTE_RAM_ADDR + offset, value)

    return palette_ram


def read_bytes_from_ppu(ppu: PPU, start: int, size: int) -> bytes:
    """Read a byte range from PPU memory through PpuBus."""
    return bytes(ppu.ppu_bus.read(start + offset) for offset in range(size))


def test_ppu_background_renderer_file_exists():
    """
    Objective:
    Keep live PPU-memory extraction separate from pure nametable rendering.
    """
    assert Path("emulator/rendering/ppu_background_renderer.py").exists()


def test_ppu_background_renderer_declares_memory_region_constants():
    """
    Objective:
    Name the simplified PPU memory regions used for background extraction.
    """
    assert BASE_NAMETABLE_ADDR == 0x2000
    assert BASE_ATTR_TABLE_ADDR == 0x23C0
    assert PALETTE_RAM_ADDR == 0x3F00
    assert PATTERN_TABLE_0_ADDR == 0x0000
    assert PATTERN_TABLE_1_ADDR == 0x1000
    assert ATTR_TABLE_SIZE == 64


def test_ppu_background_to_framebuffer_function_exists():
    """
    Objective:
    Expose one helper for rendering the current PPU background memory snapshot.
    """
    assert callable(ppu_background_to_framebuffer)


def test_ppu_background_to_framebuffer_returns_256_by_240_framebuffer():
    """
    Objective:
    Rendering from PPU memory still produces the NES visible background size.
    """
    ppu = PPU()
    write_background_palette_ram(ppu)

    framebuffer = ppu_background_to_framebuffer(ppu)

    assert isinstance(framebuffer, Framebuffer)
    assert framebuffer.width == 256
    assert framebuffer.height == 240


def test_ppu_background_reads_nametable_tile_ids_from_2000_to_23bf():
    """
    Objective:
    The renderer reads visible nametable tile IDs from $2000-$23BF.

    Setup:
        $2000 contains tile ID 1.
        tile #1 row 0 emits color index 3.
        palette 0 entry 3 comes from palette RAM $3F03 = $03.
    """
    ppu = PPU()
    write_background_palette_ram(ppu)
    ppu.ppu_bus.write(BASE_NAMETABLE_ADDR, 1)
    set_tile_row_to_color_index_in_ppu(
        ppu,
        PATTERN_TABLE_0_ADDR,
        tile_id=1,
        row=0,
        color_index=3,
    )

    framebuffer = ppu_background_to_framebuffer(ppu)

    assert framebuffer.get_pixel(0, 0) == get_nes_rgb_color(0x03)


def test_ppu_background_reads_attribute_table_from_23c0_to_select_palette():
    """
    Objective:
    Attribute bytes from $23C0-$23FF select which background palette is used.

    Setup:
        tile coordinate (2, 0) is top-right quadrant of the first attribute byte.
        $23C0 selects palette ID 1 for top-right.
        tile emits color index 3.
        palette ID 1 entry 3 comes from $3F07 = $13.
    """
    ppu = PPU()
    write_background_palette_ram(ppu)
    ppu.ppu_bus.write(BASE_NAMETABLE_ADDR + 2, 1)
    ppu.ppu_bus.write(BASE_ATTR_TABLE_ADDR, pack_attribute_byte(0, 1, 2, 3))
    set_tile_row_to_color_index_in_ppu(
        ppu,
        PATTERN_TABLE_0_ADDR,
        tile_id=1,
        row=0,
        color_index=3,
    )

    framebuffer = ppu_background_to_framebuffer(ppu)

    assert framebuffer.get_pixel(16, 0) == get_nes_rgb_color(0x13)


def test_ppu_background_uses_pattern_table_zero_when_ppuctrl_background_bit_is_clear():
    """
    Objective:
    If PPUCTRL bit 4 is clear, background tiles use pattern table $0000-$0FFF.
    """
    ppu = PPU()
    write_background_palette_ram(ppu)
    assert (ppu.ctrl & CTRL_BACKGROUND_PATTERN_TABLE) == 0

    ppu.ppu_bus.write(BASE_NAMETABLE_ADDR, 1)
    set_tile_row_to_color_index_in_ppu(
        ppu,
        PATTERN_TABLE_0_ADDR,
        tile_id=1,
        row=0,
        color_index=2,
    )
    set_tile_row_to_color_index_in_ppu(
        ppu,
        PATTERN_TABLE_1_ADDR,
        tile_id=1,
        row=0,
        color_index=3,
    )

    framebuffer = ppu_background_to_framebuffer(ppu)

    assert framebuffer.get_pixel(0, 0) == get_nes_rgb_color(0x02)


def test_ppu_background_uses_pattern_table_one_when_ppuctrl_background_bit_is_set():
    """
    Objective:
    If PPUCTRL bit 4 is set, background tiles use pattern table $1000-$1FFF.
    """
    ppu = PPU()
    write_background_palette_ram(ppu)
    ppu.write_register(0x2000, CTRL_BACKGROUND_PATTERN_TABLE)

    ppu.ppu_bus.write(BASE_NAMETABLE_ADDR, 1)
    set_tile_row_to_color_index_in_ppu(
        ppu,
        PATTERN_TABLE_0_ADDR,
        tile_id=1,
        row=0,
        color_index=2,
    )
    set_tile_row_to_color_index_in_ppu(
        ppu,
        PATTERN_TABLE_1_ADDR,
        tile_id=1,
        row=0,
        color_index=3,
    )

    framebuffer = ppu_background_to_framebuffer(ppu)

    assert framebuffer.get_pixel(0, 0) == get_nes_rgb_color(0x03)


def test_ppu_background_output_matches_manual_extraction_and_pure_renderer():
    """
    Objective:
    ppu_background_to_framebuffer is an extraction/delegation helper, not a second
    rendering algorithm.

    It should match manually reading the same PPU memory ranges and calling the
    pure renderer directly.
    """
    ppu = PPU()
    palette_ram = write_background_palette_ram(ppu)
    ppu.ppu_bus.write(BASE_NAMETABLE_ADDR + 2, 1)
    ppu.ppu_bus.write(BASE_ATTR_TABLE_ADDR, pack_attribute_byte(0, 1, 2, 3))
    set_tile_row_to_color_index_in_ppu(
        ppu,
        PATTERN_TABLE_0_ADDR,
        tile_id=1,
        row=0,
        color_index=3,
    )

    extracted_nametable = read_bytes_from_ppu(ppu, BASE_NAMETABLE_ADDR, NAMETABLE_SIZE)
    extracted_attributes = read_bytes_from_ppu(ppu, BASE_ATTR_TABLE_ADDR, ATTR_TABLE_SIZE)
    extracted_pattern_table = read_bytes_from_ppu(ppu, PATTERN_TABLE_0_ADDR, PATTERN_TABLE_SIZE)

    manual = nametable_with_palette_ram_to_framebuffer(
        extracted_nametable,
        extracted_attributes,
        extracted_pattern_table,
        palette_ram,
    )
    from_ppu = ppu_background_to_framebuffer(ppu)

    assert from_ppu.width == manual.width
    assert from_ppu.height == manual.height
    assert from_ppu.pixels == manual.pixels
