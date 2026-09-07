"""
Publish a complete timed scanline frame and reset the current recording buffer.

File to update:
    emulator/ppu/ppu.py

Reference:
    https://www.nesdev.org/wiki/PPU_rendering

Why this step exists:
PPU timing records visible scanline states into a mutable current-frame list. The
high-level renderer must consume stable data from a frame that has already finished,
not a list the PPU is still changing.

The PPU therefore owns two different values:

    current_scanline_scroll_states:
        mutable list used while the active frame is being stepped

    completed_scanline_scroll_states:
        immutable tuple published after the frame finishes

At the frame boundary:

    all 240 entries exist:
        publish a 240-state tuple

    any entry is missing or the list length is not 240:
        publish an empty tuple

    after either result:
        replace current state with a fresh [None] * 240 list

Why publish an empty tuple for incomplete data?
An unknown row must not inherit a guessed address. The empty tuple becomes a clear
signal that later rendering should keep using the existing frame-level compatibility
path for this frame.

Intuitive model:

    current list     = notebook still being written
    completed tuple  = sealed notebook safe for the renderer

Important invariants:
    - completed data contains exactly 240 states or zero states
    - completed data is immutable
    - current and completed containers are not the same object
    - recording the next frame cannot alter the completed frame
    - publication occurs after pre-render completes and before counters enter frame 0

Common misconception:
Frame completion does not happen when VBlank starts at scanline 241. Pre-render
scanline 261 still belongs to the timing sequence before the emulator rolls over to
the next frame.

Out of scope:
    - consuming completed states in framebuffer rendering
    - opacity-mask composition
    - sprite-zero-hit changes

Complete example implementation:

    # emulator/ppu/ppu.py

    @dataclass
    class PPU:
        ...
        current_scanline_scroll_states: list[BackgroundScanlineState | None] = field(
                default_factory= lambda: [None] * 240
        )

        # --- NEW LINE: LAST COMPLETE TIMED SCANLINE FRAME ---
        completed_scanline_scroll_states: tuple[
            BackgroundScanlineState, ...
        ] = ()

        ...

        # --- NEW BLOCK: PUBLISH AND RESET SCANLINE STATES ---
        def _complete_scanline_scroll_frame(self) -> None:
            current = self.current_scanline_scroll_states

            if (
                len(current) == 240
                and all(state is not None for state in current)
            ):
                self.completed_scanline_scroll_states = tuple(
                    state
                    for state in current
                    if state is not None
                )
            else:
                self.completed_scanline_scroll_states = ()

            self.current_scanline_scroll_states = [None] * 240

        def step(self, cycles: int = 1) -> None:
            ...

            if self.cycle >= PPU_CYCLES_PER_SCANLINE:
                self.cycle = 0
                self.scanline += 1

                if self.scanline >= PPU_SCANLINES_PER_FRAME:
                    # --- NEW LINE: PUBLISH BEFORE ENTERING THE NEXT FRAME ---
                    self._complete_scanline_scroll_frame()
                    self.scanline = 0
                    self.frame += 1

            ...
"""

import pytest

from emulator.ppu.ppu import BackgroundScanlineState, PPU


def make_complete_states() -> list[BackgroundScanlineState]:
    """Create one distinct immutable state for every visible scanline."""
    return [
        BackgroundScanlineState(
            vram_addr=scanline,
            fine_x=scanline % 8,
        )
        for scanline in range(240)
    ]


def test_new_ppu_has_no_completed_timed_frame():
    """
    Objective:
    Keep the old viewport path available until a complete timed frame is published.
    """
    ppu = PPU()

    assert ppu.completed_scanline_scroll_states == ()


def test_complete_240_entry_list_publishes_ordered_immutable_tuple():
    """
    Objective:
    Preserve each scanline's position and ordering in stable renderer input.
    """
    ppu = PPU()
    states = make_complete_states()
    ppu.current_scanline_scroll_states = list(states)

    ppu._complete_scanline_scroll_frame()

    assert isinstance(ppu.completed_scanline_scroll_states, tuple)
    assert len(ppu.completed_scanline_scroll_states) == 240
    assert ppu.completed_scanline_scroll_states == tuple(states)
    assert ppu.completed_scanline_scroll_states[0] is states[0]
    assert ppu.completed_scanline_scroll_states[239] is states[239]


def test_missing_scanline_publishes_empty_tuple_instead_of_guessing():
    """
    Objective:
    Reject incomplete timing evidence rather than filling an unknown row from a
    neighboring state.
    """
    ppu = PPU()
    current: list[BackgroundScanlineState | None] = list(make_complete_states())
    current[100] = None
    ppu.current_scanline_scroll_states = current

    ppu._complete_scanline_scroll_frame()

    assert ppu.completed_scanline_scroll_states == ()


@pytest.mark.parametrize("wrong_length", [0, 1, 239, 241])
def test_wrong_length_publishes_empty_tuple(wrong_length):
    """
    Objective:
    Enforce the structural invariant even if external code replaces the mutable list.
    """
    ppu = PPU()
    ppu.current_scanline_scroll_states = make_complete_states()[:wrong_length]

    if wrong_length == 241:
        ppu.current_scanline_scroll_states.append(
            BackgroundScanlineState(vram_addr=240, fine_x=0)
        )

    ppu._complete_scanline_scroll_frame()

    assert ppu.completed_scanline_scroll_states == ()


def test_completion_always_replaces_current_list_with_fresh_240_none_entries():
    """
    Objective:
    Prepare isolated storage for the next frame after successful publication.
    """
    ppu = PPU()
    old_current = list(make_complete_states())
    ppu.current_scanline_scroll_states = old_current

    ppu._complete_scanline_scroll_frame()

    assert ppu.current_scanline_scroll_states == [None] * 240
    assert ppu.current_scanline_scroll_states is not old_current


def test_incomplete_completion_also_resets_current_list():
    """
    Objective:
    Prevent stale partial state from leaking into the next frame.
    """
    ppu = PPU()
    old_current: list[BackgroundScanlineState | None] = [None] * 240
    ppu.current_scanline_scroll_states = old_current

    ppu._complete_scanline_scroll_frame()

    assert ppu.completed_scanline_scroll_states == ()
    assert ppu.current_scanline_scroll_states == [None] * 240
    assert ppu.current_scanline_scroll_states is not old_current


def test_recording_next_frame_does_not_modify_completed_tuple():
    """
    Objective:
    Keep renderer input stable while the PPU begins recording another frame.
    """
    ppu = PPU()
    states = make_complete_states()
    ppu.current_scanline_scroll_states = list(states)
    ppu._complete_scanline_scroll_frame()
    completed = ppu.completed_scanline_scroll_states

    ppu.current_scanline_scroll_states[0] = BackgroundScanlineState(
        vram_addr=999,
        fine_x=7,
    )

    assert ppu.completed_scanline_scroll_states is completed
    assert ppu.completed_scanline_scroll_states[0] == states[0]


def test_publication_occurs_only_when_frame_rolls_over():
    """
    Objective:
    Do not publish early while pre-render scanline 261 is still in progress.
    """
    ppu = PPU()
    states = make_complete_states()
    ppu.current_scanline_scroll_states = list(states)
    ppu.scanline = 261
    ppu.cycle = 339

    ppu.step()  # pre-render dot 340, not frame boundary yet

    assert ppu.completed_scanline_scroll_states == ()
    assert ppu.current_scanline_scroll_states == states


def test_frame_rollover_publishes_before_entering_next_frame():
    """
    Objective:
    Connect publication to the existing scanline/frame counter transition.
    """
    ppu = PPU()
    states = make_complete_states()
    ppu.current_scanline_scroll_states = list(states)
    ppu.scanline = 261
    ppu.cycle = 340

    ppu.step()

    assert ppu.frame == 1
    assert ppu.scanline == 0
    assert ppu.cycle == 0
    assert ppu.completed_scanline_scroll_states == tuple(states)
    assert ppu.current_scanline_scroll_states == [None] * 240
