"""
Expose current background framebuffer data from Console.

File to update:
    emulator/console.py

Why this step exists:
The renderer can now extract a background framebuffer from the current PPU memory:

    ppu_background_to_framebuffer(ppu)

Console is the top-level machine coordinator that owns the CPU/PPU relationship.
Frontend code should eventually be able to ask Console for the current background
framebuffer without knowing the details of PPU memory extraction.

This step adds a small method:

    console.render_background_framebuffer() -> Framebuffer

Important separation:

    Console.step()
        advances emulation time

    Console.render_background_framebuffer()
        observes current PPU memory and returns pure framebuffer data

Do not render inside Console.step(). A real frame contains many CPU instructions;
rendering after every CPU instruction would be wasteful and would mix timing with
observation.

Suggested implementation example:

    from emulator.rendering.framebuffer import Framebuffer
    from emulator.rendering.ppu_background_renderer import ppu_background_to_framebuffer


    class Console:
        ...

        def render_background_framebuffer(self) -> Framebuffer:
            return ppu_background_to_framebuffer(self.ppu)

Architecture rule:
This still returns pure framebuffer data. Do not import pygame here.

Out of scope:
    - pygame display
    - step_until_frame/run_frame
    - sprites
    - OAMDMA
    - controller input
"""

from emulator.bus.cpu_bus import CpuBus
from emulator.console import Console
from emulator.cpu.cpu import CPU
from emulator.memory.fake_rom import FakeROM
from emulator.ppu.chr_decoder import PATTERN_TABLE_SIZE
from emulator.rendering.framebuffer import Framebuffer
from emulator.rendering.nametable_renderer import NAMETABLE_SIZE
from emulator.rendering.nes_palette import get_nes_rgb_color
from emulator.rendering.palette_ram import PALETTE_RAM_SIZE
from emulator.rendering.ppu_background_renderer import (
    BASE_NAMETABLE_ADDR,
    PALETTE_RAM_ADDR,
    PATTERN_TABLE_0_ADDR,
    ppu_background_to_framebuffer,
)


def make_console():
    """
    Build a coherent Console for rendering tests.

    Important:
    Use the PPU already owned by CpuBus so CPU bus access and Console rendering
    observe the same PPU instance.
    """
    bus = CpuBus(program_rom=FakeROM())
    cpu = CPU(bus)
    return Console(cpu=cpu, ppu=bus.ppu)


def write_background_palette_ram(ppu) -> None:
    """Write synthetic background palette RAM bytes to $3F00-$3F0F."""
    palette_ram = bytes([
        0x0F, 0x01, 0x02, 0x03,
        0x04, 0x11, 0x12, 0x13,
        0x08, 0x21, 0x22, 0x23,
        0x0C, 0x31, 0x32, 0x33,
    ])

    assert len(palette_ram) == PALETTE_RAM_SIZE

    for offset, value in enumerate(palette_ram):
        ppu.ppu_bus.write(PALETTE_RAM_ADDR + offset, value)


def set_tile_row_to_color_index_in_ppu(
    ppu,
    tile_id: int,
    row: int,
    color_index: int,
) -> None:
    """Write one synthetic CHR tile row into pattern table 0."""
    tile_offset = tile_id * 16
    low_bit = color_index & 0b01
    high_bit = (color_index >> 1) & 0b01

    ppu.ppu_bus.write(PATTERN_TABLE_0_ADDR + tile_offset + row, 0xFF if low_bit else 0x00)
    ppu.ppu_bus.write(PATTERN_TABLE_0_ADDR + tile_offset + 8 + row, 0xFF if high_bit else 0x00)


def test_console_exposes_render_background_framebuffer_method():
    """
    Objective:
    Console exposes a pure rendering observation method for current background data.
    """
    assert hasattr(Console, "render_background_framebuffer")
    assert callable(Console.render_background_framebuffer)


def test_console_render_background_framebuffer_returns_framebuffer():
    """
    Objective:
    Console.render_background_framebuffer() returns framebuffer data, not pygame or
    frontend-specific objects.
    """
    console = make_console()
    write_background_palette_ram(console.ppu)

    framebuffer = console.render_background_framebuffer()

    assert isinstance(framebuffer, Framebuffer)
    assert framebuffer.width == 256
    assert framebuffer.height == 240


def test_console_render_background_framebuffer_uses_console_ppu_memory():
    """
    Objective:
    Rendering should observe the PPU instance owned by the Console.

    Setup:
        console.ppu nametable $2000 selects tile #1.
        tile #1 row 0 emits color index 3.
        palette RAM maps palette 0 color 3 to NES color $03.
    """
    console = make_console()
    write_background_palette_ram(console.ppu)

    console.ppu.ppu_bus.write(BASE_NAMETABLE_ADDR, 1)
    set_tile_row_to_color_index_in_ppu(
        console.ppu,
        tile_id=1,
        row=0,
        color_index=3,
    )

    framebuffer = console.render_background_framebuffer()

    assert framebuffer.get_pixel(0, 0) == get_nes_rgb_color(0x03)


def test_console_render_background_framebuffer_matches_direct_ppu_renderer_call():
    """
    Objective:
    Console.render_background_framebuffer() is a convenience wrapper around the PPU
    background renderer, not a separate rendering algorithm.
    """
    console = make_console()
    write_background_palette_ram(console.ppu)

    console.ppu.ppu_bus.write(BASE_NAMETABLE_ADDR, 1)
    set_tile_row_to_color_index_in_ppu(
        console.ppu,
        tile_id=1,
        row=0,
        color_index=2,
    )

    via_console = console.render_background_framebuffer()
    direct = ppu_background_to_framebuffer(console.ppu)

    assert via_console.width == direct.width
    assert via_console.height == direct.height
    assert via_console.pixels == direct.pixels


def test_render_background_framebuffer_does_not_step_cpu_or_ppu_timing():
    """
    Objective:
    Rendering is observation. It should not execute CPU instructions or advance PPU
    timing counters.

    Console.step() advances time. render_background_framebuffer() only reads current
    PPU memory and returns a framebuffer.
    """
    console = make_console()
    write_background_palette_ram(console.ppu)

    console.cpu.pc = 0x8000
    console.ppu.cycle = 12
    console.ppu.scanline = 34
    console.ppu.frame = 5

    console.render_background_framebuffer()

    assert console.cpu.pc == 0x8000
    assert console.ppu.cycle == 12
    assert console.ppu.scanline == 34
    assert console.ppu.frame == 5


def test_console_render_background_framebuffer_does_not_require_full_nametable_setup():
    """
    Objective:
    A blank PPU memory state is still renderable because PpuBus provides readable
    backing memory for nametable/palette/pattern data.
    """
    console = make_console()
    write_background_palette_ram(console.ppu)

    framebuffer = console.render_background_framebuffer()

    assert len(framebuffer.pixels) == 256 * 240

    # Keep imports/constants referenced so this test documents the expected memory
    # sizes without directly depending on private renderer internals.
    assert NAMETABLE_SIZE == 960
    assert PATTERN_TABLE_SIZE == 4096
