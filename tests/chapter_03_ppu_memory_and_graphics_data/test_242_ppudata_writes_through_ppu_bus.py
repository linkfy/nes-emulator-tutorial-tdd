"""
Implement PPUDATA ($2007) writes through PpuBus.

Reference:
    https://www.nesdev.org/wiki/PPU_registers#PPUDATA

File to update:
    emulator/ppu/ppu.py

Method to update:
    PPU.write_register(addr, value)

Why this step exists:
PPUDATA is the CPU-visible register at $2007. The CPU writes to $2007, but the
actual PPU memory address written is not CPU address $2007. The actual target is
the PPU's internal VRAM address:

    vram_addr

That address is set by PPUADDR ($2006), then PPUDATA ($2007) writes through the
PPU-side bus:

    PPU.write_register($2007, value)
        -> ppu_bus.write(vram_addr, value)
        -> increment vram_addr

Important future-compatibility choices in this test:
    - Use non-CHR addresses such as $2000, not $0000-$1FFF.
      CHR writes will later involve mapper.write_chr / CHR RAM behavior.

    - Test increment-by-1 only when PPUCTRL increment mode is clear.
      Later, PPUCTRL bit 2 may select increment-by-32. These tests should not
      block that future behavior.

Suggested implementation pseudocode for the current stage:

    case 0x2007:
        self.data = value
        self.ppu_bus.write(self.vram_addr, value)
        self.vram_addr = (self.vram_addr + 1) & 0x3FFF

Future implementation note:
Later, the increment may become:

    increment = 32 if self.ctrl & VRAM_INCREMENT_BY_32 else 1
    self.vram_addr = (self.vram_addr + increment) & 0x3FFF

Out of scope:
    - PPUDATA reads
    - PPUDATA read buffering
    - palette read exceptions
    - CHR RAM writes
    - PPUCTRL increment-by-32 behavior
"""

from emulator.ppu.ppu import PPU


def set_ppuaddr(ppu: PPU, addr: int) -> None:
    """Set PPU.vram_addr through the public $2006 two-write interface."""
    ppu.write_register(0x2006, (addr >> 8) & 0xFF)
    ppu.write_register(0x2006, addr & 0xFF)


def test_ppudata_write_stores_value_through_ppu_bus_at_current_vram_addr():
    """
    Objective:
    Writing $2007 should write to PpuBus at the current internal PPU address.

    We use $2000 because it is outside the CHR area $0000-$1FFF, avoiding future
    mapper/CHR RAM write behavior.
    """
    ppu = PPU()
    set_ppuaddr(ppu, 0x2000)

    ppu.write_register(0x2007, 0xAA)

    assert ppu.ppu_bus.read(0x2000) == 0xAA


def test_ppudata_write_preserves_data_as_last_written_value():
    """
    Objective:
    Keep the earlier simple `data` field useful as the last byte written to
    PPUDATA.

    Important:
    The real memory write goes through ppu_bus. The `data` field is only a simple
    observable last-written value at this tutorial stage.
    """
    ppu = PPU()
    set_ppuaddr(ppu, 0x2000)

    ppu.write_register(0x2007, 0xBB)

    assert ppu.data == 0xBB


def test_ppudata_write_increments_vram_addr_by_one_when_ppuctrl_increment_mode_is_clear():
    """
    Objective:
    With the current/default PPUCTRL increment mode clear, writing $2007 advances
    vram_addr by 1.

    Future compatibility:
    If PPUCTRL bit 2 later selects increment-by-32, this test remains valid
    because PPUCTRL is left at its default value 0.
    """
    ppu = PPU()
    assert ppu.ctrl == 0
    set_ppuaddr(ppu, 0x2000)

    ppu.write_register(0x2007, 0xCC)

    assert ppu.vram_addr == 0x2001


def test_ppudata_write_masks_value_through_ppu_bus_storage():
    """
    Objective:
    PPUDATA writes are byte writes.

    The value is already masked by PPU.write_register, and VRAM also stores only
    bytes. This test verifies the visible behavior without depending on where the
    masking happens internally.
    """
    ppu = PPU()
    set_ppuaddr(ppu, 0x2000)

    ppu.write_register(0x2007, 0x123)

    assert ppu.ppu_bus.read(0x2000) == 0x23
    assert ppu.data == 0x23
