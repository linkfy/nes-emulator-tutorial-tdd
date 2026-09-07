"""
Apply vertical v increment and vertical t-to-v copying at PPU timing dots.

File to update:
    emulator/ppu/ppu.py

References:
    https://www.nesdev.org/wiki/PPU_scrolling#At_dot_256_of_each_scanline

Why this step exists:
Steps 341 and 342 implemented pure vertical address mechanisms. This step connects
them to PPU time.

While rendering is enabled:

    visible and pre-render scanlines, dot 256:
        increment fine/coarse Y in v

    pre-render scanline, every dot 280-304:
        copy fine Y, vertical nametable, and coarse Y from t into v

Simplified timing:

    visible scanline:
        ... 255 256 257 ...
                |   |
                |   +-- horizontal reload
                +------ vertical increment

    pre-render scanline 261:
        ... 256 257 ... 280----------------304 ...
            |   |       |
            |   |       +-- vertical reload active at every dot
            |   +---------- horizontal reload
            +-------------- vertical increment

Why repeat the vertical reload at every dot 280-304?
If CPU writes change t during that interval, a later dot can copy the newer vertical
state. Treating the interval as one operation at dot 280 would lose that behavior.

Rendering is enabled when either the PPUMASK background bit or sprite bit is set.
Post-render and VBlank scanlines do not perform these automatic updates.

Important ordering at dot 256:
The horizontal fetch increment runs first and the vertical increment runs second.
They own different fields, so both changes must be visible in the resulting v.

Out of scope:
    - effective viewport recording per scanline
    - two-tile prefetch compensation
    - framebuffer row composition
    - opacity-mask row composition

Complete example implementation:

    # emulator/ppu/ppu.py

    class PPU:
        ...

        # --- NEW BLOCK: APPLY VERTICAL ADDRESS TIMING ---
        def _step_vertical_rendering_address(self) -> None:
            rendering_enabled = self.mask & (
                MASK_SHOW_BACKGROUND | MASK_SHOW_SPRITES
            )
            if not rendering_enabled:
                return

            rendering_scanline = (
                0 <= self.scanline < 240
                or self.scanline == PPU_PRE_RENDER_SCANLINE
            )
            if not rendering_scanline:
                return

            if self.cycle == 256:
                self.vram_addr = increment_vertical_vram_addr(
                    self.vram_addr
                )

            vertical_reload = (
                self.scanline == PPU_PRE_RENDER_SCANLINE
                and 280 <= self.cycle <= 304
            )
            if vertical_reload:
                self.vram_addr = copy_vertical_scroll_bits(
                    self.vram_addr,
                    self.temp_vram_addr,
                )

        def step(self, cycles: int = 1) -> None:
            ...

            for _ in range(cycles):
                self.cycle += 1
                self._step_horizontal_rendering_address()

                # --- NEW LINE: APPLY VERTICAL TIMING AT THE CURRENT DOT ---
                self._step_vertical_rendering_address()

                ...
"""

import pytest

from emulator.ppu.ppu import (
    HORIZONTAL_SCROLL_BITS,
    MASK_SHOW_BACKGROUND,
    MASK_SHOW_SPRITES,
    PPU,
    PPU_PRE_RENDER_SCANLINE,
    VERTICAL_SCROLL_BITS,
)


@pytest.mark.parametrize("rendering_mask", [MASK_SHOW_BACKGROUND, MASK_SHOW_SPRITES])
def test_either_background_or_sprite_rendering_enables_dot_256_increment(
    rendering_mask,
):
    """
    Objective:
    Match PPU address timing when either rendering path is active.
    """
    ppu = PPU()
    ppu.mask = rendering_mask
    ppu.scanline = 10
    ppu.cycle = 255
    ppu.vram_addr = 2 << 12

    ppu.step()

    assert ppu.cycle == 256
    assert (ppu.vram_addr & 0x7000) >> 12 == 3


def test_dot_256_vertical_increment_is_disabled_when_rendering_is_disabled():
    """
    Objective:
    Keep automatic vertical updates disabled with PPUMASK rendering bits clear.
    """
    ppu = PPU()
    ppu.mask = 0
    ppu.scanline = 10
    ppu.cycle = 255
    ppu.vram_addr = 2 << 12

    ppu.step()

    assert ppu.vram_addr == 2 << 12


@pytest.mark.parametrize("scanline", [0, 239, PPU_PRE_RENDER_SCANLINE])
def test_dot_256_increment_runs_on_visible_and_pre_render_scanlines(scanline):
    """
    Objective:
    Apply vertical advancement on every scanline that performs rendering fetches.
    """
    ppu = PPU()
    ppu.mask = MASK_SHOW_BACKGROUND
    ppu.scanline = scanline
    ppu.cycle = 255
    ppu.vram_addr = 4 << 12

    ppu.step()

    assert (ppu.vram_addr & 0x7000) >> 12 == 5


@pytest.mark.parametrize("scanline", [240, 241, 250, 260])
def test_dot_256_increment_does_not_run_during_post_render_or_vblank(scanline):
    """
    Objective:
    Exclude non-rendering scanlines even when PPUMASK rendering remains enabled.
    """
    ppu = PPU()
    ppu.mask = MASK_SHOW_BACKGROUND
    ppu.scanline = scanline
    ppu.cycle = 255
    ppu.vram_addr = 4 << 12

    ppu.step()

    assert ppu.vram_addr == 4 << 12


@pytest.mark.parametrize("target_dot", [280, 281, 300, 304])
def test_pre_render_dots_280_through_304_copy_vertical_t_into_v(target_dot):
    """
    Objective:
    Treat the full pre-render vertical reload interval as active, inclusive of both
    endpoints.
    """
    ppu = PPU()
    ppu.mask = MASK_SHOW_BACKGROUND
    ppu.scanline = PPU_PRE_RENDER_SCANLINE
    ppu.cycle = target_dot - 1
    ppu.vram_addr = HORIZONTAL_SCROLL_BITS
    ppu.temp_vram_addr = VERTICAL_SCROLL_BITS

    ppu.step()

    assert ppu.cycle == target_dot
    assert ppu.vram_addr & VERTICAL_SCROLL_BITS == VERTICAL_SCROLL_BITS
    assert ppu.vram_addr & HORIZONTAL_SCROLL_BITS == HORIZONTAL_SCROLL_BITS


def test_vertical_reload_repeats_when_t_changes_inside_interval():
    """
    Objective:
    A later pre-render dot must observe vertical state written after an earlier copy.
    """
    ppu = PPU()
    ppu.mask = MASK_SHOW_BACKGROUND
    ppu.scanline = PPU_PRE_RENDER_SCANLINE
    ppu.cycle = 279
    ppu.temp_vram_addr = 0x0020

    ppu.step()  # dot 280 copies coarse Y 1
    assert ppu.vram_addr & VERTICAL_SCROLL_BITS == 0x0020

    ppu.temp_vram_addr = 0x0040
    ppu.step()  # dot 281 copies coarse Y 2

    assert ppu.vram_addr & VERTICAL_SCROLL_BITS == 0x0040


@pytest.mark.parametrize("target_dot", [279, 305])
def test_vertical_reload_does_not_run_outside_pre_render_interval(target_dot):
    """
    Objective:
    Prevent off-by-one copies immediately before or after dots 280-304.
    """
    ppu = PPU()
    ppu.mask = MASK_SHOW_BACKGROUND
    ppu.scanline = PPU_PRE_RENDER_SCANLINE
    ppu.cycle = target_dot - 1
    ppu.vram_addr = HORIZONTAL_SCROLL_BITS
    ppu.temp_vram_addr = VERTICAL_SCROLL_BITS

    ppu.step()

    assert ppu.vram_addr & VERTICAL_SCROLL_BITS == 0


def test_vertical_reload_does_not_run_on_visible_scanline_at_dot_280():
    """
    Objective:
    Restrict the reload interval to pre-render rather than every rendering scanline.
    """
    ppu = PPU()
    ppu.mask = MASK_SHOW_BACKGROUND
    ppu.scanline = 100
    ppu.cycle = 279
    ppu.vram_addr = HORIZONTAL_SCROLL_BITS
    ppu.temp_vram_addr = VERTICAL_SCROLL_BITS

    ppu.step()

    assert ppu.vram_addr & VERTICAL_SCROLL_BITS == 0


def test_dot_256_applies_both_horizontal_and_vertical_increments():
    """
    Objective:
    Preserve the call ordering and independent field ownership of both timing paths.
    """
    ppu = PPU()
    ppu.mask = MASK_SHOW_BACKGROUND
    ppu.scanline = 50
    ppu.cycle = 255
    ppu.vram_addr = 0

    ppu.step()

    assert ppu.vram_addr & 0x001F == 1
    assert (ppu.vram_addr & 0x7000) >> 12 == 1


def test_pre_render_vertical_reload_is_disabled_when_rendering_is_disabled():
    """
    Objective:
    PPUMASK rendering disablement prevents automatic vertical t-to-v transfers.
    """
    ppu = PPU()
    ppu.mask = 0
    ppu.scanline = PPU_PRE_RENDER_SCANLINE
    ppu.cycle = 279
    ppu.vram_addr = HORIZONTAL_SCROLL_BITS
    ppu.temp_vram_addr = VERTICAL_SCROLL_BITS

    ppu.step()

    assert ppu.vram_addr & VERTICAL_SCROLL_BITS == 0
