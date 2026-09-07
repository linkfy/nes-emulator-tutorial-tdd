"""
PPUCTRL controls how much PPUDATA increments vram_addr.

Reference:
    https://www.nesdev.org/wiki/PPU_registers#PPUCTRL

File to update:
    emulator/ppu/ppu.py

Constant to add:
    CTRL_VRAM_INCREMENT_BY_32 = 1 << 2

Why this step exists:
PPUDATA ($2007) accesses PPU memory at the current internal VRAM address. After
each access, the PPU increments that address.

The increment amount is controlled by PPUCTRL ($2000) bit 2:

    bit 2 clear -> increment by 1
    bit 2 set   -> increment by 32

Why this matters:
Increment-by-1 is useful for writing across a row of consecutive PPU memory.
Increment-by-32 is useful for writing down a column in nametable memory.

Suggested implementation pseudocode:

    CTRL_VRAM_INCREMENT_BY_32 = 1 << 2

    case 0x2007:
        self.data = value
        self.ppu_bus.write(self.vram_addr, value)

        increment = 32 if self.ctrl & CTRL_VRAM_INCREMENT_BY_32 else 1
        self.vram_addr = (self.vram_addr + increment) & 0x3FFF

Important:
Keep masking vram_addr with 0x3FFF because the PPU address space is 14-bit:

    $0000-$3FFF

Out of scope:
    - other PPUCTRL bits
    - NMI enable
    - pattern table selection
    - base nametable selection
    - rendering
"""

from emulator.ppu.ppu import CTRL_VRAM_INCREMENT_BY_32, PPU


def set_ppuaddr(ppu: PPU, addr: int) -> None:
    """Set PPU.vram_addr through the public $2006 two-write interface."""
    ppu.write_register(0x2006, (addr >> 8) & 0xFF)
    ppu.write_register(0x2006, addr & 0xFF)


def test_ppuctrl_vram_increment_constant_exists():
    """
    Objective:
    Name PPUCTRL bit 2, which selects PPUDATA increment-by-32 mode.
    """
    assert CTRL_VRAM_INCREMENT_BY_32 == 1 << 2


def test_ppudata_increments_vram_addr_by_one_when_increment_bit_is_clear():
    """
    Objective:
    With PPUCTRL bit 2 clear, PPUDATA should increment vram_addr by 1.
    """
    ppu = PPU()
    ppu.write_register(0x2000, 0x00)
    set_ppuaddr(ppu, 0x2000)

    ppu.write_register(0x2007, 0xAA)

    assert ppu.vram_addr == 0x2001


def test_ppudata_increments_vram_addr_by_32_when_increment_bit_is_set():
    """
    Objective:
    With PPUCTRL bit 2 set, PPUDATA should increment vram_addr by 32.
    """
    ppu = PPU()
    ppu.write_register(0x2000, CTRL_VRAM_INCREMENT_BY_32)
    set_ppuaddr(ppu, 0x2000)

    ppu.write_register(0x2007, 0xBB)

    assert ppu.vram_addr == 0x2020


def test_ppudata_increment_by_32_still_writes_to_original_address_before_incrementing():
    """
    Objective:
    PPUDATA should write to the old vram_addr first, then increment.

    Why:
    The increment affects the next PPUDATA access, not the current one.
    """
    ppu = PPU()
    ppu.write_register(0x2000, CTRL_VRAM_INCREMENT_BY_32)
    set_ppuaddr(ppu, 0x2000)

    ppu.write_register(0x2007, 0xCC)

    assert ppu.ppu_bus.read(0x2000) == 0xCC
    assert ppu.vram_addr == 0x2020


def test_ppudata_increment_wraps_to_14_bit_ppu_address_space():
    """
    Objective:
    vram_addr should stay inside the PPU $0000-$3FFF address range after
    incrementing.
    """
    ppu = PPU()
    ppu.write_register(0x2000, CTRL_VRAM_INCREMENT_BY_32)
    set_ppuaddr(ppu, 0x3FF0)

    ppu.write_register(0x2007, 0xDD)

    assert ppu.vram_addr == ((0x3FF0 + 32) & 0x3FFF)
