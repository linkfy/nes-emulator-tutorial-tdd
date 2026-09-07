"""
Implement PPU-side NMI request on VBlank.

Reference:
    https://www.nesdev.org/wiki/PPU_registers#PPUCTRL
    https://www.nesdev.org/wiki/PPU_registers#Vblank_NMI

File to update:
    emulator/ppu/ppu.py

State to add:
    nmi_requested: bool = False

Why this step exists:
Many NES games do not poll PPUSTATUS in their main loop. Instead, they enable NMI
in PPUCTRL bit 7 and expect the PPU to request an interrupt when VBlank starts.

For this step, only implement the PPU-side signal:

    if VBlank starts and PPUCTRL bit 7 is set:
        ppu.nmi_requested = True

The CPU does not consume the NMI yet. That is a later integration step.

Suggested implementation example:

    nmi_requested: bool = False
    ...
    ...

    if self.scanline == PPU_VBLANK_START_SCANLINE:
        self.status |= VBLANK_STARTED

        if self.ctrl & CTRL_NMI_ENABLE:
            self.nmi_requested = True

Important concept:
NMI request is an event produced when VBlank starts. It should not be produced
continuously on every cycle of VBlank.

Out of scope:
    - CPU interrupt handling
    - reading the NMI vector
    - pushing PC/status to the CPU stack
    - clearing nmi_requested by CPU/system integration
    - enabling NMI during an already-active VBlank
    - dot/cycle-accurate NMI timing
"""

from emulator.ppu.ppu import (
    CTRL_NMI_ENABLE,
    PPU,
    PPU_CYCLES_PER_SCANLINE,
    PPU_PRE_RENDER_SCANLINE,
    PPU_VBLANK_START_SCANLINE,
    VBLANK_STARTED,
)


def cycles_to_enter_scanline(scanline: int) -> int:
    """Return the number of PPU cycles needed to enter a scanline from reset."""
    return PPU_CYCLES_PER_SCANLINE * scanline


def test_ppu_nmi_requested_starts_false():
    """
    Objective:
    A new PPU should not start with a pending NMI request.
    """
    ppu = PPU()

    assert ppu.nmi_requested is False


def test_vblank_start_does_not_request_nmi_when_ppuctrl_nmi_bit_is_clear():
    """
    Objective:
    VBlank alone is not enough to request NMI. PPUCTRL bit 7 must be enabled.
    """
    ppu = PPU()
    assert (ppu.ctrl & CTRL_NMI_ENABLE) == 0

    ppu.step(cycles_to_enter_scanline(PPU_VBLANK_START_SCANLINE))

    assert (ppu.status & VBLANK_STARTED) != 0
    assert ppu.nmi_requested is False


def test_vblank_start_requests_nmi_when_ppuctrl_nmi_bit_is_set():
    """
    Objective:
    If PPUCTRL bit 7 is set, entering VBlank should request NMI.
    """
    ppu = PPU()
    ppu.write_register(0x2000, CTRL_NMI_ENABLE)

    ppu.step(cycles_to_enter_scanline(PPU_VBLANK_START_SCANLINE))

    assert (ppu.status & VBLANK_STARTED) != 0
    assert ppu.nmi_requested is True


def test_nmi_request_is_not_recreated_after_ppustatus_read_on_same_vblank_scanline():
    """
    Objective:
    NMI request is tied to the VBlank-start event. It should not be recreated just
    because the PPU remains on the VBlank start scanline.

    This test manually clears nmi_requested to simulate future CPU/system
    consumption, then steps a few cycles on the same scanline.
    """
    ppu = PPU()
    ppu.write_register(0x2000, CTRL_NMI_ENABLE)

    ppu.step(cycles_to_enter_scanline(PPU_VBLANK_START_SCANLINE))
    assert ppu.nmi_requested is True

    ppu.nmi_requested = False
    ppu.read_register(0x2002)
    ppu.step(10)

    assert ppu.scanline == PPU_VBLANK_START_SCANLINE
    assert ppu.nmi_requested is False


def test_pre_render_vblank_clear_does_not_implicitly_clear_pending_nmi_request():
    """
    Objective:
    For now, nmi_requested is a pending signal for CPU/system integration to
    consume. The PPU should not silently discard it when pre-render clears VBlank.

    A later CPU/system step can define how the request is consumed and cleared.
    """
    ppu = PPU()
    ppu.write_register(0x2000, CTRL_NMI_ENABLE)

    ppu.step(cycles_to_enter_scanline(PPU_VBLANK_START_SCANLINE))
    assert ppu.nmi_requested is True

    ppu.step(PPU_CYCLES_PER_SCANLINE * (PPU_PRE_RENDER_SCANLINE - PPU_VBLANK_START_SCANLINE))

    assert ppu.scanline == PPU_PRE_RENDER_SCANLINE
    assert (ppu.status & VBLANK_STARTED) == 0
    assert ppu.nmi_requested is True
