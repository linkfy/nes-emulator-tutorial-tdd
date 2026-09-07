"""
VALIDATION TEST: decode one CHR tile from a tiny iNES ROM through the real path.

This file is not a student implementation step.

There is nothing new to implement for this test. It exists only to validate that
the graphics data pieces built so far work together through their real
boundaries:

    iNES bytes
        -> Cartridge.from_ines_bytes(data)
        -> CpuBus(cartridge=cartridge, ppu=ppu)
        -> mapper connected to ppu.ppu_bus
        -> ppu.ppu_bus.read($0000-$000F)
        -> decode_chr_tile(tile_bytes)
        -> 8x8 grid of color indexes

Why this validation exists:
Previous tests verified CHR ROM reads, PpuBus mapper routing, and CHR tile
decoding separately. This test proves that CHR bytes from an actual tiny iNES ROM
can flow through the cartridge/mapper/PPU-bus path and be decoded as graphics
data.

Important:
This is still not rendering. The decoder returns palette indexes 0-3, not final
RGB colors and not a screen framebuffer.

Known first CHR tile used by this test:

    low plane row 0:   1100_0011
    high plane row 0:  1010_0101

Decoded first row:

    [3, 1, 2, 0, 0, 2, 1, 3]

Out of scope:
    - pattern table image rendering
    - nametable background rendering
    - palette color lookup
    - VBlank/NMI timing
    - sprites
"""

from emulator.bus.cpu_bus import CpuBus
from emulator.cartridge.cartridge import Cartridge
from emulator.cartridge.ines import CHR_ROM_BANK_SIZE, PRG_ROM_BANK_SIZE
from emulator.ppu.chr_decoder import decode_chr_tile
from emulator.ppu.ppu import PPU


def make_tiny_ines_rom_with_known_chr_tile() -> bytes:
    """Build a minimal Mapper000 iNES ROM whose first CHR tile is known."""
    header = bytearray(16)
    header[0:4] = b"NES\x1A"
    header[4] = 1  # one 16KB PRG ROM bank
    header[5] = 1  # one 8KB CHR ROM bank
    header[6] = 0x00  # mapper 0, no trainer
    header[7] = 0x00  # mapper 0

    prg_rom = bytearray(PRG_ROM_BANK_SIZE)

    # Reset vector: CPU $FFFC-$FFFD -> PRG offsets $3FFC-$3FFD for 16KB NROM.
    # The CPU is not stepped in this validation, but a valid reset vector keeps
    # the tiny ROM structurally similar to earlier validation ROMs.
    prg_rom[0x3FFC] = 0x00
    prg_rom[0x3FFD] = 0x80

    chr_rom = bytearray(CHR_ROM_BANK_SIZE)

    # First tile, row 0:
    # low plane byte  = 1100_0011
    # high plane byte = 1010_0101
    chr_rom[0] = 0b1100_0011
    chr_rom[8] = 0b1010_0101

    return bytes(header) + bytes(prg_rom) + bytes(chr_rom)


def test_decode_chr_tile_from_tiny_ines_rom_through_ppu_bus_mapper_path():
    """
    Validation objective:
    Prove that CHR ROM bytes from a cartridge-backed iNES ROM can be read through
    PpuBus mapper routing and decoded into an 8x8 tile grid.
    """
    cartridge = Cartridge.from_ines_bytes(make_tiny_ines_rom_with_known_chr_tile())
    ppu = PPU()
    CpuBus(cartridge=cartridge, ppu=ppu)

    tile_bytes = bytes(ppu.ppu_bus.read(addr) for addr in range(16))
    pixels = decode_chr_tile(tile_bytes)

    assert pixels[0] == [3, 1, 2, 0, 0, 2, 1, 3]
    assert pixels[1:] == [[0] * 8 for _ in range(7)]
