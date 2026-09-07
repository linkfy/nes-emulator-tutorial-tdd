"""
Implement OAM memory and OAMADDR/OAMDATA behavior.

References:
    https://www.nesdev.org/wiki/PPU_registers#OAMADDR
    https://www.nesdev.org/wiki/PPU_registers#OAMDATA
    https://www.nesdev.org/wiki/PPU_OAM

File to update:
    emulator/ppu/ppu.py

State to add:
    OAM_SIZE = 256
    oam: bytearray = field(default_factory=lambda: bytearray(OAM_SIZE))

Why this step exists:
OAM means Object Attribute Memory. It is the PPU's internal 256-byte sprite
memory. The PPU renders sprites from OAM, not directly from CPU RAM.

Sprite layout:
    NES OAM stores 64 sprites.
    Each sprite uses 4 bytes.

    64 sprites * 4 bytes = 256 bytes

Basic sprite byte layout:
    byte 0: Y position
    byte 1: tile index
    byte 2: attributes
    byte 3: X position

CPU-visible registers:

    $2003 OAMADDR
        selects which OAM byte is currently addressed

    $2004 OAMDATA
        reads/writes OAM at the current OAMADDR

Important behavior for this step:
    - writing $2003 sets oam_addr
    - writing $2004 stores into oam[oam_addr]
    - writing $2004 increments oam_addr with & 0xFF
    - reading $2004 returns oam[oam_addr]

Why OAM is not PpuBus VRAM:
PpuBus handles the PPU address space used by PPUADDR/PPUDATA:

    $0000-$3FFF

OAM is separate internal sprite memory accessed through OAMADDR/OAMDATA:

    $2003/$2004

Suggested implementation pseudocode:

    OAM_SIZE = 256

    @dataclass
    class PPU:
        ...
        oam_addr: int = 0
        oam_data: int = 0
        oam: bytearray = field(default_factory=lambda: bytearray(OAM_SIZE))

        def write_register(self, addr: int, value: int) -> None:
            value = value & 0xFF

            match addr:
                ...
                case 0x2003:
                    self.oam_addr = value

                case 0x2004:
                    # Preserve old compatibility/debug field.
                    self.oam_data = value

                    # Write to current OAM byte.
                    self.oam[self.oam_addr] = value

                    # OAMADDR increments after OAMDATA write.
                    self.oam_addr = (self.oam_addr + 1) & 0xFF

                ...

        def read_register(self, addr: int) -> int:
            match addr:
                ...
                case 0x2004:
                    self.oam_data = self.oam[self.oam_addr]
                    return self.oam_data

Out of scope:
    - OAMDMA at $4014
    - sprite evaluation
    - sprite rendering
    - sprite overflow behavior
    - sprite 0 hit behavior
"""

from emulator.ppu.ppu import OAM_SIZE, PPU


def test_ppu_declares_oam_size_and_oam_memory():
    """
    Objective:
    Add 256 bytes of internal PPU sprite memory.
    """
    assert OAM_SIZE == 256
    assert "oam" in PPU.__dataclass_fields__

    ppu = PPU()

    assert len(ppu.oam) == OAM_SIZE
    assert all(value == 0 for value in ppu.oam)


def test_oamaddr_write_selects_current_oam_address():
    """
    Objective:
    Writing $2003 should set OAMADDR.
    """
    ppu = PPU()

    ppu.write_register(0x2003, 0x10)

    assert ppu.oam_addr == 0x10


def test_oamdata_write_stores_value_at_current_oam_address():
    """
    Objective:
    Writing $2004 should store the value into OAM at the current OAMADDR.
    """
    ppu = PPU()
    ppu.write_register(0x2003, 0x10)

    ppu.write_register(0x2004, 0xAB)

    assert ppu.oam[0x10] == 0xAB


def test_oamdata_write_increments_oamaddr():
    """
    Objective:
    After writing $2004, OAMADDR should increment to the next OAM byte.
    """
    ppu = PPU()
    ppu.write_register(0x2003, 0x10)

    ppu.write_register(0x2004, 0xAB)

    assert ppu.oam_addr == 0x11


def test_oamdata_write_wraps_oamaddr_from_ff_to_00():
    """
    Objective:
    OAMADDR is one byte, so it wraps after $FF.
    """
    ppu = PPU()
    ppu.write_register(0x2003, 0xFF)

    ppu.write_register(0x2004, 0xCD)

    assert ppu.oam[0xFF] == 0xCD
    assert ppu.oam_addr == 0x00


def test_oamdata_read_returns_current_oam_byte_without_incrementing():
    """
    Objective:
    Reading $2004 should return oam[oam_addr].

    For this stage, reads do not increment OAMADDR.
    """
    ppu = PPU()
    ppu.oam[0x20] = 0xEF
    ppu.write_register(0x2003, 0x20)

    value = ppu.read_register(0x2004)

    assert value == 0xEF
    assert ppu.oam_addr == 0x20


def test_oamdata_preserves_oam_data_as_last_read_or_written_value():
    """
    Objective:
    Keep oam_data as a compatibility/debug field for the last OAMDATA access.
    """
    ppu = PPU()
    ppu.write_register(0x2003, 0x30)
    ppu.write_register(0x2004, 0x12)

    assert ppu.oam_data == 0x12

    ppu.write_register(0x2003, 0x30)
    ppu.read_register(0x2004)

    assert ppu.oam_data == 0x12


def test_oamdata_write_stores_only_low_byte():
    """
    Objective:
    OAM stores bytes, so OAMDATA writes keep only the low 8 bits.
    """
    ppu = PPU()
    ppu.write_register(0x2003, 0x00)

    ppu.write_register(0x2004, 0x123)

    assert ppu.oam[0x00] == 0x23
