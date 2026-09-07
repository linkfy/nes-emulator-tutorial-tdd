"""
Connect PPU to PpuBus.

File to update:
    emulator/ppu/ppu.py

Field to add:
    ppu_bus: PpuBus = field(default_factory=PpuBus)

Why this step exists:
The PPU has registers that the CPU can access through CpuBus, but the PPU also
has its own address space:

    PPU address space: $0000-$3FFF

That address space should be routed by PpuBus.

This creates the stable boundary needed before implementing PPUADDR/PPUDATA:

    CPU writes $2006 / $2007
        -> CpuBus routes to PPU.write_register(...)
        -> PPU uses internal PPU address state
        -> PPU writes through PpuBus

Important dependency direction:

    PPU -> PpuBus -> VRAM / mapper CHR later

Not:

    PPU -> raw VRAM directly

Why this matters:
PPUDATA behavior should not need to change when PpuBus later becomes more
accurate. Today PpuBus may use big VRAM. Later it may route:

    $0000-$1FFF -> mapper CHR ROM/RAM
    $2000-$3EFF -> nametable VRAM/mirrors
    $3F00-$3FFF -> palette RAM/mirrors

Suggested implementation pseudocode:

    from dataclasses import dataclass, field
    from emulator.bus.ppu_bus import PpuBus


    @dataclass
    class PPU:
        ctrl: int = 0
        mask: int = 0
        status: int = 0
        oam_addr: int = 0
        oam_data: int = 0
        scroll: int = 0
        addr: int = 0
        data: int = 0

        ppu_bus: PpuBus = field(default_factory=PpuBus)

Out of scope:
    - PPUADDR latch behavior
    - PPUDATA writes through PpuBus
    - palette/nametable accuracy
    - CHR RAM writes
"""

from emulator.bus.ppu_bus import PpuBus
from emulator.ppu.ppu import PPU


def test_ppu_has_ppu_bus_field():
    """
    Objective:
    PPU should expose a ppu_bus field.
    """
    assert "ppu_bus" in PPU.__dataclass_fields__


def test_ppu_creates_default_ppu_bus():
    """
    Objective:
    A default PPU should have a PpuBus available.

    Why:
    Later, PPUDATA writes need a PPU-side bus without requiring every test to
    manually wire one.
    """
    ppu = PPU()

    assert isinstance(ppu.ppu_bus, PpuBus)


def test_each_ppu_gets_its_own_ppu_bus():
    """
    Objective:
    Avoid shared mutable PpuBus/VRAM state between PPU instances.
    """
    first_ppu = PPU()
    second_ppu = PPU()

    assert first_ppu.ppu_bus is not second_ppu.ppu_bus


def test_ppu_allows_injecting_specific_ppu_bus():
    """
    Objective:
    Tests and future emulator orchestration should be able to provide a specific
    PpuBus instance.

    Why:
    This makes it possible to inspect the exact PPU-side memory bus connected to
    the PPU.
    """
    ppu_bus = PpuBus()

    ppu = PPU(ppu_bus=ppu_bus)

    assert ppu.ppu_bus is ppu_bus
