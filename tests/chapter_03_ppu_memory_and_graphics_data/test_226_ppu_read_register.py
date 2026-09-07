"""
Add PPU.read_register(addr).

File to update:
    emulator/ppu/ppu.py

Method to implement:
    PPU.read_register(addr: int) -> int

Why this step exists:
Some PPU registers can be read by the CPU. Reads are also memory-mapped I/O, not
normal RAM access. The PPU decides what value the CPU receives.

Readable registers for this simplified stage:

    $2002 -> status
    $2007 -> data

Note about $2004/OAMDATA:
OAMDATA is readable, but later it becomes a port into internal OAM sprite memory.
That behavior is tested in the OAM-specific step. This early read-register test
does not lock itself to the old placeholder `oam_data` field behavior.

Note about $2007/PPUDATA:
PPUDATA is readable, but later it becomes a buffered PPU memory read port. That
behavior is tested in the PPUDATA-specific step. This early read-register test
does not lock itself to the old placeholder `data` field behavior.

Why only these:
Several PPU registers are primarily write-only from the CPU side. Unsupported
reads should fail loudly instead of pretending all PPU registers are normal RAM.

Important future accuracy note:
Real PPUSTATUS reads have side effects. Reading $2002 clears the VBlank flag and
resets the internal address/scroll latch. We intentionally do not model those
side effects yet. This step only creates the basic register boundary.

Suggested implementation pseudocode:

    def read_register(self, addr: int) -> int:
        match addr:
            case 0x2002:
                return self.status
            case 0x2007:
                return self.data
            case _:
                raise ValueError(...)
"""

import pytest

from emulator.ppu.ppu import PPU


def test_ppu_read_register_returns_cpu_readable_registers():
    """
    Objective:
    Implement basic CPU-side reads from normalized PPU register addresses.
    """
    ppu = PPU()
    ppu.status = 0x80

    assert ppu.read_register(0x2002) == 0x80


def test_ppu_read_register_rejects_write_only_or_invalid_registers():
    """
    Objective:
    Unsupported reads should fail loudly.

    For example, $2000/PPUCTRL is write-only for our current CPU-side model.
    """
    ppu = PPU()

    with pytest.raises(ValueError):
        ppu.read_register(0x2000)

    with pytest.raises(ValueError):
        ppu.read_register(0x2008)
