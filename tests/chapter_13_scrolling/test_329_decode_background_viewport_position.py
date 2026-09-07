"""
Decode a simplified background viewport position from PPU scrolling state.

File to create:
    emulator/rendering/background_viewport.py

Reference documentation:
    https://www.nesdev.org/wiki/PPU_scrolling
    https://www.nesdev.org/wiki/PPU_scrolling#PPU_internal_registers
    https://www.nesdev.org/wiki/PPU_scrolling#During_rendering

Why this step exists:
The PPU stores scrolling as packed hardware fields rather than ready-to-use pixel
coordinates. Rendering needs a simple top-left viewport position, so this step
decodes:

    temp_vram_addr (t): yyy NN YYYYY XXXXX
    fine_x (x):         xxx

Where:

    XXXXX -> coarse X tile position, 5 bits
    YYYYY -> coarse Y tile position, 5 bits
    NN    -> logical nametable X/Y selection
    yyy   -> fine Y pixel position, 3 bits
    xxx   -> fine X pixel position, 3 bits stored separately

Pixel conversion:

    viewport X = nametable X * 256 + coarse X * 8 + fine X
    viewport Y = nametable Y * 240 + coarse Y * 8 + fine Y

Suggested implementation:

    # emulator/rendering/background_viewport.py

    NAMETABLE_PIXEL_WIDTH = 256
    NAMETABLE_PIXEL_HEIGHT = 240
    TILE_PIXEL_SIZE = 8

    BackgroundViewportPosition = tuple[int, int]


    def decode_background_viewport_position(
        temp_vram_addr: int,
        fine_x: int,
    ) -> BackgroundViewportPosition:
        coarse_x = temp_vram_addr & 0b1_1111
        coarse_y = (temp_vram_addr >> 5) & 0b1_1111

        nametable_x = (temp_vram_addr >> 10) & 1
        nametable_y = (temp_vram_addr >> 11) & 1

        fine_y = (temp_vram_addr >> 12) & 0b111

        viewport_x = (
            nametable_x * NAMETABLE_PIXEL_WIDTH
            + coarse_x * TILE_PIXEL_SIZE
            + fine_x
        )

        viewport_y = (
            nametable_y * NAMETABLE_PIXEL_HEIGHT
            + coarse_y * TILE_PIXEL_SIZE
            + fine_y
        )

        return viewport_x, viewport_y

Why use t and x instead of the old scroll field?
$2005 receives horizontal and vertical writes, while the compatibility scroll field
stores only the latest byte. The hardware-style t and x fields preserve the complete
packed state.

Accuracy boundary:
Real hardware renders from current address v plus fine X after timed transfers from
t into v. This tutorial currently uses t plus fine X as a frame-level snapshot. The
exact dot-257 and pre-render-dot-280-304 transfers remain future timing work.

Another simplification:
Real coarse Y values 30 and 31 have special wrapping behavior. This step only
performs direct field-to-pixel decoding; viewport wrapping comes later.

Out of scope:
    - reading nametable bytes
    - creating a framebuffer
    - crossing a nametable boundary
    - exact t -> v timing transfers
    - coarse Y 30/31 wrapping
    - commercial ROM fixtures
"""

from emulator.ppu.ppu import PPU
from emulator.rendering.background_viewport import (
    BackgroundViewportPosition,
    NAMETABLE_PIXEL_HEIGHT,
    NAMETABLE_PIXEL_WIDTH,
    TILE_PIXEL_SIZE,
    decode_background_viewport_position,
)


def make_temp_vram_addr(
    *,
    coarse_x: int = 0,
    coarse_y: int = 0,
    nametable_x: int = 0,
    nametable_y: int = 0,
    fine_y: int = 0,
) -> int:
    """Pack simplified scrolling fields into the PPU t-register layout."""
    return (
        (coarse_x & 0b1_1111)
        | ((coarse_y & 0b1_1111) << 5)
        | ((nametable_x & 1) << 10)
        | ((nametable_y & 1) << 11)
        | ((fine_y & 0b111) << 12)
    )


def test_viewport_constants_match_nametable_and_tile_dimensions():
    """
    Objective:
    Name the pixel dimensions used when converting packed tile coordinates.
    """
    assert NAMETABLE_PIXEL_WIDTH == 256
    assert NAMETABLE_PIXEL_HEIGHT == 240
    assert TILE_PIXEL_SIZE == 8


def test_background_viewport_position_type_alias_is_coordinate_tuple():
    """
    Objective:
    Keep the decoded result as simple pure data for future viewport rendering.
    """
    position: BackgroundViewportPosition = (123, 45)

    assert position == (123, 45)


def test_zero_scroll_decodes_to_top_left_of_nametable_zero():
    """
    Objective:
    Empty packed state and zero fine X represent viewport coordinate (0, 0).
    """
    position = decode_background_viewport_position(
        temp_vram_addr=0,
        fine_x=0,
    )

    assert position == (0, 0)


def test_coarse_x_converts_tiles_to_pixels():
    """
    Objective:
    Coarse X selects an 8-pixel-wide tile column.
    """
    temp = make_temp_vram_addr(coarse_x=5)

    position = decode_background_viewport_position(temp, fine_x=0)

    assert position == (40, 0)


def test_fine_x_adds_pixel_offset_inside_horizontal_tile():
    """
    Objective:
    Fine X contributes a 0-7 pixel offset after coarse tile selection.
    """
    temp = make_temp_vram_addr(coarse_x=5)

    position = decode_background_viewport_position(temp, fine_x=3)

    assert position == (43, 0)


def test_coarse_y_uses_all_five_bits_and_converts_tiles_to_pixels():
    """
    Objective:
    Coarse Y is five bits, not four. A value above 15 must remain intact.
    """
    temp = make_temp_vram_addr(coarse_y=20)

    position = decode_background_viewport_position(temp, fine_x=0)

    assert position == (0, 160)


def test_fine_y_adds_pixel_offset_inside_vertical_tile():
    """
    Objective:
    Fine Y contributes a 0-7 pixel offset after coarse tile-row selection.
    """
    temp = make_temp_vram_addr(coarse_y=2, fine_y=6)

    position = decode_background_viewport_position(temp, fine_x=0)

    assert position == (0, 22)


def test_horizontal_nametable_bit_adds_256_pixels():
    """
    Objective:
    Logical nametable X=1 selects the right-hand 256-pixel region.
    """
    temp = make_temp_vram_addr(nametable_x=1)

    position = decode_background_viewport_position(temp, fine_x=0)

    assert position == (256, 0)


def test_vertical_nametable_bit_adds_240_pixels():
    """
    Objective:
    Logical nametable Y=1 selects the lower 240-pixel region in the simplified
    viewport model.
    """
    temp = make_temp_vram_addr(nametable_y=1)

    position = decode_background_viewport_position(temp, fine_x=0)

    assert position == (0, 240)


def test_combined_fields_decode_one_viewport_coordinate():
    """
    Objective:
    Verify all packed fields contribute to the final coordinate without overwriting
    one another.
    """
    temp = make_temp_vram_addr(
        coarse_x=5,
        coarse_y=2,
        nametable_x=1,
        nametable_y=1,
        fine_y=6,
    )

    position = decode_background_viewport_position(temp, fine_x=3)

    assert position == (299, 262)


def test_existing_ppuscroll_writes_produce_decodable_pixel_offsets():
    """
    Objective:
    Connect the pure decoder to the PPU's existing two-write $2005 state model.

    Horizontal value 43 -> coarse X 5, fine X 3.
    Vertical value 22   -> coarse Y 2, fine Y 6.
    """
    ppu = PPU()

    ppu.write_register(0x2005, 43)
    ppu.write_register(0x2005, 22)

    position = decode_background_viewport_position(
        temp_vram_addr=ppu.temp_vram_addr,
        fine_x=ppu.fine_x,
    )

    assert position == (43, 22)


def test_ppuctrl_and_ppuscroll_together_produce_logical_viewport_position():
    """
    Objective:
    PPUCTRL supplies nametable selection while PPUSCROLL supplies coarse/fine pixel
    offsets in the shared t/x state model.
    """
    ppu = PPU()

    ppu.write_register(0x2000, 0b0000_0001)
    ppu.write_register(0x2005, 43)
    ppu.write_register(0x2005, 22)

    position = decode_background_viewport_position(
        temp_vram_addr=ppu.temp_vram_addr,
        fine_x=ppu.fine_x,
    )

    assert position == (299, 22)
