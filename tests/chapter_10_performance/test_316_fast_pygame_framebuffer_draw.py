"""
Improve pygame framebuffer drawing by replacing per-pixel rectangles with bulk blit.

File to update:
    tools/show_framebuffer.py

Why this step exists:
The original draw_framebuffer() was intentionally simple and educational:

    for each framebuffer pixel:
        create/fill one scaled pygame rectangle

For a NES frame, that means:

    256 * 240 = 61,440 pygame drawing operations per frame

That is slow because Python repeatedly crosses into pygame/SDL for thousands of
tiny rectangles.

This step keeps the old implementation for comparison by renaming it:

    old_draw_framebuffer(...)

Then it creates a new faster draw_framebuffer(...) that:

    1. packs the framebuffer pixels into one RGB byte buffer
    2. creates one pygame Surface from that buffer
    3. scales that Surface when needed
    4. blits the complete image to the window

Mental model:

    Old path:
        Python -> pygame draw tiny rect
        Python -> pygame draw tiny rect
        Python -> pygame draw tiny rect
        ... 61,440 times per frame

    New path:
        Python builds one RGB buffer
        pygame uploads/scales/blits one image

Bulk operations are usually much faster than many small Python-to-pygame calls.

Example implementation:

    def old_draw_framebuffer(
        surface: pygame.Surface,
        framebuffer: Framebuffer,
        scale: int,
    ) -> None:
        # Keep the old rectangle-based implementation for comparison.
        ...


    def draw_framebuffer(
        surface: pygame.Surface,
        framebuffer: Framebuffer,
        scale: int,
    ) -> None:
        # Write the framebuffer to pygame surface using one image upload.
        rgb_bytes = bytearray(framebuffer.width * framebuffer.height * 3)

        write_index = 0
        for color in framebuffer.pixels:
            red, green, blue = color
            rgb_bytes[write_index] = red
            rgb_bytes[write_index + 1] = green
            rgb_bytes[write_index + 2] = blue
            write_index += 3

        frame_surface = pygame.image.frombuffer(
            bytes(rgb_bytes),
            (framebuffer.width, framebuffer.height),
            "RGB",
        )

        if scale == 1:
            surface.blit(frame_surface, (0, 0))
            return

        scaled_surface = pygame.transform.scale(
            frame_surface,
            (framebuffer.width * scale, framebuffer.height * scale),
        )
        surface.blit(scaled_surface, (0, 0))

Important boundary:
This optimization belongs in tools/show_framebuffer.py. The emulator core still
produces a pure Framebuffer and must not import pygame.

Out of scope:
    - caching surfaces/buffers
    - NumPy/surfarray
    - Numba
    - changing main.py
    - frame pacing / speed cap
"""

import inspect
from pathlib import Path

from tools import show_framebuffer


def test_old_draw_framebuffer_is_preserved_for_comparison():
    """
    Objective:
    Keep the old rectangle-based implementation available as a teaching comparison.
    """
    assert hasattr(show_framebuffer, "old_draw_framebuffer")
    assert callable(show_framebuffer.old_draw_framebuffer)


def test_draw_framebuffer_public_api_stays_the_same():
    """
    Objective:
    main.py should not need to change. The optimization should keep the same helper
    name and parameters.
    """
    signature = inspect.signature(show_framebuffer.draw_framebuffer)

    assert list(signature.parameters) == ["surface", "framebuffer", "scale"]


def test_new_draw_framebuffer_uses_pygame_image_frombuffer():
    """
    Objective:
    The new renderer should upload one RGB image buffer instead of drawing thousands
    of rectangles.
    """
    source = inspect.getsource(show_framebuffer.draw_framebuffer)

    assert "pygame.image.frombuffer" in source
    assert '"RGB"' in source or "'RGB'" in source


def test_new_draw_framebuffer_uses_scale_and_blit():
    """
    Objective:
    Scaling/blitting a complete Surface is the important pygame-side optimization.
    """
    source = inspect.getsource(show_framebuffer.draw_framebuffer)

    assert "pygame.transform.scale" in source
    assert ".blit(" in source


def test_new_draw_framebuffer_does_not_use_per_pixel_rectangles():
    """
    Objective:
    The optimized draw_framebuffer should not create pygame.Rect objects or call
    surface.fill for every pixel.
    """
    source = inspect.getsource(show_framebuffer.draw_framebuffer)

    assert "pygame.Rect" not in source
    assert ".fill(" not in source


def test_old_draw_framebuffer_still_documents_the_original_slow_path():
    """
    Objective:
    The old implementation should remain recognizable as the rectangle/fill version
    for students comparing the two approaches.
    """
    source = inspect.getsource(show_framebuffer.old_draw_framebuffer)

    assert "pygame.Rect" in source
    assert ".fill(" in source


def test_main_still_uses_draw_framebuffer_name_after_renderer_optimization():
    """
    Objective:
    This step changes the helper internals, not the main.py call site.
    """
    source = Path("main.py").read_text()

    assert "from tools.show_framebuffer import draw_framebuffer" in source
    assert "draw_framebuffer(window, framebuffer, SCALE)" in source
    assert "old_draw_framebuffer" not in source


def test_pygame_renderer_optimization_stays_outside_emulator_core():
    """
    Objective:
    pygame is still a frontend/tool dependency only.
    """
    core_files = [
        Path("emulator/console.py"),
        Path("emulator/rendering/framebuffer.py"),
        Path("emulator/rendering/frame_compositor.py"),
        Path("emulator/rendering/sprite_renderer.py"),
    ]

    for file_path in core_files:
        assert "import pygame" not in file_path.read_text()
