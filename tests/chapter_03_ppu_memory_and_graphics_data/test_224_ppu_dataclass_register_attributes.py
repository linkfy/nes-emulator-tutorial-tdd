"""
Create the PPU dataclass with explicit register attributes.

File to create:
    emulator/ppu/ppu.py

Class to implement:
    PPU

Why this step exists:
The CPU communicates with the NES Picture Processing Unit through CPU-visible
hardware registers at addresses $2000-$2007. These are not normal RAM bytes;
they are named hardware registers with specific meanings.

For this first PPU step, we only create the register state. We do not implement
reads, writes, rendering, VBlank, scrolling, VRAM, or DMA yet.

This test verifies that the original CPU-visible PPU register fields exist. It
does not require these to be the only fields forever. Later steps may add
internal PPU state such as ppu_bus, vram_addr, or addr_latch.

CPU-visible PPU register window:

    $2000 PPUCTRL   -> ctrl
    $2001 PPUMASK   -> mask
    $2002 PPUSTATUS -> status
    $2003 OAMADDR   -> oam_addr
    $2004 OAMDATA   -> oam_data
    $2005 PPUSCROLL -> scroll
    $2006 PPUADDR   -> addr
    $2007 PPUDATA   -> data

Important design choice:
Use explicit integer fields, similar to the CPU registers. This keeps debugging
simple and makes the hardware model visible:

    assert ppu.ctrl == 0x80

Do not add OAMDMA here. OAMDMA is accessed at CPU address $4014 and triggers a
256-byte DMA copy into sprite memory. It is related to the PPU, but it is not
part of the normal $2000-$2007 PPU register window.

Suggested implementation pseudocode:

    from dataclasses import dataclass


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
"""

import dataclasses
from pathlib import Path

from emulator.ppu.ppu import PPU


def test_ppu_file_exists():
    """
    Objective:
    Create emulator/ppu/ppu.py.

    Why:
    The PPU is its own hardware subsystem. Keeping it in its own module prevents
    CpuBus from becoming responsible for PPU state and behavior.
    """
    assert Path("emulator/ppu/ppu.py").exists()


def test_ppu_is_dataclass_with_explicit_register_attributes():
    """
    Objective:
    Define PPU as a dataclass with explicit fields for the CPU-visible PPU
    registers $2000-$2007.
    """
    assert dataclasses.is_dataclass(PPU)
    required_register_fields = [
        "ctrl",
        "mask",
        "status",
        "oam_addr",
        "oam_data",
        "scroll",
        "addr",
        "data",
    ]

    for field_name in required_register_fields:
        assert field_name in PPU.__dataclass_fields__

    ppu = PPU()

    assert ppu.ctrl == 0
    assert ppu.mask == 0
    assert ppu.status == 0
    assert ppu.oam_addr == 0
    assert ppu.oam_data == 0
    assert ppu.scroll == 0
    assert ppu.addr == 0
    assert ppu.data == 0
