"""
Apply horizontal v increments and the horizontal t-to-v copy at PPU timing dots.

File to update:
    emulator/ppu/ppu.py

References:
    https://www.nesdev.org/wiki/PPU_scrolling#During_rendering
    https://www.nesdev.org/wiki/PPU_rendering#Line-by-line_timing

Why this step exists:
Steps 338 and 339 implemented pure horizontal address mechanisms. This step connects
them to PPU time.

On visible and pre-render scanlines while rendering is enabled:

    dots 8, 16, 24, ... 256:
        increment horizontal v after each fetched tile

    dot 257:
        copy coarse X and horizontal nametable from t into v

    dots 328 and 336:
        increment horizontal v while prefetching the first tiles for the next scanline

Rendering is enabled when either PPUMASK background or sprite rendering is enabled.
The address timing is inactive during post-render and VBlank scanlines.

Simplified timeline:

    1---------256 257 --------320 321------336 ----340
    tile fetches  reload X          prefetch tiles
      ^ every 8                     ^ 328 and 336

Important ordering:
PPU.step() first advances self.cycle. The resulting value is treated as the current
dot, then horizontal address timing is applied. Therefore, a PPU starting at cycle
256 performs the horizontal reload after one step at dot 257.

Common misconception:
Horizontal increments are not limited to visible pixels. Dots 328 and 336 prepare
the first two background tiles for the next scanline and also increment v.

Out of scope:
    - vertical increment at dot 256
    - vertical t-to-v copy during pre-render
    - scanline viewport recording
    - framebuffer and opacity-mask changes

Complete example implementation:

    # emulator/ppu/ppu.py

    class PPU:
        ...

        # --- NEW BLOCK: APPLY HORIZONTAL ADDRESS TIMING ---
        def _step_horizontal_rendering_address(self) -> None:
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

            visible_fetch_increment = (
                1 <= self.cycle <= 256
                and self.cycle % 8 == 0
            )
            prefetch_increment = (
                321 <= self.cycle <= 336
                and self.cycle % 8 == 0
            )

            if visible_fetch_increment or prefetch_increment:
                self.vram_addr = increment_horizontal_vram_addr(
                    self.vram_addr
                )

            if self.cycle == 257:
                self.vram_addr = copy_horizontal_scroll_bits(
                    self.vram_addr,
                    self.temp_vram_addr,
                )

        def step(self, cycles: int = 1) -> None:
            ...

            for _ in range(cycles):
                self.cycle += 1

                # --- NEW LINE: APPLY TIMING AT THE CURRENT DOT ---
                self._step_horizontal_rendering_address()

                ...
"""

import pytest

from emulator.ppu.ppu import (
    HORIZONTAL_SCROLL_BITS,
    MASK_SHOW_BACKGROUND,
    MASK_SHOW_SPRITES,
    PPU,
    PPU_PRE_RENDER_SCANLINE,
)


@pytest.mark.parametrize("rendering_mask", [MASK_SHOW_BACKGROUND, MASK_SHOW_SPRITES])
def test_either_background_or_sprite_rendering_enables_horizontal_timing(
    rendering_mask,
):
    """
    Objective:
    Match hardware address timing when either rendering path is enabled.
    """
    ppu = PPU()
    ppu.mask = rendering_mask
    ppu.scanline = 0
    ppu.cycle = 7
    ppu.vram_addr = 10

    ppu.step()

    assert ppu.cycle == 8
    assert ppu.vram_addr & 0x001F == 11


def test_rendering_disabled_does_not_change_horizontal_v():
    """
    Objective:
    CPU-controlled rendering disablement also disables automatic address timing.
    """
    ppu = PPU()
    ppu.mask = 0
    ppu.scanline = 0
    ppu.cycle = 7
    ppu.vram_addr = 10

    ppu.step()

    assert ppu.vram_addr == 10


def test_visible_fetch_region_increments_once_every_eight_dots():
    """
    Objective:
    Increment after each tile fetch rather than on every PPU dot.
    """
    ppu = PPU()
    ppu.mask = MASK_SHOW_BACKGROUND
    ppu.scanline = 20
    ppu.cycle = 6
    ppu.vram_addr = 0

    ppu.step()  # dot 7
    assert ppu.vram_addr == 0

    ppu.step()  # dot 8
    assert ppu.vram_addr == 1

    ppu.step()  # dot 9
    assert ppu.vram_addr == 1

    ppu.step(7)  # dots 10-16
    assert ppu.vram_addr == 2


def test_dot_256_performs_the_final_visible_horizontal_increment():
    """
    Objective:
    Include dot 256 in the every-eight-dot horizontal fetch sequence.
    """
    ppu = PPU()
    ppu.mask = MASK_SHOW_BACKGROUND
    ppu.scanline = 100
    ppu.cycle = 255
    ppu.vram_addr = 30

    ppu.step()

    assert ppu.cycle == 256
    assert ppu.vram_addr & 0x001F == 31


def test_dot_257_copies_horizontal_fields_from_t_into_v():
    """
    Objective:
    Reload the next scanline's coarse X and horizontal nametable immediately after the
    visible fetch region.
    """
    ppu = PPU()
    ppu.mask = MASK_SHOW_BACKGROUND
    ppu.scanline = 40
    ppu.cycle = 256
    ppu.vram_addr = 0x7BE0 | 3
    ppu.temp_vram_addr = 0x0400 | 20
    preserved_vertical = ppu.vram_addr & ~HORIZONTAL_SCROLL_BITS

    ppu.step()

    assert ppu.cycle == 257
    assert ppu.vram_addr & HORIZONTAL_SCROLL_BITS == 0x0400 | 20
    assert ppu.vram_addr & ~HORIZONTAL_SCROLL_BITS == preserved_vertical


@pytest.mark.parametrize("starting_cycle", [327, 335])
def test_prefetch_dots_328_and_336_increment_horizontal_v(starting_cycle):
    """
    Objective:
    Account for the two background tiles fetched before the next scanline begins.
    """
    ppu = PPU()
    ppu.mask = MASK_SHOW_BACKGROUND
    ppu.scanline = 60
    ppu.cycle = starting_cycle
    ppu.vram_addr = 8

    ppu.step()

    assert ppu.vram_addr & 0x001F == 9


@pytest.mark.parametrize("scanline", [0, 239, PPU_PRE_RENDER_SCANLINE])
def test_visible_and_pre_render_scanlines_apply_horizontal_timing(scanline):
    """
    Objective:
    Apply fetch-address behavior to every rendering scanline, including pre-render.
    """
    ppu = PPU()
    ppu.mask = MASK_SHOW_BACKGROUND
    ppu.scanline = scanline
    ppu.cycle = 7
    ppu.vram_addr = 4

    ppu.step()

    assert ppu.vram_addr & 0x001F == 5


@pytest.mark.parametrize("scanline", [240, 241, 250, 260])
def test_post_render_and_vblank_do_not_apply_horizontal_timing(scanline):
    """
    Objective:
    Keep automatic rendering-address updates out of non-rendering scanlines.
    """
    ppu = PPU()
    ppu.mask = MASK_SHOW_BACKGROUND
    ppu.scanline = scanline
    ppu.cycle = 7
    ppu.vram_addr = 4

    ppu.step()

    assert ppu.vram_addr == 4


def test_dot_257_copy_is_disabled_when_rendering_is_disabled():
    """
    Objective:
    Prevent automatic t-to-v transfers while PPUMASK disables rendering.
    """
    ppu = PPU()
    ppu.mask = 0
    ppu.scanline = 0
    ppu.cycle = 256
    ppu.vram_addr = 3
    ppu.temp_vram_addr = 0x0400 | 20

    ppu.step()

    assert ppu.vram_addr == 3
