"""
Implement PPUADDR ($2006) two-write address behavior.

Reference:
    https://www.nesdev.org/wiki/PPU_registers#PPUADDR

File to update:
    emulator/ppu/ppu.py

State to add:
    vram_addr: int = 0
    temp_vram_addr: int = 0
    second_write_toggle: bool = False

Why this step exists:
PPUADDR is the CPU-visible register at $2006. The CPU uses it to set the PPU's
internal VRAM address. That internal address is later used by PPUDATA ($2007) to
read/write PPU memory.

Important idea:
$2006 is not just a simple one-byte storage register. It is a two-write port.
The CPU writes the address in two parts:

    first write  -> high byte
    second write -> low byte

Example:

    write $20 to $2006
    write $00 to $2006

Result after both writes:

    vram_addr == $2000

Important internal-register model:
The first $2006 write updates temp_vram_addr, not vram_addr. The second $2006
write completes temp_vram_addr and copies it into vram_addr.

Why `second_write_toggle`:
The PPU must remember whether the next $2006 write is the first or second write.
In this tutorial, `second_write_toggle` means:

    False -> next $2006 write is the first write / high byte
    True  -> next $2006 write is the second write / low byte

Why the high byte is masked with 0x3F:
The PPU address space is 14-bit:

    $0000-$3FFF

Only the lower 6 bits of the high byte are useful for this address range. So the
first write should use:

    (value & 0x3F) << 8

Suggested implementation pseudocode:

    @dataclass
    class PPU:
        ...
        addr: int = 0
        vram_addr: int = 0
        temp_vram_addr: int = 0
        second_write_toggle: bool = False

        def write_register(self, addr: int, value: int) -> None:
            value = value & 0xFF

            match addr:
                ...
                case 0x2006:
                    # Keep old simple register-field behavior for test compatibility.
                    self.addr = value

                    if not self.second_write_toggle:
                        self.temp_vram_addr = (
                            (self.temp_vram_addr & 0x00FF)
                            | ((value & 0x3F) << 8)
                        )
                        self.second_write_toggle = True
                    else:
                        self.temp_vram_addr = (
                            (self.temp_vram_addr & 0x3F00)
                            | value
                        )
                        self.vram_addr = self.temp_vram_addr
                        self.second_write_toggle = False

                ...

Out of scope:
    - PPUDATA ($2007) writing through PpuBus
    - PPUSTATUS ($2002) resetting the write toggle
    - PPUSCROLL ($2005) using this same toggle
    - increment-by-32 behavior from PPUCTRL
"""

from emulator.ppu.ppu import PPU


def test_ppuaddr_uses_existing_internal_address_state():
    """
    Objective:
    PPUADDR uses the internal state introduced in the previous step.

    `addr` remains the simple last-written $2006 byte for test compatibility.
    `temp_vram_addr` is built by $2006 writes, and `vram_addr` is updated after
    the second write.
    """
    assert "vram_addr" in PPU.__dataclass_fields__
    assert "temp_vram_addr" in PPU.__dataclass_fields__
    assert "second_write_toggle" in PPU.__dataclass_fields__

    ppu = PPU()

    assert ppu.vram_addr == 0
    assert ppu.temp_vram_addr == 0
    assert ppu.second_write_toggle is False


def test_first_ppuaddr_write_sets_high_byte_and_enables_second_write():
    """
    Objective:
    The first write to $2006 sets the high byte of temp_vram_addr.

    Example:
        write $20 to $2006 -> temp_vram_addr becomes $2000
        vram_addr remains unchanged until the second write
    """
    ppu = PPU()

    ppu.write_register(0x2006, 0x20)

    assert ppu.temp_vram_addr == 0x2000
    assert ppu.vram_addr == 0x0000
    assert ppu.second_write_toggle is True


def test_second_ppuaddr_write_sets_low_byte_and_resets_toggle():
    """
    Objective:
    The second write to $2006 completes the internal PPU address.

    Example:
        write $23 to $2006
        write $C0 to $2006

    Result:
        vram_addr == $23C0
    """
    ppu = PPU()

    ppu.write_register(0x2006, 0x23)
    ppu.write_register(0x2006, 0xC0)

    assert ppu.vram_addr == 0x23C0
    assert ppu.temp_vram_addr == 0x23C0
    assert ppu.second_write_toggle is False


def test_ppuaddr_high_byte_is_limited_to_14_bit_ppu_address_space():
    """
    Objective:
    The high byte write should be masked with 0x3F.

    Why:
    PPU addresses are 14-bit, so the internal address must stay within
    $0000-$3FFF.

    Example:
        $FF & $3F == $3F
        $3F << 8 == $3F00
    """
    ppu = PPU()

    ppu.write_register(0x2006, 0xFF)

    assert ppu.temp_vram_addr == 0x3F00
    assert ppu.vram_addr == 0x0000
    assert ppu.second_write_toggle is True


def test_ppuaddr_preserves_addr_as_last_written_value_for_compatibility():
    """
    Objective:
    Keep the earlier simple `addr` (unnecesary field) for old tests compatibility.

    Important:
    `addr` is not the full internal PPU address. The full current address is
    vram_addr after the second $2006 write.
    """
    ppu = PPU()

    ppu.write_register(0x2006, 0x20)
    assert ppu.addr == 0x20

    ppu.write_register(0x2006, 0x00)
    assert ppu.addr == 0x00
    assert ppu.vram_addr == 0x2000
