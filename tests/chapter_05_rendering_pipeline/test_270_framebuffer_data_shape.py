"""
Create the pure framebuffer data shape for the rendering pipeline.

Files to create:
    emulator/rendering/
    emulator/rendering/framebuffer.py

Recommended package file:
    emulator/rendering/__init__.py

Why this step exists:
Phase 7 starts by defining the data shape that the emulator core will produce for
visual output. This should be pure Python data, not pygame-specific data.

What is a framebuffer?
A framebuffer is a block of pixel data representing one complete image/frame.

Minimal example:
    A 256x240 NES framebuffer contains:

        256 * 240 = 61440 pixels

Each pixel is represented as an RGB tuple:

        (red, green, blue)

Example:
        BLACK = (0, 0, 0)
        WHITE = (255, 255, 255)

Common misconception:
Framebuffer does not mean pygame window. The framebuffer is core emulator data.
Pygame can later display it, but pygame should not be required to create or test
the framebuffer.

Suggested implementation example:

    from dataclasses import dataclass, field

    RGBColor = tuple[int, int, int]

    NES_SCREEN_WIDTH = 256
    NES_SCREEN_HEIGHT = 240
    BLACK: RGBColor = (0, 0, 0)


    @dataclass
    class Framebuffer:
        width: int = NES_SCREEN_WIDTH
        height: int = NES_SCREEN_HEIGHT
        pixels: list[RGBColor] = field(default_factory=list)

        def __post_init__(self) -> None:
            if not self.pixels:
                self.pixels = [BLACK] * (self.width * self.height)

            if len(self.pixels) != self.width * self.height:
                raise ValueError("Framebuffer pixel count must be equal width * height")

Important invariant:
After construction:

    len(framebuffer.pixels) == framebuffer.width * framebuffer.height

Out of scope:
    - get_pixel/set_pixel methods, tested in the next step
    - coordinate validation
    - RGB component validation
    - converting NES palette indexes to RGB
    - rendering CHR/nametable data
    - pygame/frontend display
"""

from dataclasses import is_dataclass
from pathlib import Path

import pytest

from emulator.rendering.framebuffer import (
    BLACK,
    NES_SCREEN_HEIGHT,
    NES_SCREEN_WIDTH,
    Framebuffer,
)


def test_rendering_folder_and_framebuffer_file_exist():
    """
    Objective:
    Start a rendering module for pure rendering data and transformations.

    Note:
    emulator/rendering/__init__.py is recommended so the folder is an explicit
    Python package, even if modern Python can import namespace packages.
    """
    assert Path("emulator/rendering").exists()
    assert Path("emulator/rendering/framebuffer.py").exists()


def test_framebuffer_constants_define_nes_screen_size_and_black_color():
    """
    Objective:
    Name the standard NES visible framebuffer dimensions and default clear color.
    """
    assert NES_SCREEN_WIDTH == 256
    assert NES_SCREEN_HEIGHT == 240
    assert BLACK == (0, 0, 0)


def test_framebuffer_is_dataclass_with_expected_fields():
    """
    Objective:
    Framebuffer is a small data container with width, height, and flat pixel data.
    """
    assert is_dataclass(Framebuffer)
    assert list(Framebuffer.__dataclass_fields__) == ["width", "height", "pixels"]


def test_framebuffer_default_init_creates_blank_nes_sized_frame():
    """
    Objective:
    Framebuffer() creates a blank 256x240 frame by default.
    """
    framebuffer = Framebuffer()

    assert framebuffer.width == NES_SCREEN_WIDTH
    assert framebuffer.height == NES_SCREEN_HEIGHT
    assert len(framebuffer.pixels) == NES_SCREEN_WIDTH * NES_SCREEN_HEIGHT
    assert framebuffer.pixels[0] == BLACK
    assert framebuffer.pixels[-1] == BLACK


def test_framebuffer_custom_size_initializes_blank_pixels():
    """
    Objective:
    The same data shape can be used for small tests without allocating a full NES
    frame.
    """
    framebuffer = Framebuffer(width=4, height=3)

    assert framebuffer.width == 4
    assert framebuffer.height == 3
    assert framebuffer.pixels == [BLACK] * 12


def test_framebuffer_accepts_existing_pixel_data_when_size_matches():
    """
    Objective:
    Framebuffer can wrap existing pixel data as long as the pixel count matches
    width * height.
    """
    pixels = [
        (255, 0, 0),
        (0, 255, 0),
        (0, 0, 255),
        (255, 255, 255),
    ]

    framebuffer = Framebuffer(width=2, height=2, pixels=pixels)

    assert framebuffer.pixels == pixels


def test_framebuffer_rejects_existing_pixel_data_with_wrong_size():
    """
    Objective:
    Protect the core framebuffer invariant: pixel count must equal width * height.
    """
    with pytest.raises(ValueError, match="Framebuffer pixel count"):
        Framebuffer(width=2, height=2, pixels=[BLACK])
