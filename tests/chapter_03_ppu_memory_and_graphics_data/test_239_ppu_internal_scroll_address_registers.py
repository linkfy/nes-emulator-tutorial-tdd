"""
Introduce the PPU internal scroll/address registers.

Reference:
    https://www.nesdev.org/wiki/PPU_registers#Internal_registers

File to update:
    emulator/ppu/ppu.py

Fields to add:
    vram_addr: int = 0
    temp_vram_addr: int = 0
    fine_x: int = 0
    second_write_toggle: bool = False

Why this step exists:
PPUADDR ($2006), PPUSCROLL ($2005), PPUDATA ($2007), and rendering do not use
only simple one-byte register fields. The PPU has internal address/scroll state.

Common nesdev names:

    v = current VRAM address
    t = temporary VRAM address
    x = fine X scroll
    w = first/second write toggle

Tutorial names:

    vram_addr           -> v
    temp_vram_addr      -> t
    fine_x              -> x
    second_write_toggle -> w

Short meaning:
    - vram_addr is the current PPU memory address used by PPUDATA and rendering.
    - temp_vram_addr is built by PPUADDR/PPUSCROLL writes before being copied.
    - fine_x stores the fine horizontal scroll offset, 0-7. (pixel-level horizontal scroll offset inside a tile)
    - second_write_toggle tracks first vs second write for $2005/$2006.

Suggested implementation pseudocode:

    @dataclass
    class PPU:
        ...
        vram_addr: int = 0
        temp_vram_addr: int = 0
        fine_x: int = 0
        second_write_toggle: bool = False

Out of scope:
    - PPUSCROLL behavior
    - accurate rendering scroll reload timing
    - nametable rendering
"""

from emulator.ppu.ppu import PPU


def test_ppu_has_internal_scroll_address_registers():
    """
    Objective:
    Add the internal PPU state used by PPUADDR, PPUSCROLL, PPUDATA, and future
    rendering.
    """
    assert "vram_addr" in PPU.__dataclass_fields__
    assert "temp_vram_addr" in PPU.__dataclass_fields__
    assert "fine_x" in PPU.__dataclass_fields__
    assert "second_write_toggle" in PPU.__dataclass_fields__


def test_ppu_internal_scroll_address_registers_start_clear():
    """
    Objective:
    Internal PPU scroll/address state should start from a known clear state.
    """
    ppu = PPU()

    assert ppu.vram_addr == 0
    assert ppu.temp_vram_addr == 0
    assert ppu.fine_x == 0
    assert ppu.second_write_toggle is False
