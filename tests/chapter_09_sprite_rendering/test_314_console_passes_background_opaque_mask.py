"""
Wire Console.render_framebuffer() to pass the background opacity mask.

File to update:
    emulator/console.py

Why this step exists:
The sprite renderer can now apply sprite priority bit 5 when it receives a
BackgroundOpaqueMask. Step 313 added the PPU-level helper:

    ppu_background_to_opaque_mask(ppu)

This step connects that helper to the full-frame render path.

Required behavior:

    Console.render_framebuffer()
        -> render background framebuffer
        -> call ppu_background_to_opaque_mask(self.ppu)
        -> build sprite palettes
        -> select sprite pattern table with PPUCTRL bit 3
        -> call composite_background_and_sprites(..., background_opaque_mask=mask)

Example implementation fragment:

    from emulator.rendering.ppu_background_renderer import (
        ppu_background_to_framebuffer,
        # --- ADD THIS NEW IMPORT ---
        ppu_background_to_opaque_mask,
        PATTERN_TABLE_0_ADDR,
        PATTERN_TABLE_1_ADDR,
    )


    def render_framebuffer(self) -> Framebuffer:
        background = self.render_background_framebuffer()

        # --- ADD THIS NEW LINE ---
        background_opaque_mask = ppu_background_to_opaque_mask(self.ppu)

        ...

        return composite_background_and_sprites(
            background=background,
            oam=self.ppu.oam,
            pattern_table=pattern_table,
            sprite_palettes=sprite_palettes,
            # --- ADD THIS NEW LINE ---
            background_opaque_mask=background_opaque_mask,
        )

Important boundary:
Console should orchestrate helpers. It should not duplicate the background
nametable/pattern-table extraction that belongs to ppu_background_renderer.py.

Out of scope:
    - adding another background mask algorithm
    - changing ppu_background_to_opaque_mask()
    - sprite 0 hit
    - sprite overflow
    - pygame
"""

import inspect

from emulator.bus.cpu_bus import CpuBus
from emulator.cartridge.cartridge import Cartridge
from emulator.console import Console
from emulator.cpu.cpu import CPU
from emulator.ppu.ppu import PPU
from emulator.rendering.framebuffer import Framebuffer
from emulator.rendering.nametable_renderer import BackgroundOpaqueMask


def make_minimal_cartridge() -> Cartridge:
    """Create a minimal NROM cartridge for Console construction."""
    header = bytes([
        0x4E, 0x45, 0x53, 0x1A,
        1,
        1,
        0,
        0,
        0, 0, 0, 0, 0, 0, 0, 0,
    ])
    prg_rom = bytes([0xEA] * 0x4000)
    chr_rom = bytes([0x00] * 0x2000)
    return Cartridge.from_ines_bytes(header + prg_rom + chr_rom)


def make_console() -> Console:
    cartridge = make_minimal_cartridge()
    cpu_bus = CpuBus(cartridge=cartridge)
    cpu = CPU(cpu_bus)
    return Console(cpu=cpu, ppu=cpu_bus.ppu)


def test_console_render_framebuffer_calls_background_opaque_mask_helper(monkeypatch):
    """
    Objective:
    Console should obtain the mask through ppu_background_to_opaque_mask(self.ppu),
    not by duplicating PPU background extraction internally.
    """
    import emulator.console as console_module

    console = make_console()
    expected_mask: BackgroundOpaqueMask = [False] * (256 * 240)
    captured = {}

    def fake_ppu_background_to_opaque_mask(ppu: PPU) -> BackgroundOpaqueMask:
        captured["ppu"] = ppu
        return expected_mask

    def fake_composite_background_and_sprites(**kwargs):
        captured["compositor_kwargs"] = kwargs
        return Framebuffer(width=256, height=240)

    monkeypatch.setattr(
        console_module,
        "ppu_background_to_opaque_mask",
        fake_ppu_background_to_opaque_mask,
    )
    monkeypatch.setattr(
        console_module,
        "composite_background_and_sprites",
        fake_composite_background_and_sprites,
    )

    console.render_framebuffer()

    assert captured["ppu"] is console.ppu


def test_console_render_framebuffer_passes_mask_to_compositor(monkeypatch):
    """
    Objective:
    The mask returned by ppu_background_to_opaque_mask should reach the compositor
    unchanged.
    """
    import emulator.console as console_module

    console = make_console()
    expected_mask: BackgroundOpaqueMask = [True, False] * ((256 * 240) // 2)
    captured = {}

    def fake_ppu_background_to_opaque_mask(ppu: PPU) -> BackgroundOpaqueMask:
        return expected_mask

    def fake_composite_background_and_sprites(**kwargs):
        captured.update(kwargs)
        return Framebuffer(width=256, height=240)

    monkeypatch.setattr(
        console_module,
        "ppu_background_to_opaque_mask",
        fake_ppu_background_to_opaque_mask,
    )
    monkeypatch.setattr(
        console_module,
        "composite_background_and_sprites",
        fake_composite_background_and_sprites,
    )

    result = console.render_framebuffer()

    assert isinstance(result, Framebuffer)
    assert captured["background_opaque_mask"] is expected_mask


def test_console_render_framebuffer_still_passes_existing_compositor_inputs(monkeypatch):
    """
    Objective:
    Adding the mask should not remove the existing full-frame composition inputs.
    """
    import emulator.console as console_module

    console = make_console()
    expected_mask: BackgroundOpaqueMask = [False] * (256 * 240)
    captured = {}

    def fake_ppu_background_to_opaque_mask(ppu: PPU) -> BackgroundOpaqueMask:
        return expected_mask

    def fake_composite_background_and_sprites(**kwargs):
        captured.update(kwargs)
        return Framebuffer(width=256, height=240)

    monkeypatch.setattr(
        console_module,
        "ppu_background_to_opaque_mask",
        fake_ppu_background_to_opaque_mask,
    )
    monkeypatch.setattr(
        console_module,
        "composite_background_and_sprites",
        fake_composite_background_and_sprites,
    )

    console.render_framebuffer()

    assert isinstance(captured["background"], Framebuffer)
    assert captured["oam"] is console.ppu.oam
    assert isinstance(captured["pattern_table"], bytes)
    assert len(captured["pattern_table"]) == 0x1000
    assert len(captured["sprite_palettes"]) == 4


def test_console_render_framebuffer_does_not_duplicate_background_extraction_details():
    """
    Objective:
    Console should remain an orchestration layer. Background nametable and
    background pattern-table extraction belongs to ppu_background_renderer.py.
    """
    source = inspect.getsource(Console.render_framebuffer)

    assert "ppu_background_to_opaque_mask(self.ppu)" in source
    assert "BASE_NAMETABLE_ADDR" not in source
    assert "CTRL_BACKGROUND_PATTERN_TABLE" not in source


def test_console_wiring_keeps_pygame_outside_emulator_core():
    """
    Objective:
    Wiring the mask into Console must not introduce frontend dependencies.
    """
    import emulator.console as console_module

    source = inspect.getsource(console_module)

    assert "import pygame" not in source
