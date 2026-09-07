"""
VALIDATION TEST: tiny iNES ROM writes to PPU registers.

This file is not a student implementation step.

There is nothing new to implement for this test. It exists only to validate that
the pieces built so far work together through their real boundaries:

    iNES bytes
        -> Cartridge.from_ines_bytes(data)
        -> CpuBus(cartridge=cartridge, ppu=ppu)
        -> CPU.reset()
        -> CPU.step()
        -> STA $2000 / STA $2001
        -> CpuBus.write(...)
        -> PPU.write_register(...)

Why this validation exists:
The previous tests verified PPU registers and CpuBus routing in isolation. This
test proves that actual CPU instructions fetched from cartridge PRG ROM can
write to PPU registers through the bus.

Tiny program placed at CPU address $8000:

    A9 80       LDA #$80
    8D 00 20    STA $2000
    A9 1E       LDA #$1E
    8D 01 20    STA $2001
    EA          NOP

Expected result:

    ppu.ctrl == $80
    ppu.mask == $1E

Out of scope:
    - rendering
    - VBlank timing
    - NMI behavior
    - OAMDMA
    - real PPUSCROLL/PPUADDR latch behavior
"""

from emulator.bus.cpu_bus import CpuBus
from emulator.cartridge.cartridge import Cartridge
from emulator.cartridge.ines import CHR_ROM_BANK_SIZE, PRG_ROM_BANK_SIZE
from emulator.cpu.cpu import CPU
from emulator.ppu.ppu import PPU


def make_tiny_ines_rom_that_writes_ppu_registers() -> bytes:
    """Build a minimal Mapper000 iNES ROM that writes PPUCTRL and PPUMASK."""
    header = bytearray(16)
    header[0:4] = b"NES\x1A"
    header[4] = 1  # one 16KB PRG ROM bank
    header[5] = 1  # one 8KB CHR ROM bank
    header[6] = 0x00  # mapper 0, no trainer
    header[7] = 0x00  # mapper 0

    prg_rom = bytearray(PRG_ROM_BANK_SIZE)

    program = [
        0xA9, 0x80,        # LDA #$80
        0x8D, 0x00, 0x20,  # STA $2000
        0xA9, 0x1E,        # LDA #$1E
        0x8D, 0x01, 0x20,  # STA $2001
        0xEA,              # NOP
    ]
    prg_rom[0 : len(program)] = bytes(program)

    # Reset vector: CPU $FFFC-$FFFD -> PRG offsets $3FFC-$3FFD for 16KB NROM.
    prg_rom[0x3FFC] = 0x00
    prg_rom[0x3FFD] = 0x80

    chr_rom = bytes([0x00]) * CHR_ROM_BANK_SIZE

    return bytes(header) + bytes(prg_rom) + chr_rom


def test_tiny_ines_rom_writes_ppu_registers_through_cpu_bus():
    """
    Validation objective:
    Prove that CPU instructions fetched from cartridge PRG ROM can update PPU
    registers through CpuBus.write routing.
    """
    cartridge = Cartridge.from_ines_bytes(make_tiny_ines_rom_that_writes_ppu_registers())
    ppu = PPU()
    bus = CpuBus(cartridge=cartridge, ppu=ppu)
    cpu = CPU(bus=bus)

    cpu.reset()

    cpu.step()  # LDA #$80
    cpu.step()  # STA $2000
    cpu.step()  # LDA #$1E
    cpu.step()  # STA $2001

    assert ppu.ctrl == 0x80
    assert ppu.mask == 0x1E
