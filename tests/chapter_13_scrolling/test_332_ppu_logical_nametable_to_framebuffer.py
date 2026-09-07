"""
Render one selected logical PPU nametable as a framebuffer.

File to update:
    emulator/rendering/ppu_background_renderer.py

Reference:
    https://www.nesdev.org/wiki/PPU_nametables

Why this step exists:
The original helper always rendered logical nametable $2000. Horizontal scrolling
also needs the adjacent logical nametable, so the helper now accepts one of:

    $2000, $2400, $2800, $2C00

Memory layout relative to the selected base:

    base + $000-$3BF: 960 visible tile IDs
    base + $3C0-$3FF: 64 attribute bytes

Compatibility:
Omitting base_nametable_addr must still render $2000. Existing callers therefore do
not need to change.

Mirroring boundary:
Rendering requests logical addresses through PpuBus. PpuBus remains responsible for
mapping those addresses to horizontally or vertically mirrored physical VRAM.

Out of scope:
    - selecting and composing two adjacent framebuffers
    - opacity-mask address selection
    - Console integration
    - vertical viewport composition
    - pygame

Example implementation:

    # emulator/rendering/ppu_background_renderer.py

    # --- NEW LINES: ACCEPTED LOGICAL NAMETABLE BASE ADDRESSES ---
    LOGICAL_NAMETABLE_BASE_ADDRS = (
        0x2000,
        0x2400,
        0x2800,
        0x2C00,
    )


    def ppu_background_to_framebuffer(
        ppu: PPU,
        # --- NEW LINE: OPTIONAL LOGICAL NAMETABLE SELECTION ---
        base_nametable_addr: int = BASE_NAMETABLE_ADDR,
    ) -> Framebuffer:
        # --- NEW BLOCK: REJECT NON-NAMETABLE BASE ADDRESSES ---
        if base_nametable_addr not in LOGICAL_NAMETABLE_BASE_ADDRS:
            raise ValueError(
                "Logical nametable base address must be $2000, $2400, $2800, $2C00"
            )

        nametable_bytes = bytes(
            # --- UPDATED LINE: READ FROM THE SELECTED NAMETABLE ---
            ppu.ppu_bus.read(base_nametable_addr + offset)
            for offset in range(NAMETABLE_SIZE)
        )

        # --- NEW LINE: DERIVE THE SELECTED ATTRIBUTE-TABLE BASE ---
        attribute_table_base = base_nametable_addr + NAMETABLE_SIZE
        attribute_table = bytes(
            # --- UPDATED LINE: READ THE SELECTED ATTRIBUTE TABLE ---
            ppu.ppu_bus.read(attribute_table_base + offset)
            for offset in range(ATTR_TABLE_SIZE)
        )

       ... 
       # Everything remains the same below this point
       
"""

import pytest

from emulator.ppu.ppu import CTRL_BACKGROUND_PATTERN_TABLE, PPU
from emulator.rendering.framebuffer import Framebuffer
from emulator.rendering.nametable_renderer import NAMETABLE_SIZE
import emulator.rendering.ppu_background_renderer as background_renderer
from emulator.rendering.ppu_background_renderer import (
    ATTR_TABLE_SIZE,
    BASE_ATTR_TABLE_ADDR,
    BASE_NAMETABLE_ADDR,
    LOGICAL_NAMETABLE_BASE_ADDRS,
    PALETTE_RAM_ADDR,
    PATTERN_TABLE_1_ADDR,
    ppu_background_to_framebuffer,
)


class RecordingPpuBus:
    """Minimal bus double that records every logical address requested."""

    def __init__(self) -> None:
        self.read_addresses: list[int] = []

    def read(self, addr: int) -> int:
        self.read_addresses.append(addr)
        return addr & 0xFF


def replace_low_level_renderer(monkeypatch):
    """Capture extracted bytes without spending time decoding a full framebuffer."""
    captured: dict[str, bytes] = {}
    expected_framebuffer = Framebuffer()

    def fake_renderer(
        nametable_bytes: bytes,
        attribute_table: bytes,
        pattern_table_bytes: bytes,
        palette_ram: bytes,
    ) -> Framebuffer:
        captured["nametable"] = nametable_bytes
        captured["attributes"] = attribute_table
        captured["pattern_table"] = pattern_table_bytes
        captured["palette_ram"] = palette_ram
        return expected_framebuffer

    monkeypatch.setattr(
        background_renderer,
        "nametable_with_palette_ram_to_framebuffer",
        fake_renderer,
    )
    return captured, expected_framebuffer


@pytest.mark.parametrize("base", LOGICAL_NAMETABLE_BASE_ADDRS)
def test_selected_logical_base_reads_its_tile_and_attribute_ranges(monkeypatch, base):
    """
    Objective:
    Read tile IDs and attributes relative to each selected logical nametable base.
    """
    bus = RecordingPpuBus()
    ppu = PPU(ppu_bus=bus)
    replace_low_level_renderer(monkeypatch)

    ppu_background_to_framebuffer(ppu, base_nametable_addr=base)

    tile_reads = bus.read_addresses[:NAMETABLE_SIZE]
    attribute_start = NAMETABLE_SIZE
    attribute_end = attribute_start + ATTR_TABLE_SIZE
    attribute_reads = bus.read_addresses[attribute_start:attribute_end]

    assert tile_reads == list(range(base, base + NAMETABLE_SIZE))
    assert attribute_reads == list(
        range(base + NAMETABLE_SIZE, base + NAMETABLE_SIZE + ATTR_TABLE_SIZE)
    )


def test_omitted_base_preserves_historical_2000_behavior(monkeypatch):
    """
    Objective:
    Keep every existing one-argument caller compatible with the original helper.
    """
    bus = RecordingPpuBus()
    ppu = PPU(ppu_bus=bus)
    replace_low_level_renderer(monkeypatch)

    ppu_background_to_framebuffer(ppu)

    assert BASE_NAMETABLE_ADDR == 0x2000
    assert BASE_ATTR_TABLE_ADDR == 0x23C0
    assert bus.read_addresses[0] == BASE_NAMETABLE_ADDR
    assert bus.read_addresses[NAMETABLE_SIZE] == BASE_ATTR_TABLE_ADDR


def test_selected_nametable_still_uses_shared_pattern_and_palette_data(monkeypatch):
    """
    Objective:
    Generalizing nametable selection must not change PPUCTRL pattern-table selection
    or the shared palette-RAM address.
    """
    bus = RecordingPpuBus()
    ppu = PPU(ppu_bus=bus)
    ppu.ctrl = CTRL_BACKGROUND_PATTERN_TABLE
    captured, expected_framebuffer = replace_low_level_renderer(monkeypatch)

    result = ppu_background_to_framebuffer(
        ppu,
        base_nametable_addr=0x2400,
    )

    pattern_read_start = NAMETABLE_SIZE + ATTR_TABLE_SIZE
    palette_read_start = pattern_read_start + len(captured["pattern_table"])

    assert bus.read_addresses[pattern_read_start] == PATTERN_TABLE_1_ADDR
    assert bus.read_addresses[palette_read_start] == PALETTE_RAM_ADDR
    assert result is expected_framebuffer


@pytest.mark.parametrize("invalid_base", [0x0000, 0x23C0, 0x3000, 0x3F00])
def test_rejects_addresses_that_are_not_logical_nametable_bases(invalid_base):
    """
    Objective:
    Reject arbitrary addresses before performing partial or misleading bus reads.
    """
    bus = RecordingPpuBus()
    ppu = PPU(ppu_bus=bus)

    with pytest.raises(ValueError, match="Logical nametable base address"):
        ppu_background_to_framebuffer(
            ppu,
            base_nametable_addr=invalid_base,
        )

    assert bus.read_addresses == []


def test_renderer_requests_logical_addresses_and_leaves_mirroring_to_ppu_bus(monkeypatch):
    """
    Objective:
    The renderer must issue the selected logical address range without duplicating
    PpuBus nametable-normalization rules.
    """
    bus = RecordingPpuBus()
    ppu = PPU(ppu_bus=bus)
    replace_low_level_renderer(monkeypatch)

    ppu_background_to_framebuffer(ppu, base_nametable_addr=0x2C00)

    assert bus.read_addresses[0] == 0x2C00
    assert bus.read_addresses[NAMETABLE_SIZE - 1] == 0x2FBF
    assert bus.read_addresses[NAMETABLE_SIZE] == 0x2FC0
    assert bus.read_addresses[NAMETABLE_SIZE + ATTR_TABLE_SIZE - 1] == 0x2FFF
