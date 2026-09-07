"""
Let PPU timing set sprite 0 hit at a previously detected screen position.

File to update:
    emulator/ppu/ppu.py

Why this step exists:
Step 320 can find the first overlapping sprite 0/background pixel and return its
screen position:

    (screen_x, screen_y)

The PPU must not set PPUSTATUS bit 6 immediately when that position is discovered.
It should store the position and set the flag only when emulated PPU timing reaches
the corresponding visible pixel.

Simplified coordinate mapping:

    screen y -> PPU scanline y
    screen x -> PPU cycle x + 1

Visible framebuffer coordinates begin at x=0, while this project's simplified PPU
timing treats visible output as beginning at cycle 1:

    screen x=0 -> PPU cycle 1
    screen x=1 -> PPU cycle 2
    screen x=40 -> PPU cycle 41

Suggested implementation changes:

    # --- NEW LINE ---
    SpriteZeroHitPosition = tuple[int, int]
    # --- END NEW LINE ---


    @dataclass
    class PPU:
        ...
        scanline: int = 0
        frame: int = 0
        nmi_requested: bool = False
        # --- NEW BLOCK ---
        sprite_zero_hit_position: SpriteZeroHitPosition | None = None

        def set_sprite_zero_hit_position(
            self,
            position: SpriteZeroHitPosition | None,
        ) -> None:
            self.sprite_zero_hit_position = position
        # --- END NEW BLOCK ---

        def step(self, cycles: int = 1) -> None:
            ...
            for _ in range(cycles):
                self.cycle += 1

                # --- NEW BLOCK ---
                if self.sprite_zero_hit_position is not None:
                    hit_x, hit_y = self.sprite_zero_hit_position

                    if self.scanline == hit_y and self.cycle == hit_x + 1:
                        self.status |= SPRITE_ZERO_HIT
                        self.sprite_zero_hit_position = None
                # --- END NEW BLOCK ---

                ...

Why consume the position?
The position describes one future timing event. After the event fires, setting it to
None prevents the same scheduled event from firing again in a later frame. The
PPUSTATUS flag itself remains set until Step 319's pre-render clear.

Important distinction:

    set_sprite_zero_hit_position((x, y))
        stores a future position

    PPU.step()
        sets SPRITE_ZERO_HIT when timing reaches that position

Important boundary:
PPU receives only a neutral tuple[int, int] | None. It must not import rendering
modules or know how CHR/background overlap was detected.

Out of scope:
    - Console wiring
    - calling find_sprite_zero_hit_position()
    - selecting sprite/background pattern tables
    - PPUMASK rendering-enable rules
    - x=255 hardware exception
    - OAM Y+1 correction
    - Super Mario Bros. validation
"""

from pathlib import Path

from emulator.ppu.ppu import PPU, SPRITE_ZERO_HIT, SpriteZeroHitPosition


def test_sprite_zero_hit_position_type_alias_has_screen_coordinate_shape():
    """
    Objective:
    PPU timing receives a simple screen-coordinate tuple without depending on the
    rendering package's implementation types.
    """
    position: SpriteZeroHitPosition = (40, 30)

    assert position == (40, 30)


def test_ppu_starts_without_a_scheduled_sprite_zero_hit_position():
    """
    Objective:
    A new PPU should not invent a future sprite 0 hit event.
    """
    ppu = PPU()

    assert ppu.sprite_zero_hit_position is None


def test_set_sprite_zero_hit_position_stores_future_event_without_setting_status():
    """
    Objective:
    Supplying an overlap position schedules a future event; it must not immediately
    set PPUSTATUS bit 6.
    """
    ppu = PPU()

    ppu.set_sprite_zero_hit_position((40, 30))

    assert ppu.sprite_zero_hit_position == (40, 30)
    assert (ppu.status & SPRITE_ZERO_HIT) == 0


def test_setting_none_represents_no_sprite_zero_hit_this_frame():
    """
    Objective:
    The caller can explicitly represent a frame where pure overlap detection found
    no hit.
    """
    ppu = PPU()
    ppu.set_sprite_zero_hit_position((10, 20))

    ppu.set_sprite_zero_hit_position(None)

    assert ppu.sprite_zero_hit_position is None
    assert (ppu.status & SPRITE_ZERO_HIT) == 0


def test_sprite_zero_hit_is_not_set_one_cycle_before_scheduled_pixel():
    """
    Objective:
    An overlap at screen x=3 maps to PPU cycle 4, not cycle 3.
    """
    ppu = PPU()
    ppu.scanline = 20
    ppu.cycle = 2
    ppu.set_sprite_zero_hit_position((3, 20))

    ppu.step(1)

    assert ppu.cycle == 3
    assert (ppu.status & SPRITE_ZERO_HIT) == 0
    assert ppu.sprite_zero_hit_position == (3, 20)


def test_sprite_zero_hit_is_set_at_screen_x_plus_one_cycle():
    """
    Objective:
    When timing reaches the scheduled scanline and x+1 cycle, set PPUSTATUS bit 6.
    """
    ppu = PPU()
    ppu.scanline = 20
    ppu.cycle = 3
    ppu.set_sprite_zero_hit_position((3, 20))

    ppu.step(1)

    assert ppu.scanline == 20
    assert ppu.cycle == 4
    assert (ppu.status & SPRITE_ZERO_HIT) != 0


def test_screen_x_zero_maps_to_ppu_cycle_one():
    """
    Objective:
    Verify the origin conversion explicitly: the first framebuffer pixel maps to
    visible PPU cycle 1.
    """
    ppu = PPU()
    ppu.scanline = 8
    ppu.cycle = 0
    ppu.set_sprite_zero_hit_position((0, 8))

    ppu.step(1)

    assert ppu.cycle == 1
    assert (ppu.status & SPRITE_ZERO_HIT) != 0


def test_matching_cycle_on_wrong_scanline_does_not_set_hit():
    """
    Objective:
    Both timing coordinates must match. Reaching x+1 on a different scanline is not
    the scheduled event.
    """
    ppu = PPU()
    ppu.scanline = 19
    ppu.cycle = 3
    ppu.set_sprite_zero_hit_position((3, 20))

    ppu.step(1)

    assert (ppu.status & SPRITE_ZERO_HIT) == 0
    assert ppu.sprite_zero_hit_position == (3, 20)


def test_sprite_zero_hit_position_is_consumed_after_it_fires():
    """
    Objective:
    One scheduled position represents one timing event and should be removed after
    setting the status flag.
    """
    ppu = PPU()
    ppu.scanline = 20
    ppu.cycle = 3
    ppu.set_sprite_zero_hit_position((3, 20))

    ppu.step(1)

    assert (ppu.status & SPRITE_ZERO_HIT) != 0
    assert ppu.sprite_zero_hit_position is None


def test_consumed_position_does_not_fire_again():
    """
    Objective:
    Consuming the position prevents a stale event from setting the flag in a later
    frame unless the caller schedules a new overlap.
    """
    ppu = PPU()
    ppu.scanline = 20
    ppu.cycle = 3
    ppu.set_sprite_zero_hit_position((3, 20))
    ppu.step(1)
    assert ppu.sprite_zero_hit_position is None

    ppu.status &= ~SPRITE_ZERO_HIT
    ppu.scanline = 20
    ppu.cycle = 3
    ppu.step(1)

    assert (ppu.status & SPRITE_ZERO_HIT) == 0


def test_ppu_does_not_import_rendering_to_schedule_hit_position():
    """
    Objective:
    PPU owns timing and status flags, but overlap detection remains in the pure
    rendering helper. Keep this dependency direction explicit.
    """
    source = Path("emulator/ppu/ppu.py").read_text()

    assert "from emulator.rendering" not in source
    assert "import emulator.rendering" not in source
