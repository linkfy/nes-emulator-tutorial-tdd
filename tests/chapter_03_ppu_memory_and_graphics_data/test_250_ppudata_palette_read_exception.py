"""
Implement the PPUDATA ($2007) palette read exception.

Reference:
    https://www.nesdev.org/wiki/PPU_registers#PPUDATA

File to update:
    emulator/ppu/ppu.py

Constants to add:
    PALETTE_START_ADDR = 0x3F00
    PALETTE_END_ADDR = 0x3FFF

Why this step exists:
Normal PPUDATA reads are buffered:

    read $2007:
        return old ppu_data_buffer
        reload ppu_data_buffer from ppu_bus.read(vram_addr)
        increment vram_addr

Palette reads are the exception. When vram_addr points to palette memory:

    $3F00-$3FFF

the PPU returns the palette byte immediately instead of returning the old buffer.

Important detail:
The old buffer is still discarded. On normal NES PPUs, the buffer is reloaded
from the shadowed nametable memory behind the palette address:

    $3F00 -> reload buffer from $2F00
    $3F10 -> reload buffer from $2F10

That means palette reads affect both:

    - the value returned to the CPU
    - the internal ppu_data_buffer used by future normal reads

Suggested implementation pseudocode, matching the explicit comment style:

    PALETTE_START_ADDR = 0x3F00
    PALETTE_END_ADDR = 0x3FFF

    case 0x2007:  # PPU DATA read
        # Palette data is returned immediately.
        if PALETTE_START_ADDR <= self.vram_addr <= PALETTE_END_ADDR:
            value = self.ppu_bus.read(self.vram_addr)

            # Read buffer is discarded and reloaded from shadowed memory:
            # vram_addr - 0x1000
            # Example: 0x3F00 -> 0x2F00
            self.ppu_data_buffer = self.ppu_bus.read(self.vram_addr - 0x1000)
        else:
            # Normal PPUDATA reads return the old buffer first.
            value = self.ppu_data_buffer

            # Then the buffer is reloaded from current PPU memory.
            self.ppu_data_buffer = self.ppu_bus.read(self.vram_addr)

        increment = 32 if self.ctrl & CTRL_VRAM_INCREMENT_BY_32 else 1

        # Keep vram_addr in the 14-bit PPU address range.
        self.vram_addr = (self.vram_addr + increment) & 0x3FFF

        # Preserve self.data for old test compatibility/debugging.
        self.data = value
        return self.data

Out of scope:
    - palette RAM mirroring, such as $3F10 -> $3F00
    - accurate palette color values
    - rendering
"""

from emulator.ppu.ppu import PALETTE_END_ADDR, PALETTE_START_ADDR, PPU


def set_ppuaddr(ppu: PPU, addr: int) -> None:
    """Set PPU.vram_addr through the public $2006 two-write interface."""
    ppu.write_register(0x2006, (addr >> 8) & 0xFF)
    ppu.write_register(0x2006, addr & 0xFF)


def test_ppu_declares_palette_read_range_constants():
    """
    Objective:
    Name the PPU palette address range used by the PPUDATA read exception.
    """
    assert PALETTE_START_ADDR == 0x3F00
    assert PALETTE_END_ADDR == 0x3FFF


def test_ppudata_palette_read_returns_palette_value_immediately():
    """
    Objective:
    Reading $2007 while vram_addr is in $3F00-$3FFF should return the palette
    byte immediately, not the old ppu_data_buffer.
    """
    ppu = PPU()
    ppu.ppu_data_buffer = 0x55
    ppu.ppu_bus.write(0x3F00, 0x0F)
    set_ppuaddr(ppu, 0x3F00)

    value = ppu.read_register(0x2007)

    assert value == 0x0F


def test_ppudata_palette_read_discards_old_buffer_and_reloads_shadowed_memory():
    """
    Objective:
    Palette reads should replace the old buffer with data from the shadowed
    address behind palette memory.

    Example:
        vram_addr = $3F00
        returned value comes from $3F00
        buffer reload comes from $2F00
    """
    ppu = PPU()
    ppu.ppu_data_buffer = 0x55
    ppu.ppu_bus.write(0x3F00, 0x0F)
    ppu.ppu_bus.write(0x2F00, 0xAA)
    set_ppuaddr(ppu, 0x3F00)

    value = ppu.read_register(0x2007)

    assert value == 0x0F
    assert ppu.ppu_data_buffer == 0xAA


def test_ppudata_palette_read_still_increments_vram_addr():
    """
    Objective:
    Palette reads still increment vram_addr after the read.
    """
    ppu = PPU()
    ppu.ppu_bus.write(0x3F00, 0x0F)
    set_ppuaddr(ppu, 0x3F00)

    ppu.read_register(0x2007)

    assert ppu.vram_addr == 0x3F01


def test_non_palette_ppudata_reads_remain_buffered():
    """
    Objective:
    The palette exception must not break normal buffered PPUDATA reads outside
    $3F00-$3FFF.
    """
    ppu = PPU()
    ppu.ppu_data_buffer = 0x55
    ppu.ppu_bus.write(0x2000, 0xAA)
    set_ppuaddr(ppu, 0x2000)

    value = ppu.read_register(0x2007)

    assert value == 0x55
    assert ppu.ppu_data_buffer == 0xAA


def test_ppudata_palette_read_updates_data_compatibility_field():
    """
    Objective:
    Preserve self.data as the last PPUDATA value returned, even for palette
    immediate reads.
    """
    ppu = PPU()
    ppu.ppu_bus.write(0x3F00, 0x21)
    set_ppuaddr(ppu, 0x3F00)

    value = ppu.read_register(0x2007)

    assert value == 0x21
    assert ppu.data == 0x21
