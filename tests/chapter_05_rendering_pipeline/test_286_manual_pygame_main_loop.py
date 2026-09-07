"""
Add a manual pygame main loop for the framebuffer smoke runner.

Files to update/create:
    tools/show_framebuffer.py
    tools/__init__.py

Why this step exists:
The previous step added helpers that can draw a Framebuffer onto a pygame Surface.
This step adds the manual window loop so a developer can visually confirm that the
pure Framebuffer data can be displayed.

Important:
This is a manual smoke runner, not an automated rendering test. Automated tests
must not open a real pygame window.

Why create tools/__init__.py?
We want to run the tool as a Python module:

    uv run python -m tools.show_framebuffer

Python's -m flag expects a module name, not a file path. The module name uses dots:

    tools.show_framebuffer

not:

    tools/show_framebuffer.py

Adding tools/__init__.py makes tools an explicit package and avoids confusion
about import/module resolution.

Manual commands:

    Correct:
        uv run python -m tools.show_framebuffer

    Incorrect:
        uv run python -m tools/show_framebuffer.py
        uv run python -m tools.show_framebuffer.py

What is the pygame main loop?
A pygame main loop keeps a window alive by repeatedly:

    1. reading events
    2. drawing to the window surface
    3. presenting the drawn image

Minimal shape:

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        draw_framebuffer(window, framebuffer, SCALE)
        pygame.display.flip()

What is pygame.display.flip()?
It presents the current contents of the window surface to the display. In simple
terms:

    draw pixels -> flip -> user sees pixels

Expected manual visual result:
The checkerboard framebuffer should show a black/white or dark/white pattern like:

    +----------------+
    | ██  ██  ██  ██ |
    | ██  ██  ██  ██ |
    |   ██  ██  ██   |
    |   ██  ██  ██   |
    | ██  ██  ██  ██ |
    | ██  ██  ██  ██ |
    +----------------+

The exact block size depends on the framebuffer size and SCALE, but the important
visual check is:

    alternating light and dark squares are visible
    closing the window exits cleanly

Suggested implementation example:

    SCALE = 3


    def main() -> None:
        framebuffer = make_checkerboard_framebuffer()

        pygame.init()
        try:
            window = pygame.display.set_mode(
                (framebuffer.width * SCALE, framebuffer.height * SCALE)
            )
            pygame.display.set_caption("Framebuffer Smoke Test")

            running = True
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False

                draw_framebuffer(window, framebuffer, SCALE)
                pygame.display.flip()
        finally:
            pygame.quit()


    if __name__ == "__main__":
        main()

Architecture rule:
pygame remains outside emulator core. This file may import pygame because it lives
under tools/. Do not import pygame from emulator/rendering, emulator/ppu, or
emulator/console.

Out of scope:
    - testing the real pygame window in pytest
    - loading ROMs
    - rendering live Console output
    - controller input
    - sprites
"""

import inspect
from pathlib import Path

from tools import show_framebuffer


def test_tools_package_init_file_exists_for_module_execution():
    """
    Objective:
    tools/__init__.py makes the manual tools directory an explicit Python package.

    This supports:
        uv run python -m tools.show_framebuffer
    """
    assert Path("tools/__init__.py").exists()


def test_show_framebuffer_declares_scale_constant():
    """
    Objective:
    SCALE controls how large each framebuffer pixel appears in the pygame window.
    """
    assert hasattr(show_framebuffer, "SCALE")
    assert isinstance(show_framebuffer.SCALE, int)
    assert show_framebuffer.SCALE >= 1


def test_show_framebuffer_declares_main_function_but_test_does_not_call_it():
    """
    Objective:
    The manual runner exposes main(), but automated tests must not call it because
    it opens a real pygame window and waits for events.
    """
    assert hasattr(show_framebuffer, "main")
    assert callable(show_framebuffer.main)


def test_main_function_uses_pygame_window_loop_concepts():
    """
    Objective:
    main() should include the important pygame window-loop operations:

        pygame.init()
        pygame.display.set_mode(...)
        pygame.event.get()
        pygame.display.flip()
        pygame.quit()

    This checks source shape instead of opening a window.
    """
    source = inspect.getsource(show_framebuffer.main)

    assert "pygame.init()" in source
    assert "pygame.display.set_mode" in source
    assert "pygame.event.get()" in source
    assert "pygame.display.flip()" in source
    assert "pygame.quit()" in source


def test_show_framebuffer_has_main_guard_for_direct_execution():
    """
    Objective:
    The tool should be runnable directly or with module execution while avoiding
    accidental main-loop execution during import.

    Expected guard:
        if __name__ == "__main__":
            main()
    """
    source = Path("tools/show_framebuffer.py").read_text()

    assert 'if __name__ == "__main__"' in source
    assert "main()" in source


def test_manual_runner_keeps_pygame_outside_emulator_core():
    """
    Objective:
    Document the architectural boundary. Pygame belongs in tools/frontend code, not
    in emulator core rendering modules.
    """
    core_files = [
        Path("emulator/rendering/framebuffer.py"),
        Path("emulator/rendering/color_index_renderer.py"),
        Path("emulator/rendering/pattern_table_renderer.py"),
        Path("emulator/rendering/nametable_renderer.py"),
        Path("emulator/rendering/ppu_background_renderer.py"),
        Path("emulator/console.py"),
    ]

    for file_path in core_files:
        assert "import pygame" not in file_path.read_text()
