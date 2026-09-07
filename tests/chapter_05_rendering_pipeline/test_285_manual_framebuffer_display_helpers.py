"""
Add manual framebuffer display helpers using pygame Surface drawing.

File to create:
    tools/show_framebuffer.py

Why this step exists:
The emulator core now produces pure Framebuffer data. Before building a full
frontend, we want a small manual tool that can draw a Framebuffer with pygame for
visual smoke checks.

Important boundary:
This file lives under tools/ because pygame is a frontend/manual-display concern.
Core emulator modules must not import pygame:

    emulator/rendering/framebuffer.py
    emulator/rendering/nametable_renderer.py
    emulator/rendering/ppu_background_renderer.py
    emulator/console.py

What is a pygame Surface?
A Surface is a drawable pixel buffer managed by pygame. A window created by
pygame.display.set_mode(...) is also a Surface.

Minimal example:

    surface.fill((255, 0, 0), pygame.Rect(0, 0, 10, 10))

This fills a 10x10 rectangle with red.

How draw_framebuffer works:

    Framebuffer pixel (x, y)
        -> RGB color
        -> pygame Rect(x * scale, y * scale, scale, scale)
        -> surface.fill(color, rect)

Suggested implementation example:

    import pygame

    from emulator.rendering.framebuffer import Framebuffer


    def make_checkerboard_framebuffer(width: int = 64, height: int = 64) -> Framebuffer:
        framebuffer = Framebuffer(width=width, height=height)

        for y in range(height):
            for x in range(width):
                block_x = x // 8
                block_y = y // 8

                if (block_x + block_y) % 2 == 0:
                    framebuffer.set_pixel(x, y, (255, 255, 255))
                else:
                    framebuffer.set_pixel(x, y, (40, 40, 40))

        return framebuffer


    def draw_framebuffer(
        surface: pygame.Surface,
        framebuffer: Framebuffer,
        scale: int,
    ) -> None:
        for y in range(framebuffer.height):
            for x in range(framebuffer.width):
                color = framebuffer.get_pixel(x, y)

                rect = pygame.Rect(
                    x * scale,
                    y * scale,
                    scale,
                    scale,
                )

                surface.fill(color, rect)

Testing policy:
This test does not open a real pygame window. It uses an off-screen pygame Surface
to verify the drawing helper. The window/main-loop step is separate.

Out of scope:
    - pygame main loop
    - pygame.display.set_mode
    - event handling
    - displaying ROM output
    - controller input
    - sprites
"""

from pathlib import Path

import pygame

from emulator.rendering.framebuffer import Framebuffer
from tools.show_framebuffer import draw_framebuffer, make_checkerboard_framebuffer


def test_manual_show_framebuffer_tool_file_exists():
    """
    Objective:
    Keep pygame display helpers outside emulator core.
    """
    assert Path("tools/show_framebuffer.py").exists()


def test_show_framebuffer_declares_manual_display_helpers():
    """
    Objective:
    The manual tool exposes one helper to create test framebuffer data and one
    helper to draw a framebuffer onto a pygame Surface.
    """
    assert callable(make_checkerboard_framebuffer)
    assert callable(draw_framebuffer)


def test_make_checkerboard_framebuffer_returns_framebuffer_with_requested_size():
    """
    Objective:
    The smoke helper creates pure Framebuffer data before pygame draws anything.
    """
    framebuffer = make_checkerboard_framebuffer(width=16, height=8)

    assert isinstance(framebuffer, Framebuffer)
    assert framebuffer.width == 16
    assert framebuffer.height == 8
    assert len(framebuffer.pixels) == 16 * 8


def test_make_checkerboard_framebuffer_alternates_8_by_8_blocks():
    """
    Objective:
    The synthetic framebuffer should visibly alternate colors in 8x8 blocks.
    """
    framebuffer = make_checkerboard_framebuffer(width=16, height=16)

    assert framebuffer.get_pixel(0, 0) == (255, 255, 255)
    assert framebuffer.get_pixel(7, 7) == (255, 255, 255)
    assert framebuffer.get_pixel(8, 0) == (40, 40, 40)
    assert framebuffer.get_pixel(0, 8) == (40, 40, 40)
    assert framebuffer.get_pixel(8, 8) == (255, 255, 255)


def test_draw_framebuffer_draws_scaled_pixels_to_offscreen_surface():
    """
    Objective:
    draw_framebuffer maps each Framebuffer pixel to a scaled rectangle on a pygame
    Surface.

    This uses an off-screen Surface, not a real display window.
    """
    framebuffer = Framebuffer(width=2, height=2)
    framebuffer.set_pixel(0, 0, (255, 0, 0))
    framebuffer.set_pixel(1, 0, (0, 255, 0))
    framebuffer.set_pixel(0, 1, (0, 0, 255))
    framebuffer.set_pixel(1, 1, (255, 255, 255))

    surface = pygame.Surface((4, 4))

    draw_framebuffer(surface, framebuffer, scale=2)

    assert surface.get_at((0, 0))[:3] == (255, 0, 0)
    assert surface.get_at((2, 0))[:3] == (0, 255, 0)
    assert surface.get_at((0, 2))[:3] == (0, 0, 255)
    assert surface.get_at((2, 2))[:3] == (255, 255, 255)


def test_draw_framebuffer_does_not_modify_source_framebuffer():
    """
    Objective:
    Drawing is a frontend operation. It should not mutate the emulator's pure
    framebuffer data.
    """
    framebuffer = make_checkerboard_framebuffer(width=8, height=8)
    before = list(framebuffer.pixels)
    surface = pygame.Surface((8, 8))

    draw_framebuffer(surface, framebuffer, scale=1)

    assert framebuffer.pixels == before
