"""
Integrate the horizontal framebuffer and opacity-mask viewports into Console.

File to update:
    emulator/console.py

Why this step exists:
Steps 334 and 335 produce viewport-aware background data from current PPU scroll
state. This step assembles those new functions inside Console so the full-frame path
uses both the scrolled framebuffer and its matching opacity mask.

What changes:

    Console.render_background_framebuffer()
        -> keeps the older fixed-background behavior

    Console.render_framebuffer()
        -> uses ppu_background_viewport_to_framebuffer(self.ppu)
        -> uses the new viewport opacity mask through a compatibility alias
        -> passes both new results to the existing sprite compositor

Why use an alias for the mask?
Earlier lessons already use the name ppu_background_to_opaque_mask inside Console.
Importing the new viewport-mask function under that name lets the full-frame path use
the new behavior without breaking compatibility with those earlier lessons.

Temporary Super Mario Bros. limitation:
Do not worry if it is not scrolling as expected yet.
This step uses only one scroll position for the whole frame. Super Mario Bros. uses
one position for the fixed status bar and another for the moving gameplay area during
the same frame. The game can therefore still show a stationary background, a moving
status bar, or other incorrect scrolling after this test passes. That is expected.
Future steps will record the scroll changes and render the status bar and gameplay as
separate horizontal bands.

Out of scope:
    - changing sprite-zero-hit scheduling
    - tracing $2005 writes
    - split-screen band rendering
    - vertical pixel scrolling
    - pygame

Complete example implementation:

    # emulator/console.py

    from emulator.rendering.ppu_background_renderer import (
        ppu_background_to_framebuffer,
        # --- NEW LINE: FULL-FRAME RENDERING USES THE VIEWPORT ADAPTER ---
        ppu_background_viewport_to_framebuffer,
        # --- UPDATED LINE: USE THE NEW MASK WITH THE EXISTING CONSOLE NAME ---
        ppu_background_viewport_to_opaque_mask as ppu_background_to_opaque_mask,
        PATTERN_TABLE_0_ADDR,
        PATTERN_TABLE_1_ADDR,
    )

    ...

    def render_background_framebuffer(self) -> Framebuffer:
        # Keep the older background-only behavior for compatibility.
        return ppu_background_to_framebuffer(self.ppu)

    def render_framebuffer(self) -> Framebuffer:
        # --- UPDATED LINE: FULL-FRAME OUTPUT USES THE VIEWPORT FRAMEBUFFER ---
        background = ppu_background_viewport_to_framebuffer(self.ppu)

        # The existing name now refers to the new viewport-mask function.
        background_opaque_mask = ppu_background_to_opaque_mask(self.ppu)

        ...
        # Everything remains the same below this point.
"""

from emulator.bus.cpu_bus import CpuBus
from emulator.console import Console
from emulator.cpu.cpu import CPU
from emulator.memory.fake_rom import FakeROM
from emulator.ppu.ppu import PPU
from emulator.rendering.framebuffer import Framebuffer
from emulator.rendering.nametable_renderer import BackgroundOpaqueMask
from emulator.rendering.ppu_background_renderer import (
    ppu_background_to_framebuffer as one_nametable_to_framebuffer,
    ppu_background_to_opaque_mask as one_nametable_to_opaque_mask,
    ppu_background_viewport_to_framebuffer,
    ppu_background_viewport_to_opaque_mask,
)


def make_console() -> Console:
    """Build a Console whose CPU and renderer observe the same PPU instance."""
    cpu_bus = CpuBus(program_rom=FakeROM())
    cpu = CPU(cpu_bus)
    return Console(cpu=cpu, ppu=cpu_bus.ppu)


def test_console_preserves_fixed_background_api_and_aliases_viewport_mask():
    """
    Objective:
    Keep the old background-only behavior and connect the existing mask name to the
    new viewport-mask behavior.
    """
    import emulator.console as console_module

    assert (
        console_module.ppu_background_to_framebuffer
        is one_nametable_to_framebuffer
    )
    assert (
        console_module.ppu_background_viewport_to_framebuffer
        is ppu_background_viewport_to_framebuffer
    )
    assert (
        console_module.ppu_background_to_opaque_mask
        is ppu_background_viewport_to_opaque_mask
    )


def test_console_passes_matching_viewport_framebuffer_and_mask_to_sprite_compositor(
    monkeypatch,
):
    """
    Objective:
    The displayed background and sprite-priority mask must come from viewport-aware
    adapters and reach the existing compositor unchanged.
    """
    import emulator.console as console_module

    console = make_console()
    expected_background = Framebuffer()
    expected_mask: BackgroundOpaqueMask = [False] * (256 * 240)
    expected_result = Framebuffer()
    captured = {}

    def fake_viewport_framebuffer(ppu: PPU) -> Framebuffer:
        captured["framebuffer_ppu"] = ppu
        return expected_background

    def fake_viewport_mask(ppu: PPU) -> BackgroundOpaqueMask:
        captured["mask_ppu"] = ppu
        return expected_mask

    def fake_compositor(**kwargs):
        captured["compositor"] = kwargs
        return expected_result

    monkeypatch.setattr(
        console_module,
        "ppu_background_viewport_to_framebuffer",
        fake_viewport_framebuffer,
    )
    monkeypatch.setattr(
        console_module,
        "ppu_background_to_opaque_mask",
        fake_viewport_mask,
    )
    monkeypatch.setattr(
        console_module,
        "composite_background_and_sprites",
        fake_compositor,
    )

    result = console.render_framebuffer()

    assert captured["framebuffer_ppu"] is console.ppu
    assert captured["mask_ppu"] is console.ppu
    assert captured["compositor"]["background"] is expected_background
    assert captured["compositor"]["background_opaque_mask"] is expected_mask
    assert captured["compositor"]["oam"] is console.ppu.oam
    assert result is expected_result


def test_renderer_module_keeps_old_one_nametable_functions_distinct():
    """
    Objective:
    Adding Console aliases must not replace the older renderer functions.
    """
    assert one_nametable_to_framebuffer is not ppu_background_viewport_to_framebuffer
    assert one_nametable_to_opaque_mask is not ppu_background_viewport_to_opaque_mask
