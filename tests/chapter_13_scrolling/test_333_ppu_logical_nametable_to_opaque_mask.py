"""
Build an opacity mask from one selected logical PPU nametable.

File to update:
    emulator/rendering/ppu_background_renderer.py

Reference:
    https://www.nesdev.org/wiki/PPU_nametables

Why this step exists:
The existing helper builds the mask used by sprite priority and sprite-zero-hit
detection, but originally reads only logical nametable $2000. Horizontal scrolling
also needs the mask belonging to the adjacent logical nametable.

Compatibility:
Omitting base_nametable_addr still selects $2000, so existing Console and sprite-zero
hit callers remain valid until viewport integration is performed deliberately.

Opacity inputs:
    - 960 tile IDs from the selected logical nametable
    - the background pattern table selected by PPUCTRL bit 4

Opacity does not use attribute bytes, palette RAM, or final RGB colors.

Out of scope:
    - composing the left and right masks
    - framebuffer rendering
    - Console integration
    - sprite-zero-hit viewport integration
    - vertical scrolling

Complete example implementation:

    # emulator/rendering/ppu_background_renderer.py

    def ppu_background_to_opaque_mask(
        ppu: PPU,
        # --- NEW LINE: OPTIONAL LOGICAL NAMETABLE SELECTION ---
        base_nametable_addr: int = BASE_NAMETABLE_ADDR,
    ) -> BackgroundOpaqueMask:
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

        ...
        # Everything remains the same below this point.
"""

import pytest

from emulator.ppu.ppu import CTRL_BACKGROUND_PATTERN_TABLE, PPU
from emulator.rendering.nametable_renderer import BackgroundOpaqueMask, NAMETABLE_SIZE
import emulator.rendering.ppu_background_renderer as background_renderer
from emulator.rendering.ppu_background_renderer import (
    BASE_NAMETABLE_ADDR,
    LOGICAL_NAMETABLE_BASE_ADDRS,
    PATTERN_TABLE_0_ADDR,
    PATTERN_TABLE_1_ADDR,
    ppu_background_to_opaque_mask,
)


class RecordingPpuBus:
    """Minimal bus double that records each logical read request."""

    def __init__(self) -> None:
        self.read_addresses: list[int] = []

    def read(self, addr: int) -> int:
        self.read_addresses.append(addr)
        return addr & 0xFF


def replace_mask_builder(monkeypatch):
    """Capture extracted bytes while keeping this test focused on PPU adaptation."""
    captured: dict[str, bytes] = {}
    expected_mask: BackgroundOpaqueMask = [False, True]

    def fake_builder(
        pattern_table: bytes,
        nametable: bytes,
    ) -> BackgroundOpaqueMask:
        captured["pattern_table"] = pattern_table
        captured["nametable"] = nametable
        return expected_mask

    monkeypatch.setattr(
        background_renderer,
        "build_background_opaque_mask",
        fake_builder,
    )
    return captured, expected_mask


@pytest.mark.parametrize("base", LOGICAL_NAMETABLE_BASE_ADDRS)
def test_selected_logical_base_reads_its_visible_tile_range(monkeypatch, base):
    """
    Objective:
    Read all 960 tile IDs relative to each accepted logical nametable base.
    """
    bus = RecordingPpuBus()
    ppu = PPU(ppu_bus=bus)
    replace_mask_builder(monkeypatch)

    ppu_background_to_opaque_mask(ppu, base_nametable_addr=base)

    assert bus.read_addresses[:NAMETABLE_SIZE] == list(
        range(base, base + NAMETABLE_SIZE)
    )


def test_omitted_base_preserves_historical_2000_behavior(monkeypatch):
    """
    Objective:
    Keep existing one-argument Console and sprite-zero-hit callers compatible.
    """
    bus = RecordingPpuBus()
    ppu = PPU(ppu_bus=bus)
    replace_mask_builder(monkeypatch)

    ppu_background_to_opaque_mask(ppu)

    assert bus.read_addresses[0] == BASE_NAMETABLE_ADDR


@pytest.mark.parametrize(
    ("ctrl", "expected_pattern_base"),
    [
        (0, PATTERN_TABLE_0_ADDR),
        (CTRL_BACKGROUND_PATTERN_TABLE, PATTERN_TABLE_1_ADDR),
    ],
)
def test_selected_nametable_preserves_ppuctrl_pattern_table_selection(
    monkeypatch,
    ctrl,
    expected_pattern_base,
):
    """
    Objective:
    Nametable selection and background pattern-table selection remain independent.
    """
    bus = RecordingPpuBus()
    ppu = PPU(ppu_bus=bus)
    ppu.ctrl = ctrl
    captured, expected_mask = replace_mask_builder(monkeypatch)

    result = ppu_background_to_opaque_mask(
        ppu,
        base_nametable_addr=0x2400,
    )

    assert bus.read_addresses[NAMETABLE_SIZE] == expected_pattern_base
    assert len(captured["nametable"]) == NAMETABLE_SIZE
    assert result is expected_mask


def test_mask_extraction_does_not_read_attributes_or_palette_ram(monkeypatch):
    """
    Objective:
    Keep opacity based only on tile IDs and CHR color indexes.

    After 960 nametable reads, every remaining read must belong to the selected
    4096-byte pattern table.
    """
    bus = RecordingPpuBus()
    ppu = PPU(ppu_bus=bus)
    replace_mask_builder(monkeypatch)

    ppu_background_to_opaque_mask(ppu, base_nametable_addr=0x2400)

    pattern_reads = bus.read_addresses[NAMETABLE_SIZE:]

    assert pattern_reads == list(range(0x0000, 0x1000))


@pytest.mark.parametrize("invalid_base", [0x0000, 0x23C0, 0x3000, 0x3F00])
def test_rejects_addresses_that_are_not_logical_nametable_bases(invalid_base):
    """
    Objective:
    Reject invalid input before performing partial PPU memory reads.
    """
    bus = RecordingPpuBus()
    ppu = PPU(ppu_bus=bus)

    with pytest.raises(ValueError, match="Logical nametable base address"):
        ppu_background_to_opaque_mask(
            ppu,
            base_nametable_addr=invalid_base,
        )

    assert bus.read_addresses == []
