"""
Add basic PpuBus read/write forwarding to VRAM.

File to update:
    emulator/bus/ppu_bus.py

Methods to implement:
    PpuBus.read(addr: int) -> int
    PpuBus.write(addr: int, value: int) -> None

Why this step exists:
Before PPUADDR/PPUDATA can write to video memory, the PPU needs a bus-like object
that can accept PPU addresses and perform memory access.

For this first read/write step, avoid testing the CHR region $0000-$1FFF. CHR
will be tested separately because it involves cartridge mapper behavior.

Use non-CHR addresses such as $2000 for now:

    PpuBus.write($2000, $AA)
    PpuBus.read($2000) -> $AA

Suggested implementation pseudocode for the non-CHR/default region:

    def read(self, addr: int) -> int:
        addr = addr & PPU_ADDRESS_MASK
        return self.vram.read(addr)

    def write(self, addr: int, value: int) -> None:
        addr = addr & PPU_ADDRESS_MASK
        self.vram.write(addr, value)

Later, these methods will grow sections for:
    - CHR area: $0000-$1FFF
    - nametable area: $2000-$3EFF
    - palette area: $3F00-$3FFF
"""

from emulator.bus.ppu_bus import PpuBus


def test_ppu_bus_has_read_and_write_methods():
    """
    Objective:
    PpuBus exposes the stable read/write API that PPU will use later.
    """
    assert hasattr(PpuBus, "read")
    assert callable(PpuBus.read)
    assert hasattr(PpuBus, "write")
    assert callable(PpuBus.write)


def test_ppu_bus_reads_value_from_vram_for_non_chr_address():
    """
    Objective:
    PpuBus.read should return the value stored in VRAM for non-CHR addresses.
    """
    bus = PpuBus()
    bus.vram.write(0x2000, 0xAA)

    assert bus.read(0x2000) == 0xAA


def test_ppu_bus_writes_value_to_vram_for_non_chr_address():
    """
    Objective:
    PpuBus.write should forward non-CHR writes to VRAM.
    """
    bus = PpuBus()

    bus.write(0x2000, 0xBB)

    assert bus.vram.read(0x2000) == 0xBB


def test_ppu_bus_masks_addresses_before_accessing_vram():
    """
    Objective:
    PpuBus owns PPU address normalization.

    Example:
    $6000 masked with $3FFF becomes $2000.
    """
    bus = PpuBus()

    bus.write(0x6000, 0xCC)

    assert bus.read(0x2000) == 0xCC
