"""
VALIDATION TEST: tiny iNES ROM writes to PPU memory through PPUADDR/PPUDATA.

This file is not a student implementation step.

There is nothing new to implement for this test. It exists only to validate that
the pieces built so far work together through their real boundaries:

    iNES bytes
        -> Cartridge.from_ines_bytes(data)
        -> CpuBus(cartridge=cartridge, ppu=ppu)
        -> CPU.reset()
        -> CPU.step()
        -> STA $2006 / STA $2007
        -> CpuBus.write(...)
        -> PPU.write_register(...)
        -> PPUADDR sets vram_addr
        -> PPUDATA writes through PpuBus
        -> VRAM stores the byte

Why this validation exists:
Previous tests verified PPUADDR, PPUDATA, PPUCTRL increment behavior, PpuBus, and
CpuBus routing in isolation. This test proves a real CPU program fetched from a
tiny cartridge-backed iNES ROM can write into PPU-side memory.

Tiny program placed at CPU address $8000:

    A9 20       LDA #$20
    8D 06 20    STA $2006    ; PPUADDR high byte
    A9 00       LDA #$00
    8D 06 20    STA $2006    ; PPUADDR low byte
    A9 AA       LDA #$AA
    8D 07 20    STA $2007    ; PPUDATA write to PPU memory at $2000
    EA          NOP

Expected result:

    ppu.ppu_bus.read($2000) == $AA
    ppu.vram_addr == $2001

Out of scope:
    - rendering
    - nametable mirroring accuracy
    - palette RAM accuracy
    - CHR RAM writes
    - PPUDATA reads/read buffering
    - VBlank/NMI timing
"""

from emulator.bus.cpu_bus import CpuBus
from emulator.cartridge.cartridge import Cartridge
from emulator.cartridge.ines import CHR_ROM_BANK_SIZE, PRG_ROM_BANK_SIZE
from emulator.cpu.cpu import CPU
from emulator.ppu.ppu import PPU


def make_tiny_ines_rom_that_writes_ppu_memory() -> bytes:
    """Build a minimal Mapper000 iNES ROM that writes one byte to PPU memory."""
    header = bytearray(16)
    header[0:4] = b"NES\x1A"
    header[4] = 1  # one 16KB PRG ROM bank
    header[5] = 1  # one 8KB CHR ROM bank
    header[6] = 0x00  # mapper 0, no trainer
    header[7] = 0x00  # mapper 0

    prg_rom = bytearray(PRG_ROM_BANK_SIZE)

    program = [
        0xA9, 0x20,        # LDA #$20
        0x8D, 0x06, 0x20,  # STA $2006
        0xA9, 0x00,        # LDA #$00
        0x8D, 0x06, 0x20,  # STA $2006
        0xA9, 0xAA,        # LDA #$AA
        0x8D, 0x07, 0x20,  # STA $2007
        0xEA,              # NOP
    ]
    prg_rom[0 : len(program)] = bytes(program)

    # Reset vector: CPU $FFFC-$FFFD -> PRG offsets $3FFC-$3FFD for 16KB NROM.
    prg_rom[0x3FFC] = 0x00
    prg_rom[0x3FFD] = 0x80

    chr_rom = bytes([0x00]) * CHR_ROM_BANK_SIZE

    return bytes(header) + bytes(prg_rom) + chr_rom


def test_tiny_ines_rom_writes_ppu_memory_through_ppuaddr_and_ppudata():
    """
    Validation objective:
    Prove that CPU instructions can set PPUADDR and write PPUDATA into PPU-side
    memory through CpuBus, PPU, PpuBus, and VRAM.
    """
    cartridge = Cartridge.from_ines_bytes(make_tiny_ines_rom_that_writes_ppu_memory())
    ppu = PPU()
    bus = CpuBus(cartridge=cartridge, ppu=ppu)
    cpu = CPU(bus=bus)

    cpu.reset()

    cpu.step()  # LDA #$20
    cpu.step()  # STA $2006
    cpu.step()  # LDA #$00
    cpu.step()  # STA $2006
    cpu.step()  # LDA #$AA
    cpu.step()  # STA $2007

    assert ppu.ppu_bus.read(0x2000) == 0xAA
    assert ppu.vram_addr == 0x2001
