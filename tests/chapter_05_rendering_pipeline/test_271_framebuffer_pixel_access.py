"""
Add simple framebuffer pixel access helpers.

File to update:
    emulator/rendering/framebuffer.py

Why this step exists:
The framebuffer now stores a flat list of RGB pixels. Rendering code should not
need to repeat the flat-index formula everywhere, so Framebuffer exposes two tiny
helpers:

    get_pixel(x, y) -> RGBColor
    set_pixel(x, y, color) -> None

What is flat pixel indexing?
Flat indexing stores 2D image coordinates in a 1D list.

Formula:

    index = y * width + x

Minimal example with width = 4:

    (x=0, y=0) -> index 0
    (x=1, y=0) -> index 1
    (x=0, y=1) -> index 4
    (x=2, y=1) -> index 6

Suggested implementation example:

    class Framebuffer:
        ...

        def get_pixel(self, x: int, y: int) -> RGBColor:
            return self.pixels[y * self.width + x]

        def set_pixel(self, x: int, y: int, color: RGBColor) -> None:
            self.pixels[y * self.width + x] = color

Important simplification:
This tutorial step intentionally keeps the helpers small. In the future, we can
add validation for:

    x/y out of bounds
    negative coordinates
    RGB tuple length
    RGB component byte range 0-255

For now, tests use valid coordinates and valid RGB colors only.

Out of scope:
    - coordinate validation
    - RGB validation
    - palette lookup
    - rendering pattern tables
    - rendering nametables
    - pygame display
"""

from emulator.rendering.framebuffer import BLACK, Framebuffer


def test_framebuffer_declares_get_pixel_and_set_pixel_methods():
    """
    Objective:
    Framebuffer exposes simple helpers for reading and writing pixels by x/y.
    """
    assert hasattr(Framebuffer, "get_pixel")
    assert callable(Framebuffer.get_pixel)
    assert hasattr(Framebuffer, "set_pixel")
    assert callable(Framebuffer.set_pixel)


def test_get_pixel_reads_default_blank_pixel():
    """
    Objective:
    get_pixel(x, y) reads from the framebuffer's flat pixel storage.
    """
    framebuffer = Framebuffer(width=4, height=3)

    assert framebuffer.get_pixel(0, 0) == BLACK
    assert framebuffer.get_pixel(3, 2) == BLACK


def test_set_pixel_then_get_pixel_round_trips_color():
    """
    Objective:
    set_pixel(x, y, color) writes a color that get_pixel(x, y) can read back.
    """
    framebuffer = Framebuffer(width=4, height=3)

    framebuffer.set_pixel(2, 1, (255, 0, 0))

    assert framebuffer.get_pixel(2, 1) == (255, 0, 0)


def test_set_pixel_uses_y_times_width_plus_x_flat_index():
    """
    Objective:
    Document the storage layout used by rendering code.

    Example:
        width = 4
        x = 2
        y = 1
        index = 1 * 4 + 2 = 6
    """
    framebuffer = Framebuffer(width=4, height=3)

    framebuffer.set_pixel(2, 1, (0, 255, 0))

    assert framebuffer.pixels[6] == (0, 255, 0)


def test_set_pixel_only_changes_target_pixel_for_valid_coordinates():
    """
    Objective:
    A valid pixel write should not disturb neighboring pixels.
    """
    framebuffer = Framebuffer(width=4, height=3)

    framebuffer.set_pixel(1, 1, (0, 0, 255))

    assert framebuffer.get_pixel(1, 1) == (0, 0, 255)
    assert framebuffer.get_pixel(0, 1) == BLACK
    assert framebuffer.get_pixel(2, 1) == BLACK
