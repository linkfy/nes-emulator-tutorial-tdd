"""
Cap the manual frontend loop to NES NTSC speed.

File to update:
    main.py

Why this step exists:
After the faster pygame framebuffer upload and the optional PyPy launchers, the
manual emulator can run faster than the real NES. During tutorial development, the
uncapped path reached roughly 90-120 FPS.

Running faster is useful performance evidence, but it makes gameplay, animation,
and input timing too fast. The frontend should wait when a frame finishes early.

Key term: frame pacing
Frame pacing means delaying presentation when an emulated frame finishes faster
than the target wall-clock duration.

Target NTSC timing:

    NES_NTSC_FPS = 60.0988
    TARGET_FRAME_SECONDS = 1.0 / NES_NTSC_FPS

One target frame is approximately:

    16.64 milliseconds

Example implementation:

    # --- NEW BLOCK: NES FRAME-TIME TARGET ---
    NES_NTSC_FPS = 60.0988
    TARGET_FRAME_SECONDS = 1.0 / NES_NTSC_FPS
    # --- END NEW BLOCK ---

    ...

    while running:
        # --- NEW LINE: START THIS FRAME'S TIMER ---
        frame_start_time = time.perf_counter()
        # --- END NEW LINE ---

        for event in pygame.event.get():
            ...

        executed = console.step_until_next_frame()
        framebuffer = console.render_framebuffer()
        draw_framebuffer(window, framebuffer, SCALE)
        pygame.display.flip()

        # --- NEW BLOCK: WAIT FOR THE UNUSED FRAME BUDGET ---
        # Sleep only for the unused part of this frame's time budget.
        frame_end_time = time.perf_counter()
        frame_elapsed_time = frame_end_time - frame_start_time
        wait_time = TARGET_FRAME_SECONDS - frame_elapsed_time

        if wait_time > 0:
            time.sleep(wait_time)
        # --- END NEW BLOCK ---

        # --- UPDATED BLOCK: MEASURE FPS AFTER PACING ---
        # Measure FPS after sleeping so the report shows paced gameplay speed.
        frames_since_last_report += 1
        now = time.perf_counter()
        elapsed = now - last_fps_report_time

        if elapsed >= FPS_REPORT_INTERVAL_SECONDS:
            fps = frames_since_last_report / elapsed
            print(f"fps={fps:.1f}")
            frames_since_last_report = 0
            last_fps_report_time = now
        # --- END UPDATED BLOCK ---

Important invariants:

    Fast frame:
        frame_elapsed_time < TARGET_FRAME_SECONDS
        wait_time > 0
        frontend sleeps for the remaining budget

    Slow frame:
        frame_elapsed_time >= TARGET_FRAME_SECONDS
        wait_time <= 0
        frontend does not sleep

Why not sleep in Console/CPU/PPU?
The emulator core owns deterministic emulated state transitions. Wall-clock pacing
is a frontend policy, so only main.py should sleep.

Common misconception:
Frame pacing does not fix CPU-cycle accuracy and does not make slow emulation
faster. It only prevents sufficiently fast emulation from running faster than the
target hardware.

Current manual reference:
Continue using the local, user-provided MarioBros.nes for this performance step.
Super Mario Bros. validation is deferred until sprite 0 hit is implemented.

Why source-shape tests?
Automated tests must not call main(), sleep for real, open pygame, or require a
commercial ROM. These tests verify the pacing structure without running the manual
loop.

Future compatibility:
Step 356 replaces this lesson's relative-sleep source shape with absolute-deadline
pacing. When that complete replacement is detected, only the six obsolete
source-shape assertions below are skipped. The enduring frontend/core boundary and
one-emulated-frame-per-loop assertions remain active, while Test 356 validates the
new contract. Do not add dead wait_time or time.sleep compatibility code to main.py.

Out of scope:
    - CPU branch/page-cross cycle accuracy
    - sprite 0 hit
    - Super Mario Bros. validation
    - pygame rendering optimization (completed in the previous step)
    - calling main() from pytest
"""

import inspect
from pathlib import Path

import pytest

import main


def _uses_absolute_deadline_pacing() -> bool:
    """Detect the complete Step 356 replacement without changing production code."""
    source = inspect.getsource(main.main)
    compact_source = "".join(source.split())

    return (
        hasattr(main, "TARGET_DISPLAY_FPS")
        and hasattr(main, "TARGET_FRAME_SECONDS")
        and "next_frame_deadline" in compact_source
        and "whiletime.perf_counter()<next_frame_deadline:" in compact_source
        and "next_frame_deadline+=TARGET_FRAME_SECONDS" in compact_source
    )


legacy_relative_sleep_pacing_only = pytest.mark.skipif(
    _uses_absolute_deadline_pacing(),
    reason="Step 356 supersedes relative-sleep pacing with absolute deadlines",
)


@legacy_relative_sleep_pacing_only
def test_main_defines_ntsc_nes_fps_target():
    """
    Objective:
    Name the approximate NTSC NES frame rate explicitly instead of using an
    unexplained sleep duration.
    """
    assert hasattr(main, "NES_NTSC_FPS")
    assert main.NES_NTSC_FPS == pytest.approx(60.0988)


@legacy_relative_sleep_pacing_only
def test_main_derives_target_frame_seconds_from_nes_fps():
    """
    Objective:
    Keep FPS and frame-duration constants connected by one clear invariant.
    """
    assert hasattr(main, "TARGET_FRAME_SECONDS")
    assert main.TARGET_FRAME_SECONDS == pytest.approx(1.0 / main.NES_NTSC_FPS)
    assert main.TARGET_FRAME_SECONDS == pytest.approx(0.016639, abs=0.000001)


@legacy_relative_sleep_pacing_only
def test_main_starts_frame_timer_before_emulation_work():
    """
    Objective:
    The frame budget should include event handling, emulation, rendering, and pygame
    display work.
    """
    source = inspect.getsource(main.main)

    start_index = source.index("frame_start_time = time.perf_counter()")
    # Search after the frame timer so the earlier initial framebuffer used to size
    # the pygame window is not mistaken for the per-frame render call.
    step_index = source.index("console.step_until_next_frame()", start_index)
    render_index = source.index("console.render_framebuffer()", step_index)
    flip_index = source.index("pygame.display.flip()", render_index)

    assert start_index < step_index < render_index < flip_index


@legacy_relative_sleep_pacing_only
def test_main_computes_remaining_time_after_display_work():
    """
    Objective:
    Sleep should use only the unused part of the target frame duration.
    """
    source = inspect.getsource(main.main)

    flip_index = source.index("pygame.display.flip()")
    end_index = source.index("frame_end_time = time.perf_counter()")
    elapsed_index = source.index(
        "frame_elapsed_time = frame_end_time - frame_start_time"
    )
    wait_index = source.index(
        "wait_time = TARGET_FRAME_SECONDS - frame_elapsed_time"
    )

    assert flip_index < end_index < elapsed_index < wait_index


@legacy_relative_sleep_pacing_only
def test_main_sleeps_only_when_frame_finishes_early():
    """
    Objective:
    Negative wait times represent slow frames and must never be passed to
    time.sleep().
    """
    source = inspect.getsource(main.main)

    condition_index = source.index("if wait_time > 0:")
    sleep_index = source.index("time.sleep(wait_time)")

    assert condition_index < sleep_index


@legacy_relative_sleep_pacing_only
def test_main_measures_reported_fps_after_frame_pacing_sleep():
    """
    Objective:
    The terminal FPS signal should show paced gameplay speed, not uncapped raw
    throughput.
    """
    source = inspect.getsource(main.main)

    sleep_index = source.index("time.sleep(wait_time)")
    count_index = source.index("frames_since_last_report += 1")
    fps_time_index = source.index("now = time.perf_counter()", count_index)

    assert sleep_index < count_index < fps_time_index


def test_frame_pacing_stays_in_main_not_emulator_core():
    """
    Objective:
    Wall-clock waiting is frontend policy. Emulator core modules must remain free
    from time.sleep().
    """
    core_files = [
        Path("emulator/console.py"),
        Path("emulator/cpu/cpu.py"),
        Path("emulator/ppu/ppu.py"),
        Path("emulator/rendering/frame_compositor.py"),
    ]

    for file_path in core_files:
        assert "time.sleep" not in file_path.read_text()


def test_main_still_uses_one_emulated_ppu_frame_per_frontend_iteration():
    """
    Objective:
    Frame pacing delays presentation; it should not replace or multiply the existing
    emulated frame-step mechanism.
    """
    source = inspect.getsource(main.main)

    assert source.count("console.step_until_next_frame()") == 1
