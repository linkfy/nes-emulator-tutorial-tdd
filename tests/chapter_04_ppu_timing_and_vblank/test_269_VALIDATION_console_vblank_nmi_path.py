"""
VALIDATION: Console.step drives the full VBlank NMI path.

No new implementation should be required for this test if steps 259-268 are
complete.

References:
    https://www.nesdev.org/wiki/PPU_registers#PPUCTRL
    https://www.nesdev.org/wiki/PPU_registers#Vblank_NMI
    https://www.nesdev.org/wiki/CPU_interrupts

Why this validation exists:
Previous tests verified each mechanism separately:

    PPU.step() advances timing
    PPU enters VBlank and sets VBLANK_STARTED
    PPUCTRL bit 7 enables NMI requests
    CPU.step() returns CPU cycles
    Console.step() advances PPU by cpu_cycles * 3
    Console consumes ppu.nmi_requested
    CPU.interrupt_nmi() jumps through $FFFA/$FFFB

This test validates that those pieces work together in one small machine-level
scenario.

End-to-end path being validated:

    CPU executes LDA #$80
        -> A = $80

    CPU executes STA $2000
        -> CpuBus routes $2000 to PPUCTRL
        -> PPUCTRL bit 7 enables NMI

    Console.step() keeps advancing CPU and PPU together
        -> CPU cycles advance PPU by cycles * 3
        -> PPU enters VBlank
        -> PPU sets nmi_requested = True
        -> Console consumes the request
        -> CPU.interrupt_nmi() reads $FFFA/$FFFB
        -> CPU jumps to the NMI handler address

Tiny program used in this validation:

    $8000: A9 80       LDA #$80       ; set PPUCTRL NMI-enable bit
    $8002: 8D 00 20    STA $2000      ; write A to PPUCTRL
    $8005: EA          NOP            ; wait while PPU reaches VBlank
    $8006: EA          NOP
    ...

NMI vector setup:

    $FFFA = $00
    $FFFB = $90

Expected result:

    CPU PC becomes $9000 after Console consumes the VBlank NMI request.

Important:
This is still simplified timing. The test intentionally places the PPU near
VBlank so the validation is fast and deterministic. This is not dot-accurate NMI
latency testing.

Out of scope:
    - rendering pixels
    - PPU sprite behavior
    - OAM DMA
    - controller input
    - exact NMI latency
    - dynamic CPU cycle penalties
"""

from emulator.console import Console
from emulator.ppu.ppu import (
    CTRL_NMI_ENABLE,
    PPU_CYCLES_PER_SCANLINE,
    PPU_VBLANK_START_SCANLINE,
    VBLANK_STARTED,
)
from tests.helpers import load_program, make_cpu_with_rom


def write_nmi_vector(rom, addr: int) -> None:
    """Install the NMI vector in FakeROM."""
    rom.write(0x7FFA, addr & 0xFF)
    rom.write(0x7FFB, (addr >> 8) & 0xFF)


def make_console_with_fake_rom():
    """Build a small Console using the same PPU instance attached to CpuBus."""
    cpu, bus, rom = make_cpu_with_rom()
    return Console(cpu=cpu, ppu=bus.ppu), cpu, bus.ppu, rom


def test_VALIDATION_tiny_program_enables_ppu_nmi_and_reaches_nmi_handler():
    """
    VALIDATION:
    A tiny CPU program can enable PPU NMI, then Console.step() can drive the PPU
    into VBlank and route the NMI request back into CPU.interrupt_nmi().

    No new implementation is required by this test. If it fails, inspect the
    earlier mechanisms: CpuBus PPU register routing, PPU timing, PPU NMI request,
    CPU.step cycles, Console.step, or CPU.interrupt_nmi().
    """
    console, cpu, ppu, rom = make_console_with_fake_rom()
    write_nmi_vector(rom, 0x9000)

    # Program:
    #   LDA #$80
    #   STA $2000
    #   NOP
    program = [
        0xA9, CTRL_NMI_ENABLE,
        0x8D, 0x00, 0x20,
        0xEA,
    ]
    load_program(rom, 0x8000, program)

    cpu.pc = 0x8000
    cpu.s = 0xFD

    # Put the PPU close to VBlank so this validation stays small and deterministic.
    # The first two CPU instructions enable NMI before VBlank is reached.
    ppu.scanline = PPU_VBLANK_START_SCANLINE - 1
    # The next three instructions advance the PPU by:
    #   LDA #imm: 2 CPU cycles * 3 = 6 PPU cycles
    #   STA abs:  4 CPU cycles * 3 = 12 PPU cycles
    #   NOP:      2 CPU cycles * 3 = 6 PPU cycles
    # Total: 24 PPU cycles, exactly enough to enter VBlank here.
    ppu.cycle = PPU_CYCLES_PER_SCANLINE - 24

    # Step 1: LDA #$80. This prepares the value for PPUCTRL.
    cycles = console.step()
    assert cycles == 2
    assert cpu.a == CTRL_NMI_ENABLE
    assert cpu.pc == 0x8002
    assert ppu.ctrl == 0x00

    # Step 2: STA $2000. CpuBus routes this write to PPUCTRL.
    cycles = console.step()
    assert cycles == 4
    assert cpu.pc == 0x8005
    assert ppu.ctrl & CTRL_NMI_ENABLE

    # Step 3: NOP. PPU crosses into VBlank during this Console.step(), requests
    # NMI, and Console consumes it by calling CPU.interrupt_nmi().
    cycles = console.step()

    assert cycles == 2
    assert ppu.scanline == PPU_VBLANK_START_SCANLINE
    assert ppu.cycle == 0
    assert ppu.status & VBLANK_STARTED
    assert ppu.nmi_requested is False
    assert cpu.pc == 0x9000
    assert cpu.s == 0xFA
