"""
Implement PPUSCROLL ($2005) two-write scroll behavior.
!! Take your time to implement this

References:
    https://www.nesdev.org/wiki/PPU_registers#PPUSCROLL
    https://www.nesdev.org/wiki/PPU_scrolling#$2005_(PPUSCROLL)_first_write_(w_is_0)
    https://www.nesdev.org/wiki/PPU_scrolling#$2005_(PPUSCROLL)_second_write_(w_is_1)

File to update:
    emulator/ppu/ppu.py

Method to update:
    PPU.write_register(addr, value)

Why this step exists:
PPUSCROLL is the CPU-visible register at $2005. Like PPUADDR ($2006), it uses
the shared first-write / second-write toggle:

    second_write_toggle == False -> first write
    second_write_toggle == True  -> second write

The first write configures horizontal scroll:

    value bits 7-3 -> coarse X, stored in temp_vram_addr bits 0-4
    value bits 2-0 -> fine X, stored in fine_x

The second write configures vertical scroll:

    value bits 7-3 -> coarse Y, stored in temp_vram_addr bits 5-9
    value bits 2-0 -> fine Y, stored in temp_vram_addr bits 12-14

Important internal-register model:

    vram_addr           -> v, current VRAM address
    temp_vram_addr      -> t, temporary VRAM address
    fine_x              -> x, fine horizontal scroll
    second_write_toggle -> w, first/second write toggle

Suggested implementation pseudocode, matching the explicit bit-moving style:

    case 0x2005:
        # Keep for old compatibility.
        self.scroll = value

        if not self.second_write_toggle:
            # Reference:
            # https://www.nesdev.org/wiki/PPU_scrolling#$2005_(PPUSCROLL)_first_write_(w_is_0)
            #
            # PPU Scroll first write.
            # Incoming value bits are named ABCDEFGH.
            #
            # fine_x register:
            #     x: FGH <- value: .....FGH
            #
            # In other words, save the last 3 bits as fine horizontal scroll.
            self.fine_x = value & 0b0000_0111

            # temp_vram_addr register:
            #     t: ....... ...ABCDE <- value: ABCDE...
            #
            # In other words, save the upper 5 bits as coarse X in bits 0-4.
            # The mask keeps every temp_vram_addr bit except coarse X.
            self.temp_vram_addr = (
                (self.temp_vram_addr & 0b1111_1111_1110_0000)
                | (value >> 3)
            )

            # w <- 1
            # Next $2005/$2006 write will be treated as the second write.
            self.second_write_toggle = True
        else:
            # Reference:
            # https://www.nesdev.org/wiki/PPU_scrolling#$2005_(PPUSCROLL)_second_write_(w_is_1)
            #
            # PPU Scroll second write.
            # Incoming value bits are named ABCDEFGH.
            #
            # temp_vram_addr register:
            #     t: FGH..AB CDE..... <- value: ABCDEFGH
            #
            # Step 1: keep only untouched bits:
            #     - bit 15
            #     - nametable bits 10-11
            #     - coarse X bits 0-4
            #
            # This clears the vertical scroll destination bits:
            #     - coarse Y bits 5-9
            #     - fine Y bits 12-14
            self.temp_vram_addr = (
                self.temp_vram_addr & 0b1000_1100_0001_1111
            )

            # Step 2: put the last 3 bits into fine Y.
            #     value: .....FGH
            #     FGH << 12 -> bits 12-14
            self.temp_vram_addr = (
                self.temp_vram_addr | ((value & 0b0000_0111) << 12)
            )

            # Step 3: put the upper 5 bits into coarse Y.
            #     value: ABCDE...
            #     (value & 11111000) << 2 -> bits 5-9
            self.temp_vram_addr = (
                self.temp_vram_addr | ((value & 0b1111_1000) << 2)
            )

            # w <- 0
            # The two-write PPUSCROLL sequence is complete.
            self.second_write_toggle = False


Out of scope:
    - copying scroll bits from temp_vram_addr to vram_addr during rendering
    - scanline/cycle timing
    - actual background rendering
"""

from emulator.ppu.ppu import PPU


def test_first_ppuscroll_write_sets_fine_x_and_coarse_x():
    """
    Objective:
    First write to $2005 sets horizontal scroll pieces.

    Example value:
        0x2D == 0b0010_1101 == decimal 45

    Split:
        fine X   = low 3 bits  = 0b101 = 5
        coarse X = upper 5 bits = 45 >> 3 = 5
    """
    ppu = PPU()

    ppu.write_register(0x2005, 0x2D)

    assert ppu.fine_x == 5
    assert ppu.temp_vram_addr & 0x001F == 5
    assert ppu.second_write_toggle is True


def test_first_ppuscroll_write_preserves_non_coarse_x_bits():
    """
    Objective:
    First write should replace only coarse X bits 0-4 in temp_vram_addr.

    Why:
    PPUSCROLL first write should not destroy vertical scroll or nametable bits
    already stored in temp_vram_addr.
    """
    ppu = PPU()
    ppu.temp_vram_addr = 0x7BE0

    ppu.write_register(0x2005, 0x2D)

    assert ppu.temp_vram_addr == ((0x7BE0 & 0xFFE0) | (0x2D >> 3))


def test_second_ppuscroll_write_sets_fine_y_and_coarse_y():
    """
    Objective:
    Second write to $2005 sets vertical scroll pieces.

    Example second value:
        0x6B == 0b0110_1011 == decimal 107

    Split:
        fine Y   = low 3 bits  = 0b011 = 3
        coarse Y = upper 5 bits = 0x6B >> 3 = 13

    Destination:
        fine Y   -> temp_vram_addr bits 12-14
        coarse Y -> temp_vram_addr bits 5-9
    """
    ppu = PPU()

    ppu.write_register(0x2005, 0x2D)  # first write, sets coarse X/fine X
    ppu.write_register(0x2005, 0x6B)  # second write, sets coarse Y/fine Y

    fine_y = (ppu.temp_vram_addr >> 12) & 0x07
    coarse_y = (ppu.temp_vram_addr >> 5) & 0x1F

    assert fine_y == 3
    assert coarse_y == 13
    assert ppu.second_write_toggle is False


def test_second_ppuscroll_write_preserves_coarse_x_and_nametable_bits():
    """
    Objective:
    Second write should replace vertical scroll bits while preserving untouched
    bits such as coarse X and nametable selection.

    This protects the internal-register model needed for future rendering.
    """
    ppu = PPU()
    ppu.temp_vram_addr = 0x0C00  # nametable bits set

    ppu.write_register(0x2005, 0x2D)  # coarse X becomes 5, nametable preserved
    ppu.write_register(0x2005, 0x6B)  # fine Y 3, coarse Y 13

    expected = (
        (0x0C05 & 0b1000_1100_0001_1111)
        | ((0x6B & 0b0000_0111) << 12)
        | ((0x6B & 0b1111_1000) << 2)
    )

    assert ppu.temp_vram_addr == expected
    assert ppu.temp_vram_addr & 0x001F == 5
    assert ppu.temp_vram_addr & 0x0C00 == 0x0C00


def test_ppuscroll_preserves_scroll_as_last_written_value_for_compatibility():
    """
    Objective:
    Keep the earlier simple `scroll` field useful as the last byte written to
    PPUSCROLL.

    Important:
    The real scroll state is now split across fine_x and temp_vram_addr.
    """
    ppu = PPU()

    ppu.write_register(0x2005, 0x2D)
    assert ppu.scroll == 0x2D

    ppu.write_register(0x2005, 0x6B)
    assert ppu.scroll == 0x6B
