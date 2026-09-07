"""
Add a default PPU to CpuBus.

File to update:
    emulator/bus/cpu_bus.py

What to add:
    CpuBus should own a PPU instance.

Why this step exists:
The NES CPU communicates with the PPU through memory-mapped registers. Before
CpuBus can route reads/writes in $2000-$3FFF, the bus needs a PPU object to
forward those accesses to.

Important design choice:
Use default_factory instead of PPU() directly in the dataclass field.

Why:
Each CpuBus should get its own PPU instance. Sharing one mutable PPU between bus
instances would create hidden coupling between tests and emulator instances.

Suggested implementation pseudocode:

    from dataclasses import dataclass, field
    from emulator.ppu.ppu import PPU


    @dataclass
    class CpuBus:
        ...
        ppu: PPU = field(default_factory=PPU)
"""

from emulator.bus.cpu_bus import CpuBus
from emulator.ppu.ppu import PPU


def test_cpu_bus_has_default_ppu_instance():
    """
    Objective:
    CpuBus should have a PPU available by default.
    """
    bus = CpuBus()

    assert isinstance(bus.ppu, PPU)


def test_each_cpu_bus_gets_its_own_ppu_instance():
    """
    Objective:
    Avoid shared mutable PPU state between CpuBus instances.

    Why:
    If two buses accidentally share the same PPU, one test or emulator instance
    could change PPU state observed by another. That kind of hidden coupling is
    difficult to debug.
    """
    first_bus = CpuBus()
    second_bus = CpuBus()

    assert first_bus.ppu is not second_bus.ppu


def test_cpu_bus_allows_injecting_specific_ppu_instance():
    """
    Objective:
    Tests and future emulator orchestration should be able to provide a specific
    PPU instance.

    Why:
    This makes integration tests easier because they can inspect the exact PPU
    object connected to the bus.
    """
    ppu = PPU()

    bus = CpuBus(ppu=ppu)

    assert bus.ppu is ppu
