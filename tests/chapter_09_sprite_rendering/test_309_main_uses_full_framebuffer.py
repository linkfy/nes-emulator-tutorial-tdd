"""
Create main.py from main_only_background.py and use Console.render_framebuffer().

Files involved:
    main_only_background.py
    main.py

Why this step exists:
main_only_background.py preserves the previous manual runner that displayed only
the background framebuffer. For this step, copy that file to main.py and then apply
the full-frame rendering modifications there.

Console now exposes render_framebuffer(), which returns background + sprites in one
pure Framebuffer. The new main.py should use that full-frame render path instead of
the older background-only helper.

The template file, main_only_background.py, displays:

    console.render_background_framebuffer()

After copying it to main.py and applying this step, main.py displays:

    console.render_framebuffer()

This lets the manual pygame runner show sprites such as Mario/enemies/items when
the current PPU state contains valid OAM, CHR, and sprite palette data.

Suggested implementation workflow:

    cp main_only_background.py main.py

Then update main.py so this line:

    framebuffer = console.render_background_framebuffer()

becomes:

    framebuffer = console.render_framebuffer()

Do this both before creating the pygame window and after each frame step.

Important preservation rule:
Do not delete main_only_background.py. Older tutorial tests use it as a stable
historical checkpoint for the background-only runner.

Known visual limitation:
Sprites may appear in front of pipes/tubes incorrectly. That is expected for now
because sprite/background priority bit 5 is decoded but not applied yet. The next
planned work is a background opacity mask and priority-aware composition.

Manual command:

    uv run python main.py

Expected manual behavior:
The pygame window should still show the background, and sprites should now appear.
Visual priority may still be wrong. Performance may still be slow because the
current pygame drawing helper is intentionally simple.

Out of scope:
    - background opacity mask
    - sprite/background priority behavior
    - sprite 0 hit
    - sprite overflow
    - fast framebuffer upload optimization
    - calling main() from pytest
"""

import inspect
from pathlib import Path

import main


def test_main_uses_console_render_framebuffer_for_initial_window_size():
    """
    Objective:
    The initial framebuffer used for window dimensions should come from the full
    background+sprites render path.
    """
    source = inspect.getsource(main.main)

    assert "framebuffer = console.render_framebuffer()" in source


def test_main_no_longer_calls_background_only_render_helper():
    """
    Objective:
    main.py should display the full framebuffer, while main_only_background.py keeps
    the historical background-only debug path.
    """
    source = inspect.getsource(main.main)

    assert "render_background_framebuffer" not in source


def test_main_still_steps_frame_before_redrawing_full_framebuffer():
    """
    Objective:
    Each visual update should advance emulation by one PPU frame, then render the
    current full framebuffer.
    """
    source = inspect.getsource(main.main)

    step_index = source.index("console.step_until_next_frame()")
    render_index = source.rindex("console.render_framebuffer()")

    assert step_index < render_index


def test_main_still_draws_framebuffer_with_existing_pygame_helper():
    """
    Objective:
    This step changes the framebuffer source, not the pygame drawing mechanism.
    """
    source = inspect.getsource(main.main)
    full_source = Path("main.py").read_text()

    assert "from tools.show_framebuffer import draw_framebuffer" in full_source
    assert "draw_framebuffer(window, framebuffer, SCALE)" in source
    assert "pygame.display.flip()" in source


def test_main_keeps_keyboard_controller_mapping_after_full_framebuffer_switch():
    """
    Objective:
    Switching to full-frame rendering should not remove controller input handling.
    """
    source = inspect.getsource(main.main)

    assert "pygame.KEYDOWN" in source
    assert "pygame.KEYUP" in source
    assert "handle_key_event(cpu_bus.controller_1, event.key, True)" in source
    assert "handle_key_event(cpu_bus.controller_1, event.key, False)" in source


def test_main_keeps_error_reporting_after_full_framebuffer_switch():
    """
    Objective:
    Manual ROM execution should still print emulator context before re-raising
    unexpected errors.
    """
    source = inspect.getsource(main.main)

    assert "except Exception as error" in source
    assert "print_emulation_error(error, console)" in source
    assert "raise" in source


def test_main_keeps_manual_exit_paths_after_full_framebuffer_switch():
    """
    Objective:
    The manual pygame loop should still support window close and Ctrl+C.
    """
    source = inspect.getsource(main.main)

    assert "pygame.QUIT" in source
    assert "running = False" in source
    assert "except KeyboardInterrupt" in source
    assert "Stopped by user" in source


def test_main_full_framebuffer_step_keeps_pygame_outside_emulator_core():
    """
    Objective:
    pygame remains a manual/frontend dependency only. Full-frame rendering in
    Console/rendering modules must stay pure.
    """
    core_files = [
        Path("emulator/console.py"),
        Path("emulator/rendering/frame_compositor.py"),
        Path("emulator/rendering/sprite_renderer.py"),
        Path("emulator/rendering/ppu_background_renderer.py"),
    ]

    for file_path in core_files:
        assert "import pygame" not in file_path.read_text()
