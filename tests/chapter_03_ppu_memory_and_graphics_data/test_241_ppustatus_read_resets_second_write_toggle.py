"""
Reading PPUSTATUS ($2002) resets the PPU second-write toggle.

File to update:
    emulator/ppu/ppu.py

Method to update:
    PPU.read_register(addr)

Why this step exists:
The NES PPU has two-write registers, especially:

    $2005 PPUSCROLL
    $2006 PPUADDR

Those registers use an internal first-write / second-write toggle. In this
tutorial, that state is named:

    second_write_toggle

Meaning:

    False -> the next two-write register access is the first write
    True  -> the next two-write register access is the second write

Important PPUSTATUS behavior:
Reading $2002 resets this toggle back to False.

Why:
Games commonly read PPUSTATUS before writing PPUSCROLL or PPUADDR so the PPU is
known to be waiting for the first write again.

Example:

    write $23 to $2006
        second_write_toggle = True

    read $2002
        second_write_toggle = False

    write $20 to $2006
        treated as first write / high byte, not as low byte

Suggested implementation pseudocode:

    def read_register(self, addr: int) -> int:
        match addr:
            case 0x2002:
                value = self.status
                self.status &= ~VBLANK_STARTED
                self.second_write_toggle = False
                return value

            case 0x2004:
                return self.oam_data

            case 0x2007:
                return self.data

            case _:
                raise ValueError(...)

Important invariant:
Reading $2002 should return the old status value, then apply side effects.

Side effects currently modeled:
    - clear VBLANK_STARTED
    - reset second_write_toggle

Side effects not modeled yet:
    - full scroll latch behavior
    - timing/VBlank generation
    - NMI behavior
"""

from emulator.ppu.ppu import PPU, VBLANK_STARTED


def test_reading_ppustatus_resets_second_write_toggle():
    """
    Objective:
    Reading $2002 should make the next $2006 write behave like a first write.
    """
    ppu = PPU()
    ppu.write_register(0x2006, 0x23)

    assert ppu.second_write_toggle is True

    ppu.read_register(0x2002)

    assert ppu.second_write_toggle is False


def test_reading_ppustatus_still_returns_old_status_value():
    """
    Objective:
    Resetting the write toggle must not change the rule that $2002 returns the
    old status value.
    """
    ppu = PPU()
    ppu.status = VBLANK_STARTED
    ppu.write_register(0x2006, 0x23)

    value = ppu.read_register(0x2002)

    assert value == VBLANK_STARTED


def test_reading_ppustatus_still_clears_vblank():
    """
    Objective:
    The new toggle-reset behavior should not remove the previous VBlank side
    effect.
    """
    ppu = PPU()
    ppu.status = VBLANK_STARTED
    ppu.write_register(0x2006, 0x23)

    ppu.read_register(0x2002)

    assert ppu.status == 0


def test_reading_ppustatus_does_not_modify_vram_addr():
    """
    Objective:
    Reading $2002 resets the write toggle, but it should not erase the current
    internal VRAM address.
    """
    ppu = PPU()
    ppu.write_register(0x2006, 0x23)
    ppu.write_register(0x2006, 0xC0)

    assert ppu.vram_addr == 0x23C0

    ppu.read_register(0x2002)

    assert ppu.vram_addr == 0x23C0


def test_ppuaddr_sequence_restarts_after_ppustatus_read():
    """
    Objective:
    Prove the practical effect of the reset: after reading $2002, the next $2006
    write is treated as a high-byte write.
    """
    ppu = PPU()

    ppu.write_register(0x2006, 0x23)
    assert ppu.second_write_toggle is True

    ppu.read_register(0x2002)

    ppu.write_register(0x2006, 0x20)

    assert ppu.temp_vram_addr == 0x2000
    assert ppu.vram_addr == 0x0000
    assert ppu.second_write_toggle is True
