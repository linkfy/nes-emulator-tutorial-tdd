"""
Add manual pygame background display to main_only_background.py.

File to create/update on root folder:
    main_only_background.py

Why this step exists:
core_validator.py proves that the emulator can boot a local ROM and step frames
without pygame. main_only_background.py is the historical background-only visual
manual runner: it should use pygame to display the background Framebuffer produced
by the emulator after each frame.

Recommended workflow:
Start by copying the working structure from core_validator.py, then add only the
missing pygame/display pieces:

    - import pygame
    - import draw_framebuffer from tools.show_framebuffer
    - define SCALE
    - create an initial framebuffer for window dimensions
    - open a pygame window
    - process pygame.QUIT events
    - after each frame step, render the background framebuffer
    - draw the framebuffer and flip the display
    - call pygame.quit() in finally

Important boundary:
pygame is allowed in main_only_background.py because it is a manual/frontend entry
point.
pygame must not be imported by emulator core modules.

Important legal/testing rule:
The tutorial repository must not include commercial ROM files. Automated tests must
not require MarioBros.nes or open a real pygame window.

Reference hash used during tutorial development [Mario Bros. (World).nes]:

    MD5 5d7bcc400a2fb5fa27346da345d3bb62  MarioBros.nes
    SHA1 314b6e46e814f955b52ac954f67dab849582fe77

This hash is only a manual reference. Tests must not require this file or this
exact hash because users may have different legal dumps/revisions.

Suggested implementation example:

    from pathlib import Path

    import pygame

    from emulator.bus.cpu_bus import CpuBus
    from emulator.cartridge.cartridge import Cartridge
    from emulator.console import Console
    from emulator.cpu.cpu import CPU
    from tools.show_framebuffer import draw_framebuffer


    ROM_PATH = Path("MarioBros.nes")
    debug_mode = False
    SCALE = 3


    def main() -> None:
        if not ROM_PATH.exists():
            raise FileNotFoundError(
                "MarioBros.nes not found. Provide your own legal local copy. "
                "This file is intentionally not included in the tutorial repository."
            )

        cartridge = Cartridge.from_ines_bytes(ROM_PATH.read_bytes())

        cpu_bus = CpuBus(cartridge=cartridge)
        cpu = CPU(cpu_bus)
        console = Console(cpu=cpu, ppu=cpu_bus.ppu)

        cpu.reset()
        framebuffer = console.render_background_framebuffer()

        print(f"Loaded {ROM_PATH}")
        print(f"CPU reset PC = ${cpu.pc:04X}")
        print("Starting frame loop. Close the window or press Ctrl+C to stop.")

        pygame.init()
        try:
            window = pygame.display.set_mode(
                (framebuffer.width * SCALE, framebuffer.height * SCALE)
            )
            pygame.display.set_caption("NES Background")

            running = True
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False

                executed = console.step_until_next_frame()

                framebuffer = console.render_background_framebuffer()
                draw_framebuffer(window, framebuffer, SCALE)
                pygame.display.flip()

                if debug_mode:
                    print(
                        f"frame={console.ppu.frame} "
                        f"pc=${cpu.pc:04X} "
                        f"instructions={executed}"
                    )
        except KeyboardInterrupt:
            print("\nStopped by user.")
        finally:
            pygame.quit()


    if __name__ == "__main__":
        main()

Manual command:

    uv run python main_only_background.py

Expected manual behavior:
main_only_background.py opens a pygame window and displays the current background
framebuffer. The window may look incomplete because sprites are not implemented in
this historical runner. Close the window or press Ctrl+C to stop.

Example visual expectation, roughly:

    +------------------------------+
    |                              |
    |          MARIO BROS.         |
    |                              |
    |        1 PLAYER GAME A       |
    |        1 PLAYER GAME B       |
    |        2 PLAYER GAME A       |
    |        2 PLAYER GAME B       |
    |                              |
    |   background is shown        |
    |   sprites are  missing       |
    |                              |
    +------------------------------+

After 30 seconds - 1 minute, you should also see a background/layout similar to
the classic Mario Bros. 1983 stage. Sprites are still missing, but the background
scene should make the emulator feel alive:

    +------------------------------+
    |  I-0000   TOP-0000  II-0000  |
    |                              |
    |  ====                  ====  |
    |==                          ==|
    |                              |
    |        ──────────────        |
    |─────                    ─────|
    |                              |
    |                              |
    | ─────────── POW  ─────────── |
    |====                      ====|
    |------------------------------|
    +------------------------------+

This is only an approximate ASCII sketch. The important manual signal is that the
background/title/stage tiles appear and change over time. Missing moving
characters/enemies are expected until sprite rendering is implemented.

Performance note:
The manual pygame runner may feel slow right now. That is expected at this stage.
The current draw_framebuffer helper is intentionally simple and draws many scaled
rectangles from Python. Future optimization can replace it with a faster framebuffer
upload path, but this step focuses on expected visual output and architecture
boundaries, not speed.

Why this test does not call main():
main_only_background.py opens a real pygame window and runs a manual loop.
Automated tests must stay finite and should inspect structure only.

Out of scope:
    - fast framebuffer upload optimization
    - pygame keyboard/controller mapping
    - sprite rendering
    - verifying exact visual pixels from a commercial ROM
    - calling main() from pytest
"""

import inspect
import importlib
from pathlib import Path


background_main = importlib.import_module("main_only_background")


def test_main_only_background_py_exists_and_exposes_visual_runner_configuration():
    """
    Objective:
    main_only_background.py is the background-only visual manual runner and exposes
    the expected manual knobs.
    """
    assert Path("main_only_background.py").exists()
    assert hasattr(background_main, "ROM_PATH")
    assert hasattr(background_main, "debug_mode")
    assert hasattr(background_main, "SCALE")
    assert hasattr(background_main, "main")
    assert callable(background_main.main)


def test_main_only_background_rom_path_points_to_local_mariobros_file_name_without_requiring_it():
    """
    Objective:
    main_only_background.py documents the expected local ROM filename, but pytest
    must not require that file to exist.
    """
    assert isinstance(background_main.ROM_PATH, Path)
    assert background_main.ROM_PATH.name == "MarioBros.nes"


def test_main_only_background_debug_mode_exists_but_test_does_not_freeze_value():
    """
    Objective:
    debug_mode is a manual/developer knob. The test verifies existence only so
    future tutorial steps can change the default.
    """
    assert hasattr(background_main, "debug_mode")


def test_main_only_background_scale_exists_for_manual_window_size():
    """
    Objective:
    SCALE controls how large each NES framebuffer pixel appears in the pygame
    window.
    """
    assert isinstance(background_main.SCALE, int)
    assert background_main.SCALE >= 1


def test_main_only_background_uses_real_rom_boot_construction_path():
    """
    Objective:
    main_only_background.py should keep the same emulator ownership path as
    core_validator.py.
    """
    source = inspect.getsource(background_main.main)

    assert "Cartridge.from_ines_bytes" in source
    assert "CpuBus(cartridge=cartridge)" in source
    assert "CPU(cpu_bus)" in source
    assert "Console(cpu=cpu, ppu=cpu_bus.ppu)" in source
    assert "cpu.reset()" in source


def test_main_uses_pygame_window_loop_concepts():
    """
    Objective:
    main_only_background.py should contain the core pygame window-loop operations
    without tests opening the window.
    """
    source = inspect.getsource(background_main.main)

    assert "pygame.init()" in source
    assert "pygame.display.set_mode" in source
    assert "pygame.display.set_caption" in source
    assert "pygame.event.get()" in source
    assert "pygame.QUIT" in source
    assert "pygame.display.flip()" in source
    assert "pygame.quit()" in source


def test_main_renders_background_framebuffer_and_draws_it():
    """
    Objective:
    The visual runner should display the emulator-produced background framebuffer,
    not a synthetic checkerboard.
    """
    source = inspect.getsource(background_main.main)

    assert "console.render_background_framebuffer()" in source
    assert "draw_framebuffer" in Path("main_only_background.py").read_text()
    assert "draw_framebuffer(window, framebuffer, SCALE)" in source


def test_main_steps_emulation_by_frame_before_drawing():
    """
    Objective:
    main_only_background.py should advance emulation using the frame-level helper
    before rendering the next visible background.
    """
    source = inspect.getsource(background_main.main)

    assert "console.step_until_next_frame()" in source


def test_main_can_exit_by_window_close_or_ctrl_c():
    """
    Objective:
    The manual visual loop should support both pygame window close and Ctrl+C.
    """
    source = inspect.getsource(background_main.main)

    assert "running = True" in source
    assert "running = False" in source
    assert "KeyboardInterrupt" in source
    assert "Stopped by user" in source


def test_main_has_main_guard_so_importing_does_not_start_window_loop():
    """
    Objective:
    Importing main_only_background.py from pytest must not open a pygame window.
    """
    source = Path("main_only_background.py").read_text()

    assert 'if __name__ == "__main__"' in source
    assert "main()" in source


def test_pygame_stays_outside_emulator_core_modules():
    """
    Objective:
    pygame belongs in manual/frontend code. The emulator core should still be
    importable and testable without pygame.
    """
    core_files = [
        Path("emulator/bus/cpu_bus.py"),
        Path("emulator/console.py"),
        Path("emulator/input/controller.py"),
        Path("emulator/rendering/framebuffer.py"),
        Path("emulator/rendering/ppu_background_renderer.py"),
        Path("emulator/rendering/nametable_renderer.py"),
    ]

    for file_path in core_files:
        assert "import pygame" not in file_path.read_text()
