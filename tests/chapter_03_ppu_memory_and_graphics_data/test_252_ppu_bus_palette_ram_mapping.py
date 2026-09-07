"""
Implement PpuBus palette RAM address mapping.

Reference:
    https://www.nesdev.org/wiki/PPU_palettes
    https://www.nesdev.org/wiki/PPU_memory_map

File to update:
    emulator/bus/ppu_bus.py

Constants to add:
    PALETTE_START = 0x3F00
    PALETTE_END = 0x3FFF
    PALETTE_SIZE = 0x20

Why this step exists:
The PPU address range $3F00-$3FFF is palette memory. Palette memory does not
store tile graphics. It stores NES color indices used later by background and
sprite rendering.

Hardware note:
On the original NES PPU, palette RAM is a small, separate 32-byte memory area
inside the PPU. It is not CHR ROM, and it is not nametable VRAM. It has its own
mirroring behavior in the PPU address range $3F00-$3FFF.

Tutorial simplification:
At this stage, we do not need to split the Python storage into a separate
PaletteRAM object yet. We can keep using the existing large VRAM backing array as
the physical storage location, as long as PpuBus normalizes palette addresses
before reading or writing.

Mental model:

    PPU.write_register($2007, value)
        -> ppu_bus.write(vram_addr, value)
        -> PpuBus detects whether vram_addr is palette memory
        -> PpuBus normalizes palette mirrors
        -> backing storage receives the byte

Palette mirroring rules for this step:

    $3F00-$3F1F is the 32-byte palette window
    $3F20-$3FFF mirrors $3F00-$3F1F

Special backdrop mirrors:

    $3F10 mirrors $3F00
    $3F14 mirrors $3F04
    $3F18 mirrors $3F08
    $3F1C mirrors $3F0C

Suggested implementation example:

    PALETTE_START = 0x3F00
    PALETTE_END = 0x3FFF
    PALETTE_SIZE = 0x20

    def normalize_palette_addr(self, addr: int) -> int:
        index = (addr - PALETTE_START) % PALETTE_SIZE

        if index in (0x10, 0x14, 0x18, 0x1C):
            index -= 0x10

        return PALETTE_START + index

    def read(self, addr: int) -> int:
        addr = addr & PPU_ADDRESS_MASK

        if CHR_START <= addr <= CHR_END:
            ...

        if PALETTE_START <= addr <= PALETTE_END:
            return self.vram.read(self.normalize_palette_addr(addr))

        return self.vram.read(addr)

    def write(self, addr: int, value: int) -> None:
        addr = addr & PPU_ADDRESS_MASK

        if CHR_START <= addr <= CHR_END:
            ...
            return

        if PALETTE_START <= addr <= PALETTE_END:
            self.vram.write(self.normalize_palette_addr(addr), value)
            return

        self.vram.write(addr, value)

Important design choice:
Palette mirror logic belongs in PpuBus, not PPU. PPU handles register behavior;
PpuBus handles PPU memory address routing.

Out of scope:
    - actual RGB colors
    - rendering
    - background/sprite palette selection
    - nametable attribute decoding
    - separating palette RAM into its own storage class
"""

from emulator.bus.ppu_bus import PALETTE_END, PALETTE_SIZE, PALETTE_START, PpuBus


def test_ppu_bus_declares_palette_address_range_constants():
    """
    Objective:
    Name the PPU palette address range and its 32-byte mirrored window.
    """
    assert PALETTE_START == 0x3F00
    assert PALETTE_END == 0x3FFF
    assert PALETTE_SIZE == 0x20


def test_ppu_bus_can_read_back_direct_palette_address_write():
    """
    Objective:
    Palette addresses should be readable and writable through the public PpuBus
    API.

    This test intentionally uses PpuBus.read/write instead of inspecting the
    backing storage directly.
    """
    bus = PpuBus()

    bus.write(0x3F00, 0x21)

    assert bus.read(0x3F00) == 0x21


def test_palette_range_above_first_32_bytes_mirrors_down_to_palette_window():
    """
    Objective:
    $3F20-$3FFF should mirror the first 32 palette bytes at $3F00-$3F1F.

    Example:
        $3F20 mirrors $3F00
    """
    bus = PpuBus()

    bus.write(0x3F20, 0x11)

    assert bus.read(0x3F00) == 0x11
    assert bus.read(0x3F20) == 0x11


def test_last_palette_address_maps_inside_32_byte_palette_window():
    """
    Objective:
    The entire $3F00-$3FFF range mirrors into the 32-byte palette window.

    $3FFF maps to palette index $1F, which corresponds to address $3F1F in the
    normalized palette window.
    """
    bus = PpuBus()

    bus.write(0x3FFF, 0x44)

    assert bus.read(0x3F1F) == 0x44
    assert bus.read(0x3FFF) == 0x44


def test_palette_backdrop_mirror_3f10_maps_to_3f00():
    """
    Objective:
    $3F10 is a special palette mirror of $3F00.
    """
    bus = PpuBus()

    bus.write(0x3F10, 0x0F)

    assert bus.read(0x3F00) == 0x0F
    assert bus.read(0x3F10) == 0x0F


def test_palette_backdrop_mirrors_for_3f14_3f18_and_3f1c():
    """
    Objective:
    The other special backdrop mirrors should map to their matching background
    palette entries.

    Mirrors:
        $3F14 -> $3F04
        $3F18 -> $3F08
        $3F1C -> $3F0C
    """
    bus = PpuBus()

    bus.write(0x3F14, 0x14)
    bus.write(0x3F18, 0x18)
    bus.write(0x3F1C, 0x1C)

    assert bus.read(0x3F04) == 0x14
    assert bus.read(0x3F08) == 0x18
    assert bus.read(0x3F0C) == 0x1C


def test_palette_writes_store_only_low_8_bits():
    """
    Objective:
    Palette memory stores bytes. Values written through PpuBus should be masked to
    the low 8 bits by the backing memory behavior.
    """
    bus = PpuBus()

    bus.write(0x3F00, 0x123)

    assert bus.read(0x3F00) == 0x23
