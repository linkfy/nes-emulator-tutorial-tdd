"""
Implement OAMDMA at CPU address $4014.

File to update:
    emulator/bus/cpu_bus.py

Why this step exists:
Real NES games usually prepare sprite bytes in CPU memory and then trigger OAMDMA
to copy those bytes into PPU OAM. Even before sprite rendering exists, this copy
mechanism matters because it lets real-ROM startup code keep running and gives the
future sprite renderer real OAM data to consume.

What is OAM?
OAM means Object Attribute Memory. It is the PPU's 256-byte sprite memory:

    64 sprites * 4 bytes each = 256 bytes

Each sprite entry is shaped like:

    byte 0: Y position
    byte 1: tile index
    byte 2: attributes
    byte 3: X position

What is OAMDMA?
OAMDMA is a CPU-bus write mechanism. Writing one byte to $4014 selects a CPU
memory page and copies all 256 bytes from that page into PPU OAM.

Minimal example:

    CPU writes $02 to $4014

This means:

    copy CPU $0200-$02FF -> PPU.oam[0x00-0xFF]

Suggested implementation example:

    def write(self, addr: int, value: int) -> None:
        ...

        # OAMDMA: copy one CPU page into PPU OAM.
        if addr == 0x4014:
            page_start = (value & 0xFF) << 8

            for offset in range(256):
                self.ppu.oam[offset] = self.read(page_start + offset)

            return

        ...

Important detail:
OAMDMA should read through CpuBus.read(), not directly from raw RAM. The source is
CPU address space. Most games use pages like $0200-$02FF, but using bus reads keeps
the mechanism correct and avoids future refactors.

Common misconception:

    "OAMDMA means sprites are rendered."

No. This step only copies bytes into PPU.oam. Sprite decoding/rendering comes
later.

Read behavior:
$4014 is a write-triggered register for this tutorial. CpuBus.read($4014) should
remain unsupported for now.

Out of scope:
    - sprite rendering
    - sprite priority
    - sprite transparency
    - sprite 0 hit
    - sprite overflow
    - 513/514 CPU cycle DMA stall timing
    - controller $4016
"""

import pytest

from emulator.bus.cpu_bus import CpuBus
from emulator.memory.fake_rom import FakeROM


def test_oamdma_4014_copies_256_bytes_from_selected_cpu_page_to_ppu_oam():
    """
    Objective:
    Writing a page number to $4014 copies exactly one 256-byte CPU memory page into
    PPU OAM.

    Example:
        write $02 to $4014
        copy CPU $0200-$02FF -> PPU.oam[0x00-0xFF]
    """
    bus = CpuBus(program_rom=FakeROM())

    for offset in range(256):
        bus.write(0x0200 + offset, offset ^ 0x5A)

    bus.write(0x4014, 0x02)

    assert list(bus.ppu.oam) == [(offset ^ 0x5A) for offset in range(256)]


def test_oamdma_source_page_is_value_shifted_left_by_8():
    """
    Objective:
    The value written to $4014 selects the high byte of the source address.

    Writing $03 means source page $0300-$03FF, not $0003-$0102.
    """
    bus = CpuBus(program_rom=FakeROM())

    for offset in range(256):
        bus.write(0x0200 + offset, 0x22)
        bus.write(0x0300 + offset, 0x33)

    bus.write(0x4014, 0x03)

    assert all(value == 0x33 for value in bus.ppu.oam)


def test_oamdma_reads_source_bytes_through_cpu_bus_read():
    """
    Objective:
    OAMDMA source reads should go through CpuBus.read().

    This matters because OAMDMA reads from CPU address space, not only raw internal
    RAM. This test uses RAM mirroring to prove bus behavior is used:

        source page $0800-$08FF mirrors internal RAM $0000-$00FF
    """
    bus = CpuBus(program_rom=FakeROM())

    for offset in range(256):
        bus.write(0x0000 + offset, (offset + 7) & 0xFF)

    bus.write(0x4014, 0x08)

    assert list(bus.ppu.oam) == [((offset + 7) & 0xFF) for offset in range(256)]


def test_oamdma_overwrites_all_oam_bytes():
    """
    Objective:
    DMA writes all 256 OAM bytes. It should not only update the first sprite entry
    or stop early.
    """
    bus = CpuBus(program_rom=FakeROM())
    bus.ppu.oam[:] = bytes([0xEE]) * 256

    for offset in range(256):
        bus.write(0x0400 + offset, offset)

    bus.write(0x4014, 0x04)

    assert bus.ppu.oam[0] == 0x00
    assert bus.ppu.oam[1] == 0x01
    assert bus.ppu.oam[254] == 0xFE
    assert bus.ppu.oam[255] == 0xFF
    assert list(bus.ppu.oam) == list(range(256))


def test_oamdma_read_4014_remains_unsupported():
    """
    Objective:
    $4014 is implemented as a write-triggered DMA register in this tutorial.

    A CPU read from $4014 should not pretend to return meaningful DMA state.
    """
    bus = CpuBus(program_rom=FakeROM())

    with pytest.raises(ValueError, match="Unsupported CPU bus read: 4014"):
        bus.read(0x4014)


def test_apu_audio_noop_still_works_after_oamdma_step():
    """
    Objective:
    OAMDMA $4014 should coexist with the previous APU/audio no-op step.

    The nearby audio addresses remain recognized out-of-scope no-ops.
    $4017 remains simplified too: writes are APU frame-counter no-ops, while reads
    return 0 for out-of-scope controller port 2 / expansion input.
    """
    bus = CpuBus(program_rom=FakeROM())

    bus.write(0x4000, 0x12)
    bus.write(0x4013, 0x34)
    bus.write(0x4015, 0x56)
    bus.write(0x4017, 0x78)

    assert bus.read(0x4000) == 0
    assert bus.read(0x4013) == 0
    assert bus.read(0x4015) == 0
    assert bus.read(0x4017) == 0


def test_oamdma_only_copies_bytes_and_does_not_render_sprites():
    """
    Objective:
    This step transfers sprite data into PPU.oam only. It should not add sprite
    rendering as a hidden side effect.

    Rendering sprites will be a later explicit tutorial step.
    """
    bus = CpuBus(program_rom=FakeROM())

    for offset in range(256):
        bus.write(0x0200 + offset, offset)

    bus.write(0x4014, 0x02)

    assert not hasattr(bus.ppu, "render_sprites")
