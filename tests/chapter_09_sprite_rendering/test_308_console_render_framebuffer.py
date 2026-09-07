"""
Expose a full background+sprites framebuffer from Console.

File to update:
    emulator/console.py

Why this step exists:
Frontends should not know how to extract background memory, sprite OAM, sprite
palette RAM, or sprite pattern tables separately. Console coordinates CPU/PPU
systems, so it should expose one frontend-facing method:

    console.render_framebuffer()

This method returns the current visible framebuffer using:

    background renderer
    PPU.oam sprites
    sprite palette RAM $3F10-$3F1F
    sprite pattern table selected by PPUCTRL bit 3

Suggested implementation example:

    def render_framebuffer(self) -> Framebuffer:
        background = self.render_background_framebuffer()

        sprite_palette_start = PALETTE_START + 16
        sprite_palette_ram = bytes(
            self.ppu.ppu_bus.read(sprite_palette_start + offset)
            for offset in range(16)
        )
        sprite_palettes = build_sprite_palettes_from_palette_ram(sprite_palette_ram)

        pattern_table_base = (
            PATTERN_TABLE_1_ADDR
            if self.ppu.ctrl & CTRL_SPRITE_PATTERN_TABLE
            else PATTERN_TABLE_0_ADDR
        )

        pattern_table = bytes(
            self.ppu.ppu_bus.read(pattern_table_base + offset)
            for offset in range(0x1000)
        )

        return composite_background_and_sprites(
            background=background,
            oam=self.ppu.oam,
            pattern_table=pattern_table,
            sprite_palettes=sprite_palettes,
        )

Important boundary:
Console may call pure rendering helpers. Console must not import pygame.

Out of scope:
    - sprite 0 hit
    - sprite overflow
    - 8x16 sprites
    - sprite/background priority bit behavior
    - pygame display
"""

from pathlib import Path

from emulator.bus.cpu_bus import CpuBus
from emulator.console import Console
from emulator.cpu.cpu import CPU
from emulator.ppu.ppu import CTRL_SPRITE_PATTERN_TABLE
from emulator.rendering.framebuffer import BLACK, Framebuffer
from emulator.rendering.nes_palette import get_nes_rgb_color
from emulator.rendering.ppu_background_renderer import (
    PATTERN_TABLE_0_ADDR,
    PATTERN_TABLE_1_ADDR,
)
from tests.chapter_09_sprite_rendering.test_304_render_one_sprite_8x8 import encode_chr_tile


def make_console() -> Console:
    """Create a Console with FakeROM-backed CpuBus defaults."""
    bus = CpuBus()
    cpu = CPU(bus)
    return Console(cpu=cpu, ppu=bus.ppu)


def write_ppu_bytes(console: Console, start_addr: int, data: bytes) -> None:
    """Write bytes directly through PpuBus public behavior for synthetic setup."""
    for offset, value in enumerate(data):
        console.ppu.ppu_bus.write(start_addr + offset, value)


def write_oam_sprite(
    console: Console,
    sprite_index: int,
    *,
    y: int,
    tile_index: int,
    attributes: int,
    x: int,
) -> None:
    """Write one raw OAM sprite entry."""
    base = sprite_index * 4
    console.ppu.oam[base + 0] = y
    console.ppu.oam[base + 1] = tile_index
    console.ppu.oam[base + 2] = attributes
    console.ppu.oam[base + 3] = x


def make_single_pixel_tile(color_index: int) -> bytes:
    """Create one CHR tile with a visible pixel at tile coordinate (0, 0)."""
    return encode_chr_tile(
        [[color_index if x == 0 and y == 0 else 0 for x in range(8)] for y in range(8)]
    )


def setup_sprite_palette_ram(console: Console) -> None:
    """
    Set sprite palette RAM bytes $3F10-$3F1F.

    Palette 0 indexes:
        color index 1 -> NES color $01
        color index 2 -> NES color $02
        color index 3 -> NES color $03

    Palette 1 indexes:
        color index 1 -> NES color $11
        color index 2 -> NES color $12
        color index 3 -> NES color $13
    """
    write_ppu_bytes(
        console,
        0x3F10,
        bytes(
            [
                0x00, 0x01, 0x02, 0x03,
                0x10, 0x11, 0x12, 0x13,
                0x20, 0x21, 0x22, 0x23,
                0x30, 0x31, 0x32, 0x33,
            ]
        ),
    )


def test_console_exposes_render_framebuffer_method():
    """
    Objective:
    Console exposes a frontend-facing full-frame render helper while keeping the
    existing background-only helper.
    """
    assert hasattr(Console, "render_framebuffer")
    assert callable(Console.render_framebuffer)
    assert hasattr(Console, "render_background_framebuffer")


def test_console_render_framebuffer_returns_framebuffer():
    """
    Objective:
    render_framebuffer() returns pure Framebuffer data, not pygame objects.
    """
    console = make_console()
    setup_sprite_palette_ram(console)

    framebuffer = console.render_framebuffer()

    assert isinstance(framebuffer, Framebuffer)
    assert framebuffer.width == 256
    assert framebuffer.height == 240


def test_console_render_framebuffer_preserves_background_when_no_sprite_draws():
    """
    Objective:
    If OAM sprites are offscreen/transparent, the full framebuffer still contains
    the background framebuffer content.
    """
    console = make_console()
    setup_sprite_palette_ram(console)

    background = console.render_background_framebuffer()
    final = console.render_framebuffer()

    assert final.get_pixel(0, 0) == background.get_pixel(0, 0)


def test_console_render_framebuffer_overlays_sprite_pixels_from_ppu_oam():
    """
    Objective:
    render_framebuffer() uses PPU.oam sprite data and overlays non-transparent
    sprite pixels onto the background copy.
    """
    console = make_console()
    setup_sprite_palette_ram(console)
    write_ppu_bytes(console, PATTERN_TABLE_0_ADDR, make_single_pixel_tile(1))
    write_oam_sprite(console, 0, y=4, tile_index=0, attributes=0, x=5)

    final = console.render_framebuffer()

    assert final.get_pixel(5, 4) == get_nes_rgb_color(0x01)


def test_console_render_framebuffer_uses_sprite_palette_ram_3f10_to_3f1f():
    """
    Objective:
    Sprite colors should come from sprite palette RAM, not background palette RAM.
    """
    console = make_console()

    # Background palette bytes intentionally differ from sprite palette bytes.
    write_ppu_bytes(console, 0x3F00, bytes([0x0F] * 16))
    setup_sprite_palette_ram(console)

    write_ppu_bytes(console, PATTERN_TABLE_0_ADDR, make_single_pixel_tile(2))
    write_oam_sprite(console, 0, y=0, tile_index=0, attributes=0, x=0)

    final = console.render_framebuffer()

    assert final.get_pixel(0, 0) == get_nes_rgb_color(0x02)
    assert final.get_pixel(0, 0) != get_nes_rgb_color(0x0F)


def test_console_render_framebuffer_uses_sprite_palette_id_from_oam_attributes():
    """
    Objective:
    OAM attribute bits 0-1 select which sprite palette render_framebuffer() uses.
    """
    console = make_console()
    setup_sprite_palette_ram(console)
    write_ppu_bytes(console, PATTERN_TABLE_0_ADDR, make_single_pixel_tile(3))

    # attributes=1 selects sprite palette 1, whose color index 3 is NES color $13.
    write_oam_sprite(console, 0, y=0, tile_index=0, attributes=0b0000_0001, x=0)

    final = console.render_framebuffer()

    assert final.get_pixel(0, 0) == get_nes_rgb_color(0x13)


def test_console_render_framebuffer_uses_sprite_pattern_table_zero_by_default():
    """
    Objective:
    When PPUCTRL bit 3 is clear, 8x8 sprites use pattern table $0000.
    """
    console = make_console()
    setup_sprite_palette_ram(console)
    console.ppu.ctrl &= ~CTRL_SPRITE_PATTERN_TABLE

    write_ppu_bytes(console, PATTERN_TABLE_0_ADDR, make_single_pixel_tile(1))
    write_ppu_bytes(console, PATTERN_TABLE_1_ADDR, make_single_pixel_tile(2))
    write_oam_sprite(console, 0, y=0, tile_index=0, attributes=0, x=0)

    final = console.render_framebuffer()

    assert final.get_pixel(0, 0) == get_nes_rgb_color(0x01)


def test_console_render_framebuffer_uses_sprite_pattern_table_one_when_ctrl_bit_3_set():
    """
    Objective:
    When PPUCTRL bit 3 is set, 8x8 sprites use pattern table $1000.
    """
    console = make_console()
    setup_sprite_palette_ram(console)
    console.ppu.ctrl |= CTRL_SPRITE_PATTERN_TABLE

    write_ppu_bytes(console, PATTERN_TABLE_0_ADDR, make_single_pixel_tile(1))
    write_ppu_bytes(console, PATTERN_TABLE_1_ADDR, make_single_pixel_tile(2))
    write_oam_sprite(console, 0, y=0, tile_index=0, attributes=0, x=0)

    final = console.render_framebuffer()

    assert final.get_pixel(0, 0) == get_nes_rgb_color(0x02)


def test_console_render_framebuffer_keeps_background_only_helper_available():
    """
    Objective:
    Debug/manual callers can still ask for background-only output.
    """
    console = make_console()

    background = console.render_background_framebuffer()
    final = console.render_framebuffer()

    assert isinstance(background, Framebuffer)
    assert isinstance(final, Framebuffer)


def test_console_render_framebuffer_does_not_import_pygame_or_set_sprite_flags():
    """
    Objective:
    Console may coordinate pure render helpers, but pygame and sprite timing flags
    remain out of scope.
    """
    source = Path("emulator/console.py").read_text()

    assert "import pygame" not in source
    assert "SPRITE_ZERO_HIT" not in source
    assert "SPRITE_OVERFLOW" not in source
