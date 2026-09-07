"""
Route CpuBus reads from $2000-$3FFF to PPU registers.

File to update:
    emulator/bus/cpu_bus.py

Why this step exists:
The CPU sees PPU registers through the CPU address map:

    $2000-$3FFF -> PPU registers, mirrored every 8 bytes

Only $2000-$2007 are the base PPU register addresses. The rest of the range is
mirrors of those same 8 registers.

Mirroring formula:

    unmirrored_addr = 0x2000 + ((addr - 0x2000) % 8)

How it works:
    1. addr - 0x2000 converts the CPU address into an offset from the start of
       the PPU register window.
    2. % 8 folds that offset into the repeating 8-register range.
    3. + 0x2000 converts the folded offset back into a base PPU register address.

Examples:

    $2002:
        0x2000 + ((0x2002 - 0x2000) % 8)
        = 0x2000 + (2 % 8)
        = $2002

    $200A:
        0x2000 + ((0x200A - 0x2000) % 8)
        = 0x2000 + (10 % 8)
        = $2002

    $3FFF:
        0x2000 + ((0x3FFF - 0x2000) % 8)
        = 0x2000 + (8191 % 8)
        = $2007

Why CpuBus owns the formula:
Mirroring is CPU address-map decoding. PPU.read_register should receive a
normalized register address in $2000-$2007.

Suggested implementation pseudocode:

    if 0x2000 <= addr <= 0x3FFF:
        unmirrored_addr = 0x2000 + ((addr - 0x2000) % 8)
        return self.ppu.read_register(unmirrored_addr)

"""

import pytest

from emulator.bus.cpu_bus import CpuBus


class FakePPUForReadRouting:
    """Small test double that lets this file test CpuBus routing only."""

    def __init__(self):
        self.values = {
            0x2002: 0x80,
            0x2004: 0x44,
            0x2007: 0x55,
        }

    def read_register(self, addr: int) -> int:
        if addr not in self.values:
            raise ValueError("Unsupported fake PPU read")
        return self.values[addr]

    def write_register(self, addr: int, value: int) -> None:
        raise NotImplementedError("This fake is only for read routing tests")


def test_cpu_bus_reads_base_ppu_registers():
    """
    Objective:
    CpuBus.read should forward base PPU register reads to PPU.read_register.
    """
    ppu = FakePPUForReadRouting()
    bus = CpuBus(ppu=ppu)

    assert bus.read(0x2002) == 0x80
    assert bus.read(0x2004) == 0x44
    assert bus.read(0x2007) == 0x55


def test_cpu_bus_reads_mirrored_ppu_registers():
    """
    Objective:
    CpuBus.read should mirror $2008-$3FFF back into $2000-$2007.

    Examples:
        $200A mirrors $2002
        $200C mirrors $2004
        $3FFF mirrors $2007
    """
    ppu = FakePPUForReadRouting()
    bus = CpuBus(ppu=ppu)

    assert bus.read(0x200A) == 0x80
    assert bus.read(0x200C) == 0x44
    assert bus.read(0x3FFF) == 0x55


def test_cpu_bus_ppu_read_preserves_ppu_read_errors():
    """
    Objective:
    If the mirrored register is not readable, CpuBus should let the PPU reject
    the read.

    Why:
    CpuBus owns address routing. PPU owns register semantics.
    """
    bus = CpuBus(ppu=FakePPUForReadRouting())

    with pytest.raises(ValueError):
        bus.read(0x2000)
