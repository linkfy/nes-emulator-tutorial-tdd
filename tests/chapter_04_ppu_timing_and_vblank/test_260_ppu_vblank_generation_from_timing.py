"""
Implement VBlank generation from PPU timing.

Reference:
    https://www.nesdev.org/wiki/PPU_rendering#Line-by-line_timing
    https://www.nesdev.org/wiki/PPU_registers#PPUSTATUS

File to update:
    emulator/ppu/ppu.py

Constants to add:
    PPU_VBLANK_START_SCANLINE = 241
    PPU_PRE_RENDER_SCANLINE = 261

Why this step exists:
Many NES programs wait for VBlank before writing PPU memory. They commonly poll
PPUSTATUS ($2002) until bit 7 becomes set.

Conceptual behavior for this tutorial step:

    when the PPU enters scanline 241:
        set PPUSTATUS bit 7, VBLANK_STARTED

    when the PPU enters scanline 261, the pre-render scanline:
        clear PPUSTATUS bit 7

This gives ROMs a basic frame signal without implementing full rendering yet.

Suggested implementation example:

    PPU_VBLANK_START_SCANLINE = 241
    PPU_PRE_RENDER_SCANLINE = 261

    def step(self, cycles: int = 1) -> None:
        for _ in range(cycles):
            self.cycle += 1

            if self.cycle >= PPU_CYCLES_PER_SCANLINE:
                self.cycle = 0
                self.scanline += 1

                if self.scanline >= PPU_SCANLINES_PER_FRAME:
                    self.scanline = 0
                    self.frame += 1

                # Simplified scanline-level timing event.
                if self.scanline == PPU_VBLANK_START_SCANLINE:
                    self.status |= VBLANK_STARTED

                if self.scanline == PPU_PRE_RENDER_SCANLINE:
                    self.status &= ~VBLANK_STARTED

Important simplification:
This is not dot-accurate PPU timing. On real hardware, status changes happen at
specific PPU dots/cycles, commonly modeled around dot/cycle 1 of the relevant scanline.
For now, this tutorial uses scanline-entry behavior because the goal is to teach
the frame/VBlank concept before full cycle accuracy.

Out of tutorial objectives for now:
    - dot/cycle-accurate VBlank timing
    - odd-frame cycle skip
    - rendering pixels during visible scanlines
    - sprite 0 hit
    - sprite overflow
    - NMI generation/CPU interrupt handling
"""

from emulator.ppu.ppu import (
    PPU,
    PPU_CYCLES_PER_SCANLINE,
    PPU_PRE_RENDER_SCANLINE,
    PPU_SCANLINES_PER_FRAME,
    PPU_VBLANK_START_SCANLINE,
    VBLANK_STARTED,
)


def cycles_to_enter_scanline(scanline: int) -> int:
    """Return the number of PPU cycles needed to enter a scanline from reset."""
    return PPU_CYCLES_PER_SCANLINE * scanline


def test_ppu_declares_vblank_timing_scanline_constants():
    """
    Objective:
    Name the scanlines used by the simplified VBlank timing model.
    """
    assert PPU_VBLANK_START_SCANLINE == 241
    assert PPU_PRE_RENDER_SCANLINE == 261


def test_vblank_is_clear_before_vblank_start_scanline():
    """
    Objective:
    Before entering scanline 241, PPUSTATUS VBlank bit should still be clear.
    """
    ppu = PPU()

    ppu.step(cycles_to_enter_scanline(PPU_VBLANK_START_SCANLINE) - 1)

    assert ppu.scanline == PPU_VBLANK_START_SCANLINE - 1
    assert (ppu.status & VBLANK_STARTED) == 0


def test_vblank_starts_when_ppu_enters_scanline_241():
    """
    Objective:
    Entering the VBlank start scanline sets PPUSTATUS bit 7.

    Tutorial simplification:
    This checks scanline-level behavior, not exact dot/cycle-1 timing.
    """
    ppu = PPU()

    ppu.step(cycles_to_enter_scanline(PPU_VBLANK_START_SCANLINE))

    assert ppu.scanline == PPU_VBLANK_START_SCANLINE
    assert ppu.cycle == 0
    assert (ppu.status & VBLANK_STARTED) != 0


def test_vblank_remains_set_during_vblank_until_cleared():
    """
    Objective:
    After VBlank starts, the flag remains set while the PPU continues through
    later VBlank scanlines.
    """
    ppu = PPU()

    ppu.step(cycles_to_enter_scanline(PPU_VBLANK_START_SCANLINE))
    ppu.step(PPU_CYCLES_PER_SCANLINE * 3)

    assert ppu.scanline == PPU_VBLANK_START_SCANLINE + 3
    assert (ppu.status & VBLANK_STARTED) != 0


def test_ppustatus_read_clears_vblank_and_timing_does_not_reset_it_same_scanline():
    """
    Objective:
    Reading PPUSTATUS should clear VBlank. Because VBlank is generated only when
    entering scanline 241, stepping more cycles on that same scanline should not
    immediately set it again.

    This protects against treating VBlank as "always true during scanline 241".
    """
    ppu = PPU()

    ppu.step(cycles_to_enter_scanline(PPU_VBLANK_START_SCANLINE))
    assert (ppu.status & VBLANK_STARTED) != 0

    value = ppu.read_register(0x2002)
    assert (value & VBLANK_STARTED) != 0
    assert (ppu.status & VBLANK_STARTED) == 0

    ppu.step(10)

    assert ppu.scanline == PPU_VBLANK_START_SCANLINE
    assert (ppu.status & VBLANK_STARTED) == 0


def test_pre_render_scanline_clears_vblank():
    """
    Objective:
    Entering the pre-render scanline clears the VBlank flag.
    """
    ppu = PPU()

    ppu.step(cycles_to_enter_scanline(PPU_VBLANK_START_SCANLINE))
    assert (ppu.status & VBLANK_STARTED) != 0

    ppu.step(PPU_CYCLES_PER_SCANLINE * (PPU_PRE_RENDER_SCANLINE - PPU_VBLANK_START_SCANLINE))

    assert ppu.scanline == PPU_PRE_RENDER_SCANLINE
    assert (ppu.status & VBLANK_STARTED) == 0


def test_vblank_generation_still_allows_frame_wrap():
    """
    Objective:
    Adding VBlank side effects should not break the timing counter invariant that
    262 scanlines complete one frame.
    """
    ppu = PPU()

    ppu.step(PPU_CYCLES_PER_SCANLINE * PPU_SCANLINES_PER_FRAME)

    assert ppu.cycle == 0
    assert ppu.scanline == 0
    assert ppu.frame == 1
