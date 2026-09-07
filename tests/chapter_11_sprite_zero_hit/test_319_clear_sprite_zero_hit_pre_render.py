"""
Clear sprite 0 hit at the simplified pre-render boundary.

File to update:
    emulator/ppu/ppu.py

Why this step exists:
Sprite 0 hit is PPUSTATUS bit 6. Games can use it as a timing signal by waiting for
the flag to transition through this lifecycle:

    visible frame overlap -> sprite 0 hit becomes set
    pre-render boundary   -> sprite 0 hit becomes clear
    next visible frame    -> sprite 0 hit may become set again

Before implementing overlap detection or setting the flag, this step establishes
the clear/reset invariant. Without this reset, a future sprite 0 hit could remain
set forever and break games that wait for the flag to clear before waiting for the
next hit.

Current timing model:
The project currently advances timing at scanline transitions. Therefore this step
clears the flag when scanline 261 begins. Exact hardware dot timing is a future
accuracy refinement.

Example implementation fragment:

    if self.scanline == PPU_PRE_RENDER_SCANLINE:
        self.status &= ~VBLANK_STARTED

        # --- NEW BLOCK: CLEAR SPRITE 0 HIT FOR THE NEXT FRAME ---
        self.status &= ~SPRITE_ZERO_HIT
        # --- END NEW BLOCK ---

Important invariant:
Reading PPUSTATUS clears VBlank bit 7, but it must not clear sprite 0 hit bit 6.
Only the pre-render lifecycle event clears sprite 0 hit in the current model.

Current manual ROM policy:
Continue using MarioBros.nes for current manual checks. Super Mario Bros. validation
is deferred until overlap detection and timed hit-setting are implemented.

Out of scope:
    - detecting sprite 0/background overlap
    - setting sprite 0 hit
    - fixed/fake scanline hits
    - sprite overflow
    - Console changes
    - rendering changes
    - Super Mario Bros. validation
"""

from emulator.ppu.ppu import (
    PPU,
    PPU_CYCLES_PER_SCANLINE,
    PPU_PRE_RENDER_SCANLINE,
    SPRITE_ZERO_HIT,
    VBLANK_STARTED,
)


def advance_to_start_of_pre_render_scanline(ppu: PPU) -> None:
    """Place the PPU one cycle before scanline 261 and cross the boundary."""
    ppu.scanline = PPU_PRE_RENDER_SCANLINE - 1
    ppu.cycle = PPU_CYCLES_PER_SCANLINE - 1
    ppu.step(1)


def test_sprite_zero_hit_remains_set_before_pre_render_boundary():
    """
    Objective:
    Sprite 0 hit should not be cleared early during the previous scanline.
    """
    ppu = PPU()
    ppu.status |= SPRITE_ZERO_HIT
    ppu.scanline = PPU_PRE_RENDER_SCANLINE - 1
    ppu.cycle = PPU_CYCLES_PER_SCANLINE - 2

    ppu.step(1)

    assert ppu.scanline == PPU_PRE_RENDER_SCANLINE - 1
    assert (ppu.status & SPRITE_ZERO_HIT) != 0


def test_sprite_zero_hit_clears_when_pre_render_scanline_begins():
    """
    Objective:
    Crossing into the simplified pre-render boundary should clear PPUSTATUS bit 6.
    """
    ppu = PPU()
    ppu.status |= SPRITE_ZERO_HIT

    advance_to_start_of_pre_render_scanline(ppu)

    assert ppu.scanline == PPU_PRE_RENDER_SCANLINE
    assert ppu.cycle == 0
    assert (ppu.status & SPRITE_ZERO_HIT) == 0


def test_pre_render_boundary_clears_vblank_and_sprite_zero_hit_together():
    """
    Objective:
    Adding sprite 0 hit clearing should preserve the existing VBlank-clear behavior.
    """
    ppu = PPU()
    ppu.status |= VBLANK_STARTED | SPRITE_ZERO_HIT

    advance_to_start_of_pre_render_scanline(ppu)

    assert (ppu.status & VBLANK_STARTED) == 0
    assert (ppu.status & SPRITE_ZERO_HIT) == 0


def test_pre_render_clear_preserves_unrelated_status_bits():
    """
    Objective:
    Clear only the lifecycle flags owned by this boundary. Other status bits should
    not be erased by assigning status to zero.
    """
    unrelated_status_bit = 1 << 5
    ppu = PPU()
    ppu.status = VBLANK_STARTED | SPRITE_ZERO_HIT | unrelated_status_bit

    advance_to_start_of_pre_render_scanline(ppu)

    assert (ppu.status & VBLANK_STARTED) == 0
    assert (ppu.status & SPRITE_ZERO_HIT) == 0
    assert (ppu.status & unrelated_status_bit) != 0


def test_reading_ppustatus_does_not_clear_sprite_zero_hit():
    """
    Objective:
    PPUSTATUS reads clear VBlank, not sprite 0 hit. This distinction is required by
    games that poll bit 6 repeatedly.
    """
    ppu = PPU()
    ppu.status = VBLANK_STARTED | SPRITE_ZERO_HIT

    returned_status = ppu.read_register(0x2002)

    assert (returned_status & VBLANK_STARTED) != 0
    assert (returned_status & SPRITE_ZERO_HIT) != 0
    assert (ppu.status & VBLANK_STARTED) == 0
    assert (ppu.status & SPRITE_ZERO_HIT) != 0


def test_step_319_does_not_set_sprite_zero_hit():
    """
    Objective:
    This step only defines clearing behavior. Starting with a clear flag and crossing
    pre-render must not invent a hit.
    """
    ppu = PPU()
    assert (ppu.status & SPRITE_ZERO_HIT) == 0

    advance_to_start_of_pre_render_scanline(ppu)

    assert (ppu.status & SPRITE_ZERO_HIT) == 0
