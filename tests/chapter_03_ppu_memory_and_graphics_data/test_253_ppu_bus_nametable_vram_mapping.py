"""
Implement PpuBus nametable VRAM address mapping.

Reference:
    https://www.nesdev.org/wiki/PPU_memory_map
    https://www.nesdev.org/wiki/PPU_nametables

File to update:
    emulator/bus/ppu_bus.py

Constants to add:
    NAMETABLE_START = 0x2000
    NAMETABLE_END = 0x3EFF
    NAMETABLE_SIZE = 0x0800

What is a nametable?
A nametable is background layout memory. It does not store pixels. It stores tile
numbers that tell the PPU which CHR tile to draw at each background position.

Simple example:

    PPU memory $2000 contains $24

Meaning:

    the top-left background cell uses CHR tile index $24

The PPU exposes four logical 1KB nametable areas:

    $2000-$23FF
    $2400-$27FF
    $2800-$2BFF
    $2C00-$2FFF

The range $3000-$3EFF mirrors $2000-$2EFF.

Tutorial simplification:
For now, use the existing large VRAM backing and normalize nametable addresses
into a simple 2KB window. Do not create a separate nametable RAM object yet.

Suggested implementation example:

    NAMETABLE_START = 0x2000
    NAMETABLE_END = 0x3EFF
    NAMETABLE_SIZE = 0x0800

    def normalize_nametable_addr(self, addr: int) -> int:
        if 0x3000 <= addr <= 0x3EFF:
            addr -= 0x1000

        index = (addr - NAMETABLE_START) % NAMETABLE_SIZE
        return NAMETABLE_START + index

    def read(self, addr: int) -> int:
        addr = addr & PPU_ADDRESS_MASK

        if CHR_START <= addr <= CHR_END:
            ...

        if NAMETABLE_START <= addr <= NAMETABLE_END:
            return self.vram.read(self.normalize_nametable_addr(addr))

        if PALETTE_START <= addr <= PALETTE_END:
            ...

        return self.vram.read(addr)

Out of scope:
    - horizontal/vertical cartridge mirroring
    - four-screen mirroring
    - attribute table interpretation
    - rendering
    - moving nametable storage out of the large VRAM backing
"""

from emulator.bus.ppu_bus import NAMETABLE_END, NAMETABLE_SIZE, NAMETABLE_START, PpuBus


def test_ppu_bus_declares_nametable_mapping_constants():
    """
    Objective:
    Name the PPU nametable range and the current 2KB backing window size.
    """
    assert NAMETABLE_START == 0x2000
    assert NAMETABLE_END == 0x3EFF
    assert NAMETABLE_SIZE == 0x0800


def test_ppu_bus_can_read_back_direct_nametable_address_write():
    """
    Objective:
    The first nametable address should be readable and writable through PpuBus.
    """
    bus = PpuBus()

    bus.write(0x2000, 0x24)

    assert bus.read(0x2000) == 0x24


def test_second_2kb_nametable_area_wraps_to_current_backing_window():
    """
    Objective:
    In this simplified 2KB model, $2800 wraps to $2000.

    This is not final cartridge mirroring behavior. It is the current tutorial
    model for keeping nametable storage inside the large VRAM backing.
    """
    bus = PpuBus()

    bus.write(0x2800, 0x55)

    assert bus.read(0x2000) == 0x55
    assert bus.read(0x2800) == 0x55


def test_end_of_logical_nametable_range_wraps_inside_2kb_window():
    """
    Objective:
    $2FFF maps to the last byte of the current 2KB nametable window: $27FF.
    """
    bus = PpuBus()

    bus.write(0x2FFF, 0x66)

    assert bus.read(0x27FF) == 0x66
    assert bus.read(0x2FFF) == 0x66


def test_3000_nametable_mirror_maps_to_2000():
    """
    Objective:
    $3000-$3EFF mirrors $2000-$2EFF. The first mirror address maps to $2000.
    """
    bus = PpuBus()

    bus.write(0x3000, 0x77)

    assert bus.read(0x2000) == 0x77
    assert bus.read(0x3000) == 0x77


def test_last_nametable_mirror_address_maps_through_2kb_window():
    """
    Objective:
    $3EFF first mirrors to $2EFF, then the current 2KB model maps that to $26FF.
    """
    bus = PpuBus()

    bus.write(0x3EFF, 0x88)

    assert bus.read(0x26FF) == 0x88
    assert bus.read(0x3EFF) == 0x88


def test_palette_range_remains_separate_from_nametable_range():
    """
    Objective:
    $3F00 is palette memory, not a nametable mirror.

    This protects the route order:
        CHR -> nametable -> palette
    """
    bus = PpuBus()

    bus.write(0x3000, 0x11)
    bus.write(0x3F00, 0x22)

    assert bus.read(0x2000) == 0x11
    assert bus.read(0x3F00) == 0x22
