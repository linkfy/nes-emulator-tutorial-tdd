"""
Route CpuBus writes from $2000-$3FFF to PPU registers.

File to update:
    emulator/bus/cpu_bus.py

Why this step exists:
CPU instructions such as STA absolute write to the CPU bus. When the target
address is inside $2000-$3FFF, the write should go to the PPU register window.

The same 8-byte mirroring rule used for reads applies to writes:

    unmirrored_addr = 0x2000 + ((addr - 0x2000) % 8)

Why this formula is necessary:
The PPU only has 8 CPU-visible base registers at $2000-$2007, but the CPU
address map repeats those registers until $3FFF.

Examples:

    $2000 -> $2000 -> ctrl
    $2008 -> $2000 -> ctrl
    $2009 -> $2001 -> mask
    $3FFF -> $2007 -> data

Suggested implementation pseudocode:

    if 0x2000 <= addr <= 0x3FFF:
        unmirrored_addr = 0x2000 + ((addr - 0x2000) % 8)
        self.ppu.write_register(unmirrored_addr, value)
        return

Boundary rule:
CpuBus should not directly set ppu.ctrl, ppu.mask, etc. It should route to
PPU.write_register so register semantics remain inside the PPU.
"""

import pytest

from emulator.bus.cpu_bus import CpuBus
from emulator.ppu.ppu import PPU


def test_cpu_bus_writes_base_ppu_registers():
    """
    Objective:
    CpuBus.write should forward base PPU register writes to PPU.write_register.
    """
    ppu = PPU()
    bus = CpuBus(ppu=ppu)

    bus.write(0x2000, 0x80)
    bus.write(0x2001, 0x1E)
    bus.write(0x2007, 0x55)

    assert ppu.ctrl == 0x80
    assert ppu.mask == 0x1E
    assert ppu.data == 0x55


def test_cpu_bus_writes_mirrored_ppu_registers():
    """
    Objective:
    CpuBus.write should mirror $2008-$3FFF back into $2000-$2007.
    """
    ppu = PPU()
    bus = CpuBus(ppu=ppu)

    bus.write(0x2008, 0x80)  # mirrors $2000
    bus.write(0x2009, 0x1E)  # mirrors $2001
    bus.write(0x3FFF, 0x55)  # mirrors $2007

    assert ppu.ctrl == 0x80
    assert ppu.mask == 0x1E
    assert ppu.data == 0x55


def test_cpu_bus_ppu_write_preserves_ppu_write_errors():
    """
    Objective:
    If the mirrored register is not writable, CpuBus should let the PPU reject
    the write.

    Example:
    $2002 is PPUSTATUS and is read-only from the CPU side in this simplified
    model.
    """
    bus = CpuBus(ppu=PPU())

    with pytest.raises(ValueError):
        bus.write(0x2002, 0x80)
