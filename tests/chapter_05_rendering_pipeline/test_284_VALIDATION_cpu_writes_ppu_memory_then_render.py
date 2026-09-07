"""
VALIDATION: CPU writes PPU memory, then Console renders background framebuffer.

No new implementation should be required for this test if the previous CPU, PPU,
bus, and rendering steps are complete.

Why this validation exists:
The emulator now has two important paths:

    CPU/PPU write path:
        CPU program writes PPUADDR/PPUDATA
        -> PPU memory changes

    Rendering path:
        Console.render_background_framebuffer()
        -> reads current PPU memory
        -> returns Framebuffer

This test verifies those paths observe the same PPU state.

End-to-end path:

    CPU executes STA $2006/$2007
        -> CpuBus routes $2000-$2007 to PPU registers
        -> PPUADDR selects PPU memory address
        -> PPUDATA writes through PpuBus

    Console.render_background_framebuffer()
        -> reads nametable/palette/pattern memory from console.ppu
        -> renders pure Framebuffer data

Tiny CPU program behavior:

    write $01 to PPU $2000
        nametable[0] = tile ID 1

    write $0F,$01,$02,$03 to PPU $3F00-$3F03
        background palette 0 maps color index 3 to NES color $03

Synthetic CHR setup:
CHR data is prepared directly in PPU memory for this validation. This keeps the
test focused on CPU writes to nametable/palette RAM and the rendering path. For
Mapper000/CHR ROM, CHR graphics normally come from the cartridge.

Expected result:
    top-left framebuffer pixel uses get_nes_rgb_color($03)

Important invariant:
CPU writes and Console rendering must use the same PPU instance.

Out of scope:
    - pygame display
    - real ROM fixture
    - CHR ROM loading through cartridge
    - sprites
    - scrolling
    - OAMDMA
"""

from emulator.bus.cpu_bus import CpuBus
from emulator.console import Console
from emulator.cpu.cpu import CPU
from emulator.memory.fake_rom import FakeROM
from emulator.rendering.nes_palette import get_nes_rgb_color
from emulator.rendering.ppu_background_renderer import PATTERN_TABLE_0_ADDR
from tests.helpers import load_program


def make_console_with_fake_rom():
    """Build a Console whose CPU bus and rendering path share the same PPU."""
    rom = FakeROM()
    bus = CpuBus(program_rom=rom)
    cpu = CPU(bus)
    return Console(cpu=cpu, ppu=bus.ppu), cpu, bus.ppu, rom


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


def test_VALIDATION_cpu_writes_nametable_and_palette_then_console_renders_expected_pixel():
    """
    VALIDATION:
    A CPU program writes nametable and palette RAM through PPU registers, then
    Console renders a framebuffer from the same PPU memory.

    If this fails, inspect earlier systems:
        CpuBus PPU register routing
        PPUADDR/PPUDATA behavior
        PpuBus nametable/palette mapping
        ppu_background_to_framebuffer()
        Console.render_background_framebuffer()
    """
    console, cpu, ppu, rom = make_console_with_fake_rom()

    # Synthetic CHR setup: tile #1 row 0 emits color index 3.
    set_tile_row_to_color_index_in_ppu(
        ppu,
        tile_id=1,
        row=0,
        color_index=3,
    )

    program = [
        # PPUADDR = $2000
        0xA9, 0x20,        # LDA #$20
        0x8D, 0x06, 0x20,  # STA $2006
        0xA9, 0x00,        # LDA #$00
        0x8D, 0x06, 0x20,  # STA $2006

        # PPUDATA = $01, so nametable[0] = tile ID 1
        0xA9, 0x01,        # LDA #$01
        0x8D, 0x07, 0x20,  # STA $2007

        # PPUADDR = $3F00
        0xA9, 0x3F,        # LDA #$3F
        0x8D, 0x06, 0x20,  # STA $2006
        0xA9, 0x00,        # LDA #$00
        0x8D, 0x06, 0x20,  # STA $2006

        # PPUDATA writes background palette 0: $0F,$01,$02,$03
        0xA9, 0x0F,        # LDA #$0F
        0x8D, 0x07, 0x20,  # STA $2007
        0xA9, 0x01,        # LDA #$01
        0x8D, 0x07, 0x20,  # STA $2007
        0xA9, 0x02,        # LDA #$02
        0x8D, 0x07, 0x20,  # STA $2007
        0xA9, 0x03,        # LDA #$03
        0x8D, 0x07, 0x20,  # STA $2007
    ]
    load_program(rom, 0x8000, program)
    cpu.pc = 0x8000

    instruction_count = 18
    for _ in range(instruction_count):
        console.step()

    framebuffer = console.render_background_framebuffer()

    assert framebuffer.get_pixel(0, 0) == get_nes_rgb_color(0x03)
