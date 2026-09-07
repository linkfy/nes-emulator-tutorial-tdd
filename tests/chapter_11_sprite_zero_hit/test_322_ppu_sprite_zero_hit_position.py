"""
Extract the sprite 0 overlap position from current PPU state.

File to update:
    emulator/rendering/sprite_zero_hit.py

Why this step exists:
The existing pure helper requires explicit rendering data:

    find_sprite_zero_hit_position(
        sprite_zero,
        pattern_table,
        background_opaque_mask,
    )

That API is useful for focused tests, but a future Console step starts with a PPU.
This step adds a small adapter that extracts the required data from current PPU
state and delegates to the existing pure helper.

Keeping both functions in sprite_zero_hit.py is clear at the current project size:

    find_sprite_zero_hit_position(...)
        explicit data -> overlap position

    ppu_sprite_zero_hit_position(ppu)
        PPU state -> explicit data -> overlap position

The second function is an adapter, not another overlap algorithm.

Required extraction:
    - decode OAM entry 0 only
    - build the background opacity mask through ppu_background_to_opaque_mask(ppu)
    - select the sprite pattern table using PPUCTRL bit 3
    - read PATTERN_TABLE_SIZE bytes through PpuBus
    - delegate to find_sprite_zero_hit_position(...)

Suggested implementation example:

    from emulator.ppu.chr_decoder import PATTERN_TABLE_SIZE, decode_chr_tile
    from emulator.ppu.ppu import CTRL_SPRITE_PATTERN_TABLE, PPU
    from emulator.rendering.ppu_background_renderer import (
        PATTERN_TABLE_0_ADDR,
        PATTERN_TABLE_1_ADDR,
        ppu_background_to_opaque_mask,
    )
    from emulator.rendering.sprite_renderer import (
        SpriteEntry,
        decode_sprite_attributes,
        decode_sprite_entry,
    )

    ...

    def ppu_sprite_zero_hit_position(
        ppu: PPU,
    ) -> SpriteZeroHitPosition | None:
        sprite_zero = decode_sprite_entry(
            oam=ppu.oam,
            sprite_index=0,
        )

        background_opaque_mask = ppu_background_to_opaque_mask(ppu)

        sprite_pattern_table_base = (
            PATTERN_TABLE_1_ADDR
            if ppu.ctrl & CTRL_SPRITE_PATTERN_TABLE
            else PATTERN_TABLE_0_ADDR
        )

        sprite_pattern_table = bytes(
            ppu.ppu_bus.read(sprite_pattern_table_base + offset)
            for offset in range(PATTERN_TABLE_SIZE)
        )

        return find_sprite_zero_hit_position(
            sprite_zero=sprite_zero,
            pattern_table=sprite_pattern_table,
            background_opaque_mask=background_opaque_mask,
        )

Important distinction:
Background opacity uses the background pattern-table selection path, which is based
on PPUCTRL bit 4. Sprite 0 CHR data uses PPUCTRL bit 3. The two selections may point
to different pattern tables.

Important boundary:
This function only returns a position. It does not set PPUSTATUS and does not call
PPU.set_sprite_zero_hit_position(). Console wiring remains a later step.

Out of scope:
    - Console wiring
    - automatic scheduling
    - PPUMASK rendering-enable rules
    - left-edge clipping rules
    - x=255 hardware exception
    - OAM Y+1 correction
    - Super Mario Bros. validation
"""

from emulator.ppu.chr_decoder import PATTERN_TABLE_SIZE
from emulator.ppu.ppu import CTRL_SPRITE_PATTERN_TABLE, PPU, SPRITE_ZERO_HIT
from emulator.rendering.ppu_background_renderer import (
    PATTERN_TABLE_0_ADDR,
    PATTERN_TABLE_1_ADDR,
)
from emulator.rendering.sprite_zero_hit import (
    find_sprite_zero_hit_position,
    ppu_sprite_zero_hit_position,
)
import emulator.rendering.sprite_zero_hit as sprite_zero_hit_module


def make_background_mask() -> list[bool]:
    return [False] * (256 * 240)


def test_ppu_adapter_and_pure_overlap_helper_live_in_same_focused_module():
    """
    Objective:
    Keep the two abstraction levels together while the sprite-zero-hit module remains
    small and cohesive.
    """
    assert callable(find_sprite_zero_hit_position)
    assert callable(ppu_sprite_zero_hit_position)
    assert find_sprite_zero_hit_position.__module__ == ppu_sprite_zero_hit_position.__module__


def test_ppu_sprite_zero_hit_position_decodes_only_oam_entry_zero(monkeypatch):
    """
    Objective:
    Sprite 0 hit uses the first four OAM bytes. Other sprites must not be substituted
    for OAM entry 0.
    """
    ppu = PPU()
    ppu.oam[0:4] = bytes([12, 7, 0x60, 34])
    ppu.oam[4:8] = bytes([99, 8, 0x00, 88])
    captured = {}

    monkeypatch.setattr(
        sprite_zero_hit_module,
        "ppu_background_to_opaque_mask",
        lambda received_ppu: make_background_mask(),
    )

    def fake_find_sprite_zero_hit_position(**kwargs):
        captured.update(kwargs)
        return None

    monkeypatch.setattr(
        sprite_zero_hit_module,
        "find_sprite_zero_hit_position",
        fake_find_sprite_zero_hit_position,
    )

    ppu_sprite_zero_hit_position(ppu)

    sprite_zero = captured["sprite_zero"]
    assert sprite_zero.y == 12
    assert sprite_zero.tile_index == 7
    assert sprite_zero.attributes == 0x60
    assert sprite_zero.x == 34


def test_ppu_adapter_passes_background_mask_to_pure_helper_unchanged(monkeypatch):
    """
    Objective:
    Background extraction belongs to ppu_background_to_opaque_mask(). The adapter
    should pass its result directly to the pure overlap helper.
    """
    ppu = PPU()
    expected_mask = make_background_mask()
    expected_mask[123] = True
    captured = {}

    def fake_background_mask(received_ppu):
        assert received_ppu is ppu
        return expected_mask

    def fake_find_sprite_zero_hit_position(**kwargs):
        captured.update(kwargs)
        return None

    monkeypatch.setattr(
        sprite_zero_hit_module,
        "ppu_background_to_opaque_mask",
        fake_background_mask,
    )
    monkeypatch.setattr(
        sprite_zero_hit_module,
        "find_sprite_zero_hit_position",
        fake_find_sprite_zero_hit_position,
    )

    ppu_sprite_zero_hit_position(ppu)

    assert captured["background_opaque_mask"] is expected_mask


def test_ppu_adapter_uses_sprite_pattern_table_zero_when_ctrl_bit_is_clear(monkeypatch):
    """
    Objective:
    PPUCTRL bit 3 clear selects sprite pattern table $0000-$0FFF.
    """
    ppu = PPU()
    assert (ppu.ctrl & CTRL_SPRITE_PATTERN_TABLE) == 0
    ppu.ppu_bus.write(PATTERN_TABLE_0_ADDR, 0x11)
    ppu.ppu_bus.write(PATTERN_TABLE_1_ADDR, 0x22)
    captured = {}

    monkeypatch.setattr(
        sprite_zero_hit_module,
        "ppu_background_to_opaque_mask",
        lambda received_ppu: make_background_mask(),
    )

    def fake_find_sprite_zero_hit_position(**kwargs):
        captured.update(kwargs)
        return None

    monkeypatch.setattr(
        sprite_zero_hit_module,
        "find_sprite_zero_hit_position",
        fake_find_sprite_zero_hit_position,
    )

    ppu_sprite_zero_hit_position(ppu)

    pattern_table = captured["pattern_table"]
    assert isinstance(pattern_table, bytes)
    assert len(pattern_table) == PATTERN_TABLE_SIZE
    assert pattern_table[0] == 0x11


def test_ppu_adapter_uses_sprite_pattern_table_one_when_ctrl_bit_is_set(monkeypatch):
    """
    Objective:
    PPUCTRL bit 3 set selects sprite pattern table $1000-$1FFF.
    """
    ppu = PPU()
    ppu.ctrl |= CTRL_SPRITE_PATTERN_TABLE
    ppu.ppu_bus.write(PATTERN_TABLE_0_ADDR, 0x11)
    ppu.ppu_bus.write(PATTERN_TABLE_1_ADDR, 0x22)
    captured = {}

    monkeypatch.setattr(
        sprite_zero_hit_module,
        "ppu_background_to_opaque_mask",
        lambda received_ppu: make_background_mask(),
    )

    def fake_find_sprite_zero_hit_position(**kwargs):
        captured.update(kwargs)
        return None

    monkeypatch.setattr(
        sprite_zero_hit_module,
        "find_sprite_zero_hit_position",
        fake_find_sprite_zero_hit_position,
    )

    ppu_sprite_zero_hit_position(ppu)

    pattern_table = captured["pattern_table"]
    assert isinstance(pattern_table, bytes)
    assert len(pattern_table) == PATTERN_TABLE_SIZE
    assert pattern_table[0] == 0x22


def test_ppu_adapter_returns_pure_helper_result_unchanged(monkeypatch):
    """
    Objective:
    This adapter should not reinterpret or offset the position returned by the pure
    overlap helper.
    """
    ppu = PPU()
    expected_position = (45, 67)

    monkeypatch.setattr(
        sprite_zero_hit_module,
        "ppu_background_to_opaque_mask",
        lambda received_ppu: make_background_mask(),
    )
    monkeypatch.setattr(
        sprite_zero_hit_module,
        "find_sprite_zero_hit_position",
        lambda **kwargs: expected_position,
    )

    result = ppu_sprite_zero_hit_position(ppu)

    assert result is expected_position


def test_ppu_adapter_does_not_set_status_or_schedule_position(monkeypatch):
    """
    Objective:
    Step 322 only extracts and returns a position. PPU mutation belongs to the next
    Console orchestration step.
    """
    ppu = PPU()
    expected_position = (10, 20)

    monkeypatch.setattr(
        sprite_zero_hit_module,
        "ppu_background_to_opaque_mask",
        lambda received_ppu: make_background_mask(),
    )
    monkeypatch.setattr(
        sprite_zero_hit_module,
        "find_sprite_zero_hit_position",
        lambda **kwargs: expected_position,
    )

    result = ppu_sprite_zero_hit_position(ppu)

    assert result == expected_position
    assert (ppu.status & SPRITE_ZERO_HIT) == 0
    assert ppu.sprite_zero_hit_position is None
