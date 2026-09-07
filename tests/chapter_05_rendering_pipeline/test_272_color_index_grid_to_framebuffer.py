"""
Convert color-index grids into RGB framebuffer data.

File to create:
    emulator/rendering/color_index_renderer.py

Why this step exists:
Earlier PPU/CHR helpers produce color indexes, not RGB pixels. For example,
decode_chr_tile() produces values like:

    0, 1, 2, 3

Those values are palette indexes. They are not directly displayable colors yet.

This step creates a pure rendering helper that maps:

    color-index grid + RGB palette -> Framebuffer

What is a color-index grid?
A color-index grid is a 2D grid where each number points into a palette.

Minimal example:

    grid = [
        [0, 1, 1, 0, ...],
        [2, 3, 3, 0, ...],
        ...
    ]

    palette = [
        (0, 0, 0),
        (85, 85, 85),
        (170, 170, 170),
        (255, 255, 255),
    ]

Expected framebuffer pixels:

    (x=0, y=0) -> palette[0] -> (0, 0, 0)
    (x=1, y=0) -> palette[1] -> (85, 85, 85)
    (x=0, y=1) -> palette[2] -> (170, 170, 170)
    (x=1, y=1) -> palette[3] -> (255, 255, 255)

Suggested implementation example:

    from emulator.rendering.framebuffer import Framebuffer, RGBColor

    Grid = list[list[int]]


    def color_index_grid_to_framebuffer(
        grid: Grid,
        palette: list[RGBColor],
    ) -> Framebuffer:
        height = len(grid)
        width = len(grid[0])

        framebuffer = Framebuffer(width=width, height=height)

        for y, row in enumerate(grid):
            for x, color_index in enumerate(row):
                framebuffer.set_pixel(x, y, palette[color_index])

        return framebuffer

Important simplification:
For now, assume valid input:

    grid is not empty
    grid is rectangular
    palette contains every used index
    color indexes are valid

Future validations can be added later if this becomes a debugging problem.

Architecture rule:
This helper is pure data transformation. It should not import pygame, CPU, PPU
timing, ROM loading, or frontend code.

Out of scope:
    - NES palette memory lookup
    - rendering CHR tiles directly
    - rendering pattern tables directly
    - rendering nametables/backgrounds
    - pygame display
"""

from pathlib import Path

from emulator.rendering.color_index_renderer import (
    Grid,
    color_index_grid_to_framebuffer,
)
from emulator.rendering.framebuffer import Framebuffer


def test_color_index_renderer_file_exists():
    """
    Objective:
    Keep color-index conversion separate from framebuffer storage.
    """
    assert Path("emulator/rendering/color_index_renderer.py").exists()


def test_color_index_renderer_declares_grid_alias_and_conversion_function():
    """
    Objective:
    Expose a small pure helper for converting indexed color grids to framebuffer
    data.
    """
    assert Grid == list[list[int]]
    assert callable(color_index_grid_to_framebuffer)


def test_color_index_grid_to_framebuffer_sets_output_dimensions_from_grid():
    """
    Objective:
    The framebuffer size should match the input grid dimensions.
    """
    grid = [
        [0, 0, 0],
        [0, 0, 0],
    ]
    palette = [(0, 0, 0)]

    framebuffer = color_index_grid_to_framebuffer(grid, palette)

    assert isinstance(framebuffer, Framebuffer)
    assert framebuffer.width == 3
    assert framebuffer.height == 2
    assert len(framebuffer.pixels) == 6


def test_color_index_grid_to_framebuffer_maps_2x2_indexes_to_rgb_pixels():
    """
    Objective:
    Convert a tiny 2x2 color-index grid into RGB framebuffer pixels.
    """
    grid = [
        [0, 1],
        [2, 3],
    ]
    palette = [
        (0, 0, 0),
        (85, 85, 85),
        (170, 170, 170),
        (255, 255, 255),
    ]

    framebuffer = color_index_grid_to_framebuffer(grid, palette)

    assert framebuffer.get_pixel(0, 0) == (0, 0, 0)
    assert framebuffer.get_pixel(1, 0) == (85, 85, 85)
    assert framebuffer.get_pixel(0, 1) == (170, 170, 170)
    assert framebuffer.get_pixel(1, 1) == (255, 255, 255)


def test_color_index_grid_to_framebuffer_preserves_flat_pixel_order():
    """
    Objective:
    The converted framebuffer should still use Framebuffer's flat row-major pixel
    order.

    Example:
        grid row 0 becomes pixels[0], pixels[1], pixels[2]
        grid row 1 becomes pixels[3], pixels[4], pixels[5]
    """
    grid = [
        [0, 1, 0],
        [1, 0, 1],
    ]
    palette = [
        (10, 10, 10),
        (200, 200, 200),
    ]

    framebuffer = color_index_grid_to_framebuffer(grid, palette)

    assert framebuffer.pixels == [
        (10, 10, 10),
        (200, 200, 200),
        (10, 10, 10),
        (200, 200, 200),
        (10, 10, 10),
        (200, 200, 200),
    ]


def test_color_index_grid_to_framebuffer_checkerboard_example():
    """
    Objective:
    Show a small pattern-like example that future CHR/pattern-table rendering can
    reuse conceptually.
    """
    dark = (0, 0, 0)
    light = (255, 255, 255)
    grid = [
        [0, 1, 0, 1],
        [1, 0, 1, 0],
        [0, 1, 0, 1],
        [1, 0, 1, 0],
    ]
    palette = [dark, light]

    framebuffer = color_index_grid_to_framebuffer(grid, palette)

    assert framebuffer.width == 4
    assert framebuffer.height == 4
    assert framebuffer.get_pixel(0, 0) == dark
    assert framebuffer.get_pixel(1, 0) == light
    assert framebuffer.get_pixel(0, 1) == light
    assert framebuffer.get_pixel(1, 1) == dark
