"""
Reading PPUSTATUS clears the VBlank flag.

File to update:
    emulator/ppu/ppu.py

Method to update:
    PPU.read_register(addr)

Why this step exists:
PPUSTATUS at $2002 is not a passive value. On real NES hardware, reading
PPUSTATUS returns the current status byte and clears the VBlank-started flag
inside the PPU.

Important behavior:

    read_register($2002):
        1. save the old status value
        2. clear only VBLANK_STARTED, bit 7
        3. return the old status value

The order matters.

Correct:

    value = self.status
    self.status &= ~VBLANK_STARTED
    return value

Incorrect:

    self.status &= ~VBLANK_STARTED
    return self.status

Why incorrect:
The CPU must be able to observe that VBlank was set. If the emulator clears bit
7 before returning, CPU polling loops will miss VBlank.

Bit-level example:

    status before read:      0b1110_0000
    ~VBLANK_STARTED:         0b0111_1111
    status after AND:        0b0110_0000

Only bit 7 clears. Sprite 0 hit and sprite overflow remain set.

Suggested implementation pseudocode:

    def read_register(self, addr: int) -> int:
        match addr:
            case 0x2002:
                value = self.status
                self.status &= ~VBLANK_STARTED
                return value
            case 0x2004:
                return self.oam_data
            case 0x2007:
                return self.data
            case _:
                raise ValueError(...)

Out of scope:
    - automatically setting VBlank from PPU timing
    - NMI generation
    - scanlines/cycles
    - sprite 0 hit behavior
    - sprite overflow behavior
"""

from emulator.ppu.ppu import PPU, SPRITE_OVERFLOW, SPRITE_ZERO_HIT, VBLANK_STARTED


def test_reading_ppu_status_returns_old_value_before_clearing_vblank():
    """
    Objective:
    CPU reads of $2002 should return the old PPUSTATUS value.
    """
    ppu = PPU()
    ppu.status = VBLANK_STARTED

    value = ppu.read_register(0x2002)

    assert value == VBLANK_STARTED


def test_reading_ppu_status_clears_vblank_flag():
    """
    Objective:
    Reading $2002 clears VBLANK_STARTED inside PPU.status.
    """
    ppu = PPU()
    ppu.status = VBLANK_STARTED

    ppu.read_register(0x2002)

    assert ppu.status == 0


def test_reading_ppu_status_preserves_other_status_flags():
    """
    Objective:
    Reading $2002 should clear only VBlank, not every PPUSTATUS flag.

    Why:
    Sprite 0 hit and sprite overflow are independent hardware conditions. They
    are not implemented yet, but if those bits are set, a PPUSTATUS read should
    not erase them.
    """
    ppu = PPU()
    ppu.status = VBLANK_STARTED | SPRITE_ZERO_HIT | SPRITE_OVERFLOW

    value = ppu.read_register(0x2002)

    assert value == VBLANK_STARTED | SPRITE_ZERO_HIT | SPRITE_OVERFLOW
    assert ppu.status == SPRITE_ZERO_HIT | SPRITE_OVERFLOW


def test_reading_ppu_status_when_vblank_is_clear_keeps_status_clear():
    """
    Objective:
    Reading $2002 should be safe even when VBlank was not set.
    """
    ppu = PPU()
    ppu.status = 0

    value = ppu.read_register(0x2002)

    assert value == 0
    assert ppu.status == 0
