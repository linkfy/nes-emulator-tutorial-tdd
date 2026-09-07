"""
Test 356 — Replace relative sleep pacing with absolute 60 FPS deadlines.

File to update:
    main.py

Expected manual behavior after this step:
When launched with PyPy and a legal local Super Mario Bros. ROM, startup may initially
run below the target while PyPy warms its frequently executed paths. After roughly 30
seconds, gameplay should become smooth and remain close to the 60 FPS long-term target
on a machine with sufficient processing headroom.

Why this step exists:
Each frontend-loop iteration advances one complete emulated frame. If the loop runs
faster than the intended display rate, gameplay, animation, and input progress too
quickly; if pacing delays every frame too much, the entire emulated machine runs too
slowly. The frontend therefore needs to align completed frames with a stable wall-clock
timeline rather than merely adding an approximate delay after each frame.

Relative pacing calculates every delay from the current frame's duration. Timer
overshoot and scheduling latency then move the starting point of the next frame, so
small errors can accumulate as timing drift. An absolute deadline instead gives every
frame a position on one continuing 60 Hz schedule. A frame that finishes early waits;
a slightly late frame keeps the established timeline; a delay of at least one complete
frame resets the schedule so the frontend does not attempt an unbounded catch-up burst.

At 60 FPS, consecutive scheduled frames are separated by approximately 16.67 ms. This
policy controls real-world presentation speed while leaving deterministic CPU, PPU,
and rendering transitions independent of the host clock.

Names and responsibilities:
    - No function is renamed.
    - NES_NTSC_FPS is replaced by TARGET_DISPLAY_FPS because this frontend policy now
      targets an integer 60 Hz display schedule.
    - TARGET_FRAME_SECONDS keeps its name, but is derived from TARGET_DISPLAY_FPS.
    - frame_start_time, frame_end_time, frame_elapsed_time, and wait_time are removed;
      they belong to the superseded relative-delay implementation.
    - next_frame_deadline is new mutable frontend scheduling state. It stores one
      absolute timestamp and advances by exactly one target duration per frame.

Complete main.py changes:

    # --- DELETED BLOCK: APPROXIMATE NTSC FRAME TARGET ---
    # NES_NTSC_FPS = 60.0988
    # TARGET_FRAME_SECONDS = 1.0 / NES_NTSC_FPS
    # --- END DELETED BLOCK ---

    # --- NEW BLOCK: 60 FPS ABSOLUTE FRAME TARGET ---
    TARGET_DISPLAY_FPS = 60
    TARGET_FRAME_SECONDS = 1.0 / TARGET_DISPLAY_FPS
    # --- END NEW BLOCK ---

    ...

    running = True
    # --- NEW LINE: FIRST ABSOLUTE FRAME DEADLINE ---
    next_frame_deadline = time.perf_counter() + TARGET_FRAME_SECONDS
    # --- END NEW LINE ---
    last_fps_report_time = time.perf_counter()
    frames_since_last_report = 0

    while running:
        # --- DELETED LINE: RELATIVE FRAME START ---
        # frame_start_time = time.perf_counter()
        # --- END DELETED LINE ---

        ...

        executed = console.step_until_next_frame()
        framebuffer = console.render_framebuffer()
        draw_framebuffer(window, framebuffer, SCALE)
        pygame.display.flip()

        # --- DELETED BLOCK: RELATIVE REMAINING-TIME SLEEP ---
        # frame_end_time = time.perf_counter()
        # frame_elapsed_time = frame_end_time - frame_start_time
        # wait_time = TARGET_FRAME_SECONDS - frame_elapsed_time
        #
        # if wait_time > 0:
        #     time.sleep(wait_time)
        # --- END DELETED BLOCK ---

        # --- NEW BLOCK: WAIT FOR AND ADVANCE THE ABSOLUTE DEADLINE ---
        while time.perf_counter() < next_frame_deadline:
            pass

        now = time.perf_counter()
        next_frame_deadline += TARGET_FRAME_SECONDS

        # Abandon a large backlog instead of creating a catch-up spiral.
        if now - next_frame_deadline >= TARGET_FRAME_SECONDS:
            next_frame_deadline = now + TARGET_FRAME_SECONDS
        # --- END NEW BLOCK ---

        ...

How the absolute deadline stabilizes frame timing:
Let one target frame duration be T = 16.67 ms.

    Fast frame:
        current deadline = 16.67 ms
        work finishes    = 14.00 ms
        wait             =  2.67 ms
        next deadline    = 16.67 + T = 33.34 ms

    Slightly late frame:
        current deadline = 33.34 ms
        work finishes    = 34.67 ms
        lateness         =  1.33 ms
        next deadline    = 33.34 + T = 50.01 ms

The late frame does not move the established timeline. The following frame starts
without extra waiting and has until 50.01 ms to recover the previous 1.33 ms delay.
If its work finishes at 48.67 ms, it waits until 50.01 ms and is synchronized again.

This addition is what preserves the timeline:

    next_frame_deadline += TARGET_FRAME_SECONDS

It advances from the previous scheduled deadline. Replacing it with
next_frame_deadline = now + TARGET_FRAME_SECONDS after every frame would preserve each
small delay and cause long-term timing drift.

    Severely late frame:
        current deadline           = 50.00 ms
        work finishes              = 90.00 ms
        normally advanced deadline = 66.67 ms
        remaining backlog         = 23.33 ms

The newly scheduled deadline is now more than one complete frame behind the current
time. Keeping it would cause repeated immediate catch-up frames, so the reset abandons
that stale backlog:

    next_frame_deadline = now + TARGET_FRAME_SECONDS

The new deadline becomes 106.67 ms. Small lateness therefore recovers against the
existing schedule, while severe lateness starts a fresh schedule instead of producing
an unbounded catch-up spiral.

The absolute deadline prevents relative timing drift. Small late frames may recover
against the existing schedule; falling more than one complete frame behind resets the
deadline and prevents an unbounded catch-up spiral.

Important invariants:
    - wall-clock pacing remains frontend policy
    - emulation, rendering, and presentation happen before waiting
    - FPS accounting happens after waiting
    - deadlines advance from the prior deadline, not from every fast frame's end
    - a delay of one complete frame or more resets the schedule
    - no relative time.sleep pacing remains

Trade-off:
The busy wait avoids the coarse wake-up behavior of short operating-system sleeps but
consumes more CPU and energy while a frame is early. It improves timing precision on a
general-purpose system; it does not turn the frontend into a hard real-time system or
make an over-budget frame finish faster.

Common misconception:
Frame pacing is not a performance optimization. It cannot raise slow execution to 60
FPS; it only prevents sufficiently fast execution from advancing emulated time too
quickly and limits long-term timing drift.
"""

import ast
import inspect

import pytest

import main
from emulator.rendering import nametable_renderer


pytestmark = pytest.mark.skipif(
    not hasattr(
        nametable_renderer,
        "_cached_nametable_with_palette_ram_pixels",
    ),
    reason="Complete Test 355 before activating Test 356",
)


def test_main_uses_absolute_sixty_fps_deadline_pacing():
    """Verify the complete replacement contract without running pygame or a ROM."""
    source = inspect.getsource(main.main)
    compact_source = "".join(source.split())

    assert main.TARGET_DISPLAY_FPS == 60
    assert main.TARGET_FRAME_SECONDS == pytest.approx(1.0 / 60)

    deadline_index = compact_source.index(
        "next_frame_deadline=time.perf_counter()+TARGET_FRAME_SECONDS"
    )
    step_index = compact_source.index(
        "console.step_until_next_frame()",
        deadline_index,
    )
    render_index = compact_source.index(
        "console.render_framebuffer()",
        step_index,
    )
    flip_index = compact_source.index("pygame.display.flip()", render_index)
    wait_index = compact_source.index(
        "whiletime.perf_counter()<next_frame_deadline:",
        flip_index,
    )
    count_index = compact_source.index(
        "frames_since_last_report+=1",
        wait_index,
    )

    assert deadline_index < step_index < render_index < flip_index
    assert flip_index < wait_index < count_index
    assert "next_frame_deadline+=TARGET_FRAME_SECONDS" in compact_source
    assert "now-next_frame_deadline>=TARGET_FRAME_SECONDS" in compact_source
    assert "next_frame_deadline=now+TARGET_FRAME_SECONDS" in compact_source

    syntax_tree = ast.parse(source)
    time_sleep_calls = [
        node
        for node in ast.walk(syntax_tree)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "time"
            and node.func.attr == "sleep"
        )
    ]

    assert time_sleep_calls == []
