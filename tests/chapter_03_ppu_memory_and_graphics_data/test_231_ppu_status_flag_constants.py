"""
Define PPUSTATUS flag constants.

File to update:
    emulator/ppu/ppu.py

Constants to add:
    VBLANK_STARTED      (Will be used in next test)
    SPRITE_ZERO_HIT     (Will be used later...)
    SPRITE_OVERFLOW     (Will be used later...)

Why this step exists:
PPUSTATUS is the CPU-readable PPU status register at $2002. It is one byte, and
its important hardware status flags live in the high bits:

    bit:  7 6 5 4 3 2 1 0
          V S O - - - - -

Meaning:
    V = VBlank started
    S = Sprite 0 hit
    O = Sprite overflow

Why constants:
Magic numbers such as 0x80, 0x40, and 0x20 work mechanically, but they hide the
hardware meaning. Named constants make later PPU behavior easier to read:

    self.status &= ~VBLANK_STARTED

is clearer than:

    self.status &= ~0x80

Important scope:
This step only names the status bits. It does not implement sprite 0 hit or
sprite overflow behavior yet. Those require rendering, sprite evaluation, OAM,
and scanline timing.

Suggested implementation pseudocode:

    VBLANK_STARTED = 1 << 7
    SPRITE_ZERO_HIT = 1 << 6
    SPRITE_OVERFLOW = 1 << 5

Why `1 << 7`:
Shifting 1 left by 7 positions creates a byte with only bit 7 set:

    1 << 7 == 0b1000_0000 == 0x80
"""

from emulator.ppu.ppu import SPRITE_OVERFLOW, SPRITE_ZERO_HIT, VBLANK_STARTED


def test_ppu_status_flag_constants_match_status_bit_layout():
    """
    Objective:
    Name the meaningful high bits of PPUSTATUS.
    """
    assert VBLANK_STARTED == 1 << 7
    assert SPRITE_ZERO_HIT == 1 << 6
    assert SPRITE_OVERFLOW == 1 << 5


def test_ppu_status_flag_constants_can_be_combined_as_bit_flags():
    """
    Objective:
    PPUSTATUS flags should behave like normal bit flags inside one byte.

    Why:
    Hardware status registers usually pack multiple boolean conditions into a
    single byte. The emulator should preserve that mental model.
    """
    status = VBLANK_STARTED | SPRITE_ZERO_HIT | SPRITE_OVERFLOW

    assert status == 0b1110_0000
