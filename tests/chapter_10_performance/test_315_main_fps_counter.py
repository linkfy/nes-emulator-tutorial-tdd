"""
Add a simple periodic FPS counter to main.py.

File to update:
    main.py

Why this step exists:
Before optimizing pygame rendering or emulator speed, the manual runner should show
a simple end-to-end FPS signal in the terminal.

The FPS counter should measure the complete manual frame path:

    Console.step_until_next_frame()
    Console.render_framebuffer()
    draw_framebuffer(...)
    pygame.display.flip()

Suggested implementation example:

    import time

    FPS_REPORT_INTERVAL_SECONDS = 1.0

    ...

    running = True
    last_fps_report_time = time.perf_counter()
    frames_since_last_report = 0

    while running:
        ...

        executed = console.step_until_next_frame()
        framebuffer = console.render_framebuffer()
        draw_framebuffer(window, framebuffer, SCALE)
        pygame.display.flip()

        frames_since_last_report += 1
        now = time.perf_counter()
        elapsed = now - last_fps_report_time

        if elapsed >= FPS_REPORT_INTERVAL_SECONDS:
            fps = frames_since_last_report / elapsed
            print(f"fps={fps:.1f}")
            frames_since_last_report = 0
            last_fps_report_time = now

Important:
This is intentionally simple. It does not separate emulation time from render time.
It only gives a visible terminal signal before optimization work.

Why source-shape tests?
main.py opens pygame and runs a manual loop. Automated tests must not call main(),
open a window, or require a commercial ROM.

Out of scope:
    - optimizing pygame drawing
    - frame pacing / speed cap
    - profiling individual subsystems
    - launching PyPy
    - calling main() from pytest
"""

import inspect

import main


def test_main_imports_time_for_fps_measurement():
    """
    Objective:
    FPS reporting should use a monotonic high-resolution timer from the standard
    library.
    """
    source = inspect.getsource(main)

    assert "import time" in source


def test_main_defines_one_second_fps_report_interval():
    """
    Objective:
    The first FPS counter should be intentionally simple and report about once per
    second.
    """
    assert hasattr(main, "FPS_REPORT_INTERVAL_SECONDS")
    assert main.FPS_REPORT_INTERVAL_SECONDS == 1.0


def test_main_initializes_fps_counter_state_before_loop():
    """
    Objective:
    main.py should track when the previous report happened and how many frames have
    completed since then.
    """
    source = inspect.getsource(main.main)

    assert "last_fps_report_time = time.perf_counter()" in source
    assert "frames_since_last_report = 0" in source


def test_main_counts_frames_after_display_flip():
    """
    Objective:
    The FPS counter should measure the full manual frame path, including pygame
    drawing and display flip.
    """
    source = inspect.getsource(main.main)

    flip_index = source.index("pygame.display.flip()")
    count_index = source.index("frames_since_last_report += 1")

    assert flip_index < count_index


def test_main_prints_fps_when_one_second_interval_elapsed():
    """
    Objective:
    main.py should compute frames / elapsed time and print a small terminal signal.
    """
    source = inspect.getsource(main.main)

    assert "elapsed = now - last_fps_report_time" in source
    assert "elapsed >= FPS_REPORT_INTERVAL_SECONDS" in source
    assert "fps = frames_since_last_report / elapsed" in source
    assert "fps=" in source


def test_main_resets_fps_counter_after_report():
    """
    Objective:
    After printing a report, the next one-second window should start fresh.
    """
    source = inspect.getsource(main.main)

    assert "frames_since_last_report = 0" in source
    assert "last_fps_report_time = now" in source


def test_fps_counter_stays_in_manual_frontend_not_emulator_core():
    """
    Objective:
    FPS reporting is manual/frontend observability. The emulator core should not
    import time for display reporting.
    """
    core_files = [
        "emulator/console.py",
        "emulator/cpu/cpu.py",
        "emulator/ppu/ppu.py",
        "emulator/rendering/frame_compositor.py",
    ]

    for file_path in core_files:
        source = open(file_path, encoding="utf-8").read()
        assert "import time" not in source
