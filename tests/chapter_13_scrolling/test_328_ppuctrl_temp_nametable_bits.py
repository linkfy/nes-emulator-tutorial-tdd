"""
Copy PPUCTRL base-nametable selection into temp_vram_addr.

File to update:
    emulator/ppu/ppu.py

Reference documentation:
    https://www.nesdev.org/wiki/PPU_scrolling#$2000_(PPUCTRL)_write
    https://www.nesdev.org/wiki/PPU_registers

Why this step exists:
The PPU scrolling address is assembled from several CPU-visible register writes.
The project already handles most of the $2005 PPUSCROLL pieces:

    coarse X -> temp_vram_addr bits 0-4
    coarse Y -> temp_vram_addr bits 5-9
    fine Y   -> temp_vram_addr bits 12-14
    fine X   -> separate fine_x field

The missing piece is the logical base-nametable selection:

    PPUCTRL bits 0-1 -> temp_vram_addr bits 10-11

Without this connection, temp_vram_addr behaves as if scrolling always starts from
logical nametable 0 ($2000), even when game software selected $2400, $2800, or
$2C00. A future viewport renderer would therefore cross the wrong logical boundary.

Internal scrolling layout:

    temp_vram_addr (t): yyy NN YYYYY XXXXX

    XXXXX -> coarse X tile position
    YYYYY -> coarse Y tile position
    NN    -> logical nametable selection
    yyy   -> fine Y pixel position

    fine_x (x) is stored separately

PPUCTRL mapping:

    bits 0-1 = 00 -> logical nametable $2000
    bits 0-1 = 01 -> logical nametable $2400
    bits 0-1 = 10 -> logical nametable $2800
    bits 0-1 = 11 -> logical nametable $2C00

Suggested implementation:

    # emulator/ppu/ppu.py

    case 0x2000:
        self.ctrl = value

        # --- NEW LINE: COPY BASE NAMETABLE INTO temp_vram_addr: ...GH.. ........ <- value: ......GH
        self.temp_vram_addr = (self.temp_vram_addr & 0b1111_0011_1111_1111) | ((value & CTRL_BASE_NAMETABLE_MASK) << 10)
        # --- END NEW LINE ---

Why clear bits 10-11 first?
A game may change from any logical nametable to any other logical nametable. Using
only OR would set new bits but could not clear old bits. The clear-then-insert
operation replaces the previous selection while preserving coarse X, coarse Y, and
fine Y.

Why not use the old scroll field?
$2005 receives two writes, but the compatibility scroll field stores only the most
recent byte. temp_vram_addr plus fine_x preserve the complete hardware-style state.

Important distinction:
This step records logical nametable selection. Cartridge mirroring then maps that
logical selection onto physical nametable RAM. Neither operation moves the visible
viewport by itself; viewport extraction/rendering comes in later steps.

Out of scope:
    - deriving viewport pixel X/Y
    - rendering adjacent nametables
    - transferring t into v at exact hardware dots
    - changing PpuBus mirroring
    - commercial ROM fixtures
"""

from emulator.ppu.ppu import CTRL_BASE_NAMETABLE_MASK, PPU


TEMP_NAMETABLE_BITS_MASK = 0b0000_1100_0000_0000


def selected_nametable_from_temp_addr(ppu: PPU) -> int:
    """Return the logical nametable index encoded in temp_vram_addr."""
    return (ppu.temp_vram_addr >> 10) & 0b11


def selected_nametable_base_addr(ppu: PPU) -> int:
    """Convert the temporary nametable index into its logical PPU base address."""
    return 0x2000 + selected_nametable_from_temp_addr(ppu) * 0x400


def test_ppuctrl_base_nametable_mask_names_lowest_two_bits():
    """
    Objective:
    Keep the CPU-visible PPUCTRL field explicit instead of spreading a magic value.
    """
    assert CTRL_BASE_NAMETABLE_MASK == 0b0000_0011


def test_ppuctrl_selection_zero_encodes_logical_nametable_2000():
    """
    Objective:
    PPUCTRL bits 00 select logical nametable 0 at $2000.
    """
    ppu = PPU()

    ppu.write_register(0x2000, 0b0000_0000)

    assert selected_nametable_from_temp_addr(ppu) == 0
    assert selected_nametable_base_addr(ppu) == 0x2000


def test_ppuctrl_selection_one_encodes_logical_nametable_2400():
    """
    Objective:
    PPUCTRL bits 01 select logical nametable 1 at $2400.
    """
    ppu = PPU()

    ppu.write_register(0x2000, 0b0000_0001)

    assert selected_nametable_from_temp_addr(ppu) == 1
    assert selected_nametable_base_addr(ppu) == 0x2400


def test_ppuctrl_selection_two_encodes_logical_nametable_2800():
    """
    Objective:
    PPUCTRL bits 10 select logical nametable 2 at $2800.
    """
    ppu = PPU()

    ppu.write_register(0x2000, 0b0000_0010)

    assert selected_nametable_from_temp_addr(ppu) == 2
    assert selected_nametable_base_addr(ppu) == 0x2800


def test_ppuctrl_selection_three_encodes_logical_nametable_2c00():
    """
    Objective:
    PPUCTRL bits 11 select logical nametable 3 at $2C00.
    """
    ppu = PPU()

    ppu.write_register(0x2000, 0b0000_0011)

    assert selected_nametable_from_temp_addr(ppu) == 3
    assert selected_nametable_base_addr(ppu) == 0x2C00


def test_ppuctrl_write_replaces_previous_nametable_selection():
    """
    Objective:
    Clear old bits before inserting new bits so selection can change from 11 back to
    00 rather than remaining stuck at table 3.
    """
    ppu = PPU()
    ppu.write_register(0x2000, 0b0000_0011)
    assert selected_nametable_from_temp_addr(ppu) == 3

    ppu.write_register(0x2000, 0b0000_0000)

    assert selected_nametable_from_temp_addr(ppu) == 0


def test_ppuctrl_write_preserves_other_temp_vram_address_bits():
    """
    Objective:
    PPUCTRL owns only temporary-address bits 10-11. Coarse X/Y and fine Y must remain
    unchanged.
    """
    ppu = PPU()
    original = 0b0111_0011_1010_0101
    ppu.temp_vram_addr = original

    ppu.write_register(0x2000, 0b0000_0010)

    assert (
        ppu.temp_vram_addr & ~TEMP_NAMETABLE_BITS_MASK
    ) == (
        original & ~TEMP_NAMETABLE_BITS_MASK
    )
    assert selected_nametable_from_temp_addr(ppu) == 2


def test_unrelated_ppuctrl_bits_do_not_change_temp_nametable_selection():
    """
    Objective:
    NMI, pattern-table, sprite-size, and VRAM-increment flags share PPUCTRL but must
    not leak into temporary-address bits 10-11.
    """
    ppu = PPU()
    unrelated_ctrl_bits = 0b1111_1100

    ppu.write_register(0x2000, unrelated_ctrl_bits)

    assert selected_nametable_from_temp_addr(ppu) == 0


def test_ppuctrl_register_still_preserves_complete_written_byte():
    """
    Objective:
    Adding internal scroll-state behavior must preserve the existing self.ctrl
    register contract used by NMI and pattern-table logic.
    """
    ppu = PPU()
    value = 0b1011_1101

    ppu.write_register(0x2000, value)

    assert ppu.ctrl == value
    assert selected_nametable_from_temp_addr(ppu) == (value & 0b11)


def test_ppuctrl_value_is_masked_to_one_byte_before_scroll_state_update():
    """
    Objective:
    Preserve the register-write invariant that host integers are reduced to one byte
    before decoding PPUCTRL fields.
    """
    ppu = PPU()

    ppu.write_register(0x2000, 0x102)

    assert ppu.ctrl == 0x02
    assert selected_nametable_from_temp_addr(ppu) == 2
