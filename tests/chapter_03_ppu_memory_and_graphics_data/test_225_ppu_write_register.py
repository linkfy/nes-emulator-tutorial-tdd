"""
Add PPU.write_register(addr, value).

File to update:
    emulator/ppu/ppu.py

Method to implement:
    PPU.write_register(addr: int, value: int) -> None

Why this step exists:
The CPU writes to PPU registers through memory-mapped I/O. When the CPU writes
to address $2000, it is not writing RAM; it is updating the PPUCTRL register.

For this step, PPU.write_register receives normalized PPU register addresses in
the range $2000-$2007. CpuBus mirroring for $2008-$3FFF will be implemented in a
later step.

Writable registers for this simplified stage:

    $2000 -> ctrl
    $2001 -> mask
    $2003 -> oam_addr
    $2004 -> oam_data / OAMDATA port
    $2005 -> scroll
    $2006 -> addr
    $2007 -> data

Notice that $2002 is intentionally missing.

Why $2002 is not writable:
$2002 is PPUSTATUS. From the CPU side, it is read-only. Tests may directly set
ppu.status when they need to simulate a status value, but write_register($2002,
value) should fail.

One-byte policy:
PPU registers are 8-bit. For now, writes should keep only the low byte of the
value. This means writing 0x123 stores 0x23.

Suggested implementation pseudocode:

    def write_register(self, addr: int, value: int) -> None:
        value = value & 0xFF

        match addr:
            case 0x2000:
                self.ctrl = value
            case 0x2001:
                self.mask = value
            case 0x2003:
                self.oam_addr = value
            case 0x2004:
                self.oam_data = value
            case 0x2005:
                self.scroll = value
            case 0x2006:
                self.addr = value
            case 0x2007:
                self.data = value
            case _:
                raise ValueError(...)

Future note:
Later, $2004/OAMDATA becomes a port into internal OAM sprite memory. At that
point, writing $2004 may also increment oam_addr. This early test should not
require oam_addr to stay unchanged after an OAMDATA write.
"""

import pytest

from emulator.ppu.ppu import PPU


def test_ppu_write_register_updates_writeable_cpu_visible_registers():
    """
    Objective:
    Implement basic CPU-side writes to normalized PPU register addresses.
    """
    ppu = PPU()

    ppu.write_register(0x2000, 0x80)
    ppu.write_register(0x2001, 0x1E)
    ppu.write_register(0x2003, 0x02)

    assert ppu.oam_addr == 0x02

    ppu.write_register(0x2004, 0xAA)
    ppu.write_register(0x2005, 0x11)
    ppu.write_register(0x2006, 0x22)
    ppu.write_register(0x2007, 0x33)

    assert ppu.ctrl == 0x80
    assert ppu.mask == 0x1E
    assert ppu.oam_data == 0xAA
    assert ppu.scroll == 0x11
    assert ppu.addr == 0x22
    assert ppu.data == 0x33


def test_ppu_write_register_stores_only_low_byte():
    """
    Objective:
    PPU registers are 8-bit, so writes keep only the low byte.
    """
    ppu = PPU()

    ppu.write_register(0x2000, 0x123)

    assert ppu.ctrl == 0x23


def test_ppu_write_register_rejects_read_only_or_invalid_registers():
    """
    Objective:
    Unsupported writes should fail loudly.

    This includes $2002, because PPUSTATUS is read-only from the CPU side.
    """
    ppu = PPU()

    with pytest.raises(ValueError):
        ppu.write_register(0x2002, 0x80)

    with pytest.raises(ValueError):
        ppu.write_register(0x2008, 0x80)
