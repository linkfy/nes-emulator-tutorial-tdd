"""
Implement basic PPU timing counters.

Reference:
    https://www.nesdev.org/wiki/PPU_rendering#Line-by-line_timing

File to update:
    emulator/ppu/ppu.py

Constants to add:
    PPU_CYCLES_PER_SCANLINE = 341
    PPU_SCANLINES_PER_FRAME = 262

State to add:
    cycle: int = 0
    scanline: int = 0
    frame: int = 0

Method to add:
    PPU.step(cycles: int = 1) -> None

Why this step exists:
The PPU is a time-based device. Later, VBlank, NMI, rendering, and frame pacing
will depend on knowing where the PPU is inside the current frame.

For this step, only add counters:

    cycle    -> position inside the current scanline
    scanline -> current scanline inside the frame
    frame    -> completed frame count

Initial timing model:

    341 PPU cycles per scanline
    262 scanlines per frame

Suggested implementation example:

    def step(self, cycles: int = 1) -> None:
        for _ in range(cycles):
            self.cycle += 1

            if self.cycle >= PPU_CYCLES_PER_SCANLINE:
                self.cycle = 0
                self.scanline += 1

                if self.scanline >= PPU_SCANLINES_PER_FRAME:
                    self.scanline = 0
                    self.frame += 1

Future compatibility:
These tests intentionally check only counter behavior. They do not require exact
VBlank/NMI side effects yet. Later steps may add side effects inside PPU.step(),
but these counter invariants should remain true.

Out of scope:
    - VBlank generation
    - NMI request
    - rendering
    - sprite 0 hit
    - sprite overflow
    - odd-frame cycle skip
"""

from emulator.ppu.ppu import PPU, PPU_CYCLES_PER_SCANLINE, PPU_SCANLINES_PER_FRAME, VBLANK_STARTED


def test_ppu_declares_basic_timing_constants():
    """
    Objective:
    Name the initial timing constants used by the PPU counters.
    """
    assert PPU_CYCLES_PER_SCANLINE == 341
    assert PPU_SCANLINES_PER_FRAME == 262


def test_ppu_timing_counters_start_at_zero():
    """
    Objective:
    A new PPU starts at the beginning of frame 0, scanline 0, cycle 0.
    """
    ppu = PPU()

    assert ppu.cycle == 0
    assert ppu.scanline == 0
    assert ppu.frame == 0


def test_ppu_step_advances_one_cycle_by_default():
    """
    Objective:
    Calling step() with no argument advances one PPU cycle.
    """
    ppu = PPU()

    ppu.step()

    assert ppu.cycle == 1
    assert ppu.scanline == 0
    assert ppu.frame == 0


def test_ppu_step_can_advance_multiple_cycles():
    """
    Objective:
    PPU.step(cycles) can advance more than one PPU cycle.

    This makes later CPU integration easier, because one CPU cycle corresponds to
    three PPU cycles.
    """
    ppu = PPU()

    ppu.step(12)

    assert ppu.cycle == 12
    assert ppu.scanline == 0
    assert ppu.frame == 0


def test_ppu_step_wraps_cycle_and_advances_scanline_after_341_cycles():
    """
    Objective:
    After 341 PPU cycles, the PPU moves to the next scanline and cycle resets.
    """
    ppu = PPU()

    ppu.step(PPU_CYCLES_PER_SCANLINE)

    assert ppu.cycle == 0
    assert ppu.scanline == 1
    assert ppu.frame == 0


def test_ppu_step_preserves_remaining_cycle_after_scanline_wrap():
    """
    Objective:
    Extra cycles after a scanline wrap should remain in the next scanline.

    Example:
        342 cycles = 1 full scanline + 1 cycle
    """
    ppu = PPU()

    ppu.step(PPU_CYCLES_PER_SCANLINE + 1)

    assert ppu.cycle == 1
    assert ppu.scanline == 1
    assert ppu.frame == 0


def test_ppu_step_wraps_scanline_and_advances_frame_after_262_scanlines():
    """
    Objective:
    After 262 scanlines, the PPU starts the next frame.
    """
    ppu = PPU()

    ppu.step(PPU_CYCLES_PER_SCANLINE * PPU_SCANLINES_PER_FRAME)

    assert ppu.cycle == 0
    assert ppu.scanline == 0
    assert ppu.frame == 1


def test_ppu_timing_step_does_not_require_vblank_behavior_yet():
    """
    Objective:
    Step 259 only introduces counters. VBlank side effects are added in the next
    step, so this test keeps current scope narrow.

    Future compatibility:
    This test does not step far enough to reach VBlank timing. Later VBlank logic
    can be added without breaking this assertion.
    """
    ppu = PPU()

    ppu.step(10)

    assert (ppu.status & VBLANK_STARTED) == 0
