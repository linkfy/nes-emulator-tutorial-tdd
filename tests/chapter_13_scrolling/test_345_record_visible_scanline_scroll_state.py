"""
Record the effective viewport state at dot 1 of each visible scanline.

File to update:
    emulator/ppu/ppu.py

References:
    https://www.nesdev.org/wiki/PPU_rendering#Cycles_1-256
    https://www.nesdev.org/wiki/PPU_scrolling#Details


Why this step exists:
The PPU now updates v with horizontal and vertical rendering timing, but the existing
high-level renderer runs after the frame. It needs a small record of the effective
address that represented each visible screen row.

One immutable state stores:

    vram_addr:
        the copied address represented by the prefetched pixels

    fine_x:
        the separate 0-7 pixel offset inside the first tile

At dot 1, real v is two tile columns ahead because dots 321-336 prefetched the first
two tiles for the current scanline. Recording therefore performs:

    copied visible v = real v rewound once, then rewound again

Example:

    current scanline = 20
    real v coarse X  = 7

    copied visible coarse X:
        7 -> 6 -> 5

    stored destination:
        current_scanline_scroll_states[20]

The rewinds change horizontal tile position, not the scanline index. The state belongs
to current scanline 20, not scanline 18.

Recording conditions:
    - background or sprite rendering is enabled
    - scanline is visible: 0-239
    - current dot is 1

Important invariants:
    - the buffer always has exactly 240 entries
    - each PPU owns a separate buffer
    - the real PPU.vram_addr is not modified by recording
    - fine X is stored separately
    - post-render, VBlank, and pre-render are not recorded

Out of scope:
    - archiving the completed frame
    - replacing missing entries
    - resetting the current-frame buffer
    - framebuffer or opacity-mask composition

Complete example implementation:

    # emulator/ppu/ppu.py

    # --- NEW BLOCK: EFFECTIVE STATE FOR ONE VISIBLE SCANLINE ---
    @dataclass(frozen=True)
    class BackgroundScanlineState:
        vram_addr: int
        fine_x: int


    @dataclass
    class PPU:
        ...

        # --- NEW LINE: CURRENT FRAME'S VISIBLE SCANLINE STATES ---
        current_scanline_scroll_states: list[
            BackgroundScanlineState | None
        ] = field(default_factory=lambda: [None] * 240)

        ...

        # --- NEW BLOCK: RECORD THE CURRENT VISIBLE SCANLINE ---
        def _record_visible_scanline_scroll_state(self) -> None:
            rendering_enabled = self.mask & (
                MASK_SHOW_BACKGROUND | MASK_SHOW_SPRITES
            )
            if not rendering_enabled:
                return

            if not 0 <= self.scanline < 240:
                return

            if self.cycle != 1:
                return

            visible_vram_addr = decrement_horizontal_vram_addr(
                decrement_horizontal_vram_addr(self.vram_addr)
            )

            self.current_scanline_scroll_states[self.scanline] = (
                BackgroundScanlineState(
                    vram_addr=visible_vram_addr,
                    fine_x=self.fine_x,
                )
            )

        def step(self, cycles: int = 1) -> None:
            ...

            for _ in range(cycles):
                self.cycle += 1
                self._step_horizontal_rendering_address()
                self._step_vertical_rendering_address()

                # --- NEW LINE: RECORD THE CURRENT SCANLINE AT DOT 1 ---
                self._record_visible_scanline_scroll_state()

                ...
"""

from dataclasses import FrozenInstanceError

import pytest

from emulator.ppu.ppu import (
    BackgroundScanlineState,
    MASK_SHOW_BACKGROUND,
    MASK_SHOW_SPRITES,
    PPU,
)


def test_scanline_state_is_immutable_value_data():
    """
    Objective:
    Prevent a recorded scanline from changing when later PPU state changes.
    """
    state = BackgroundScanlineState(vram_addr=5, fine_x=3)

    with pytest.raises(FrozenInstanceError):
        state.fine_x = 4


def test_new_ppu_has_240_unrecorded_scanline_entries():
    """
    Objective:
    Provide one bounded slot for every visible screen row.
    """
    ppu = PPU()

    assert len(ppu.current_scanline_scroll_states) == 240
    assert ppu.current_scanline_scroll_states == [None] * 240


def test_each_ppu_owns_an_independent_scanline_buffer():
    """
    Objective:
    Avoid shared mutable default state between emulator instances and tests.
    """
    first = PPU()
    second = PPU()

    first.current_scanline_scroll_states[0] = BackgroundScanlineState(0, 0)

    assert second.current_scanline_scroll_states[0] is None


@pytest.mark.parametrize("rendering_mask", [MASK_SHOW_BACKGROUND, MASK_SHOW_SPRITES])
def test_dot_one_records_when_either_rendering_path_is_enabled(rendering_mask):
    """
    Objective:
    Match the same PPUMASK rendering condition used by automatic v timing.
    """
    ppu = PPU()
    ppu.mask = rendering_mask
    ppu.scanline = 20
    ppu.cycle = 0
    ppu.vram_addr = 7
    ppu.fine_x = 3

    ppu.step()

    assert ppu.cycle == 1
    assert ppu.current_scanline_scroll_states[20] == BackgroundScanlineState(
        vram_addr=5,
        fine_x=3,
    )


def test_recording_uses_current_scanline_index_not_horizontal_rewind_count():
    """
    Objective:
    Keep vertical row selection independent from the two horizontal tile rewinds.
    """
    ppu = PPU()
    ppu.mask = MASK_SHOW_BACKGROUND
    ppu.scanline = 20
    ppu.cycle = 0
    ppu.vram_addr = 7

    ppu.step()

    assert ppu.current_scanline_scroll_states[18] is None
    assert ppu.current_scanline_scroll_states[19] is None
    assert ppu.current_scanline_scroll_states[20] is not None


def test_recording_rewinds_across_horizontal_nametable_boundary():
    """
    Objective:
    Interpret two prefetched tiles correctly when the rewind crosses from logical
    nametable X=1 back into logical nametable X=0.
    """
    ppu = PPU()
    ppu.mask = MASK_SHOW_BACKGROUND
    ppu.scanline = 50
    ppu.cycle = 0
    ppu.vram_addr = 0x0400 | 1

    ppu.step()

    state = ppu.current_scanline_scroll_states[50]
    assert state is not None
    assert state.vram_addr & 0x001F == 31
    assert (state.vram_addr & 0x0400) == 0


def test_recording_does_not_modify_real_ppu_vram_addr():
    """
    Objective:
    Keep the active rendering address ahead while recording a derived visible address.
    """
    ppu = PPU()
    ppu.mask = MASK_SHOW_BACKGROUND
    ppu.scanline = 80
    ppu.cycle = 0
    ppu.vram_addr = 12

    ppu.step()

    assert ppu.vram_addr == 12
    assert ppu.current_scanline_scroll_states[80] == BackgroundScanlineState(
        vram_addr=10,
        fine_x=0,
    )


def test_recording_is_disabled_when_rendering_is_disabled():
    """
    Objective:
    Do not manufacture viewport history while PPUMASK disables rendering.
    """
    ppu = PPU()
    ppu.mask = 0
    ppu.scanline = 30
    ppu.cycle = 0
    ppu.vram_addr = 7

    ppu.step()

    assert ppu.current_scanline_scroll_states[30] is None


@pytest.mark.parametrize("scanline", [240, 241, 260, 261])
def test_non_visible_scanlines_are_not_recorded(scanline):
    """
    Objective:
    Restrict the 240-entry state list to visible output rows only.
    """
    ppu = PPU()
    ppu.mask = MASK_SHOW_BACKGROUND
    ppu.scanline = scanline
    ppu.cycle = 0
    ppu.vram_addr = 7

    ppu.step()

    assert ppu.current_scanline_scroll_states == [None] * 240


def test_only_dot_one_records_the_scanline_state():
    """
    Objective:
    Prevent later fetch-address changes from replacing the visible start position.
    """
    ppu = PPU()
    ppu.mask = MASK_SHOW_BACKGROUND
    ppu.scanline = 100
    ppu.cycle = 0
    ppu.vram_addr = 7

    ppu.step()  # dot 1 records visible coarse X 5
    recorded = ppu.current_scanline_scroll_states[100]

    ppu.vram_addr = 20
    ppu.step()  # dot 2 must not overwrite the state

    assert ppu.current_scanline_scroll_states[100] == recorded
