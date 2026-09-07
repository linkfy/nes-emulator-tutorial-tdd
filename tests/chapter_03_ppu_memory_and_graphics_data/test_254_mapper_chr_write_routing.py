"""
Implement CHR write routing through the mapper.

Reference:
    https://www.nesdev.org/wiki/PPU_memory_map
    https://www.nesdev.org/wiki/NROM

Files to update:
    emulator/cartridge/mapper_interface.py
    emulator/cartridge/mapper000.py
    emulator/bus/ppu_bus.py

What is CHR memory?
CHR memory is where the PPU reads tile pattern bytes from. The PPU address range
$0000-$1FFF is the CHR area.

Simple example:

    PPU reads $0000
    mapper returns the first byte of CHR ROM

For official Mapper000/NROM in this tutorial, CHR is ROM, so writes are rejected.

Why this step exists:
PpuBus should only route addresses. It should not decide whether CHR writes are
legal. The mapper owns that policy.

Correct responsibility split:

    PpuBus.write($0000-$1FFF, value)
        -> mapper.write_chr(addr, value)

    Mapper000.write_chr(addr, value)
        -> rejects writes because official Mapper000 CHR ROM is read-only

Suggested implementation example:

    class MapperInterface(Protocol):
        def read_prg(self, addr: int) -> int:
            ...

        def read_chr(self, addr: int) -> int:
            ...

        def write_chr(self, addr: int, value: int) -> None:
            ...

    class Mapper000:
        def write_chr(self, addr: int, value: int) -> None:
            if not (CHR_ROM_START <= addr <= CHR_ROM_END):
                raise ValueError(f"Address out of CHR ROM range: {addr:04X}")

            raise ValueError("CHR ROM is read-only for official Mapper000")

    class PpuBus:
        def write(self, addr: int, value: int) -> None:
            addr = addr & PPU_ADDRESS_MASK

            if CHR_START <= addr <= CHR_END:
                if self.mapper is not None:
                    self.mapper.write_chr(addr, value)
                    return

                self.vram.write(addr, value)
                return

Out of scope:
    - CHR RAM support
    - unlicensed/homebrew Mapper000 variants with writable CHR RAM
    - mapper bank switching
    - rendering CHR tiles
"""

import pytest

from emulator.bus.ppu_bus import PpuBus
from emulator.cartridge.mapper000 import CHR_ROM_SIZE, Mapper000


class FakeMapperForChrWrites:
    """Small test double that records CHR write calls from PpuBus."""

    def __init__(self):
        self.write_chr_calls = []

    def read_prg(self, addr: int) -> int:
        raise AssertionError("read_prg is not used by this test")

    def read_chr(self, addr: int) -> int:
        raise AssertionError("read_chr is not used by this test")

    def write_chr(self, addr: int, value: int) -> None:
        self.write_chr_calls.append((addr, value))


def make_mapper000() -> Mapper000:
    """Create a minimal official Mapper000-style mapper with 8KB CHR ROM."""
    return Mapper000(
        prg_rom=bytes([0xEA]) * (16 * 1024),
        chr_rom=bytes([0x00]) * CHR_ROM_SIZE,
    )


def test_mapper_interface_requires_write_chr_method():
    """
    Objective:
    Mappers expose a write_chr method so PpuBus can delegate CHR writes.
    """
    mapper = make_mapper000()

    assert hasattr(mapper, "write_chr")
    assert callable(mapper.write_chr)


def test_mapper000_rejects_chr_rom_writes_inside_valid_chr_range():
    """
    Objective:
    Official Mapper000/NROM uses CHR ROM in this tutorial, so valid CHR writes are
    rejected as read-only.
    """
    mapper = make_mapper000()

    with pytest.raises(ValueError, match="CHR ROM is read-only"):
        mapper.write_chr(0x0000, 0x12)


def test_mapper000_rejects_chr_writes_outside_chr_range_with_range_error():
    """
    Objective:
    Mapper000 should still validate the CHR address range before applying its
    read-only policy.
    """
    mapper = make_mapper000()

    with pytest.raises(ValueError, match="Address out of CHR ROM range"):
        mapper.write_chr(0x2000, 0x12)


def test_ppu_bus_delegates_chr_writes_to_mapper_when_mapper_exists():
    """
    Objective:
    PpuBus should route CHR writes to mapper.write_chr instead of deciding CHR
    write legality itself.
    """
    mapper = FakeMapperForChrWrites()
    bus = PpuBus(mapper=mapper)

    bus.write(0x0007, 0xAB)

    assert mapper.write_chr_calls == [(0x0007, 0xAB)]


def test_ppu_bus_masks_chr_write_address_before_delegating_to_mapper():
    """
    Objective:
    PpuBus owns 14-bit PPU address normalization before routing the access.

    Example:
        $4007 masked by $3FFF becomes $0007
    """
    mapper = FakeMapperForChrWrites()
    bus = PpuBus(mapper=mapper)

    bus.write(0x4007, 0xCD)

    assert mapper.write_chr_calls == [(0x0007, 0xCD)]


def test_ppu_bus_without_mapper_still_allows_local_chr_vram_write():
    """
    Objective:
    Keep the early no-cartridge tutorial path working: without a mapper, CHR-area
    writes still use the local PpuBus VRAM backing.
    """
    bus = PpuBus(mapper=None)

    bus.write(0x0000, 0xEF)

    assert bus.read(0x0000) == 0xEF
