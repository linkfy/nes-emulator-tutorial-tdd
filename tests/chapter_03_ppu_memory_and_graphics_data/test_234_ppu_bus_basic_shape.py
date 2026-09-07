"""
Create the basic PpuBus shape.

Files to create/update:
    emulator/bus/ppu_bus.py

Class to implement:
    PpuBus

Why this step exists:
The NES has two different address spaces:

    CPU address space: $0000-$FFFF
        routed by CpuBus

    PPU address space: $0000-$3FFF
        routed by PpuBus

The PPU should not write directly to raw VRAM forever. It should talk to a stable
PPU-address-space boundary:

    PPU -> PpuBus -> VRAM / mapper CHR / palette RAM later

This allows PPUDATA behavior to stay stable while PpuBus internals become more
accurate over time.

Important constant:

    PPU_ADDRESS_MASK = 0x3FFF

Why:
PPU addresses are 14-bit. Masking with 0x3FFF folds any address into the PPU
addressable range $0000-$3FFF.

Initial storage:
For now, PpuBus owns a big VRAM backing store. This is a temporary simplification
that lets us build PPUADDR/PPUDATA before full nametable/palette accuracy.

Suggested implementation pseudocode:

    from dataclasses import dataclass, field
    from typing import Optional

    from emulator.memory.vram import VRAM
    from emulator.cartridge.mapper_interface import MapperInterface

    PPU_ADDRESS_MASK = 0x3FFF


    @dataclass
    class PpuBus:
        vram: VRAM = field(default_factory=VRAM)
        mapper: Optional[MapperInterface] = None
"""

import dataclasses
from pathlib import Path

from emulator.bus.ppu_bus import PPU_ADDRESS_MASK, PpuBus
from emulator.memory.vram import VRAM


def test_ppu_bus_file_exists():
    """
    Objective:
    Create emulator/bus/ppu_bus.py.
    """
    assert Path("emulator/bus/ppu_bus.py").exists()


def test_ppu_bus_has_address_mask_and_vram_backing_store():
    """
    Objective:
    PpuBus should own PPU address normalization and a temporary VRAM backing
    store.
    """
    assert PPU_ADDRESS_MASK == 0x3FFF
    assert dataclasses.is_dataclass(PpuBus)

    bus = PpuBus()

    assert isinstance(bus.vram, VRAM)


def test_each_ppu_bus_gets_its_own_vram():
    """
    Objective:
    Avoid shared mutable VRAM between PpuBus instances.
    """
    first_bus = PpuBus()
    second_bus = PpuBus()

    assert first_bus.vram is not second_bus.vram
