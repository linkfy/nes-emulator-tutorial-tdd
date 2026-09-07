"""
Implement PPUDATA ($2007) buffered read behavior.

Reference:
    https://www.nesdev.org/wiki/PPU_registers#PPUDATA

File to update:
    emulator/ppu/ppu.py

State to add:
    ppu_data_buffer: int = 0

Why this step exists:
PPUDATA is not a normal simple register. It is a CPU-visible port into PPU
memory. For most PPU memory reads, the NES returns the old internal read buffer,
then reloads that buffer from the current PPU memory address.

Normal buffered read behavior:

    read $2007:
        value = ppu_data_buffer
        ppu_data_buffer = ppu_bus.read(vram_addr)
        vram_addr += increment
        return value

This means the first read usually returns stale/old buffer data, and the second
read returns the byte that was loaded by the first read.

Example:

    ppu_bus[$2000] = $AA
    ppu_bus[$2001] = $BB
    ppu_data_buffer = $00
    vram_addr = $2000

    read $2007 -> returns $00, buffer becomes $AA, vram_addr becomes $2001
    read $2007 -> returns $AA, buffer becomes $BB, vram_addr becomes $2002

Compatibility/debug field:
The older tutorial model had `data` as a simple PPUDATA value. Keep `self.data`
as a compatibility/debug field containing the value returned by the latest
PPUDATA read, but the real behavior should use:

    ppu_data_buffer
    ppu_bus.read(vram_addr)

Suggested implementation pseudocode:

    @dataclass
    class PPU:
        ...
        data: int = 0  # Compatibility/debug: last PPUDATA value
        ppu_data_buffer: int = 0

        def read_register(self, addr: int) -> int:
            match addr:
                ...
                case 0x2007:
                    value = self.ppu_data_buffer
                    self.ppu_data_buffer = self.ppu_bus.read(self.vram_addr)

                    increment = 32 if self.ctrl & CTRL_VRAM_INCREMENT_BY_32 else 1
                    self.vram_addr = (self.vram_addr + increment) & 0x3FFF

                    # Preserve old compatibility/debug field.
                    self.data = value
                    return self.data

Important future note:
Palette reads from $3F00-$3FFF are an exception on real hardware. They return
the palette byte immediately instead of returning the delayed buffer value. That
exception is intentionally not implemented in this test.

Out of scope:
    - palette read exception
    - palette RAM accuracy
    - PPUDATA writes, already tested earlier
"""

from emulator.ppu.ppu import CTRL_VRAM_INCREMENT_BY_32, PPU


def set_ppuaddr(ppu: PPU, addr: int) -> None:
    """Set PPU.vram_addr through the public $2006 two-write interface."""
    ppu.write_register(0x2006, (addr >> 8) & 0xFF)
    ppu.write_register(0x2006, addr & 0xFF)


def test_ppu_has_ppudata_read_buffer():
    """
    Objective:
    Add the internal PPUDATA read buffer.
    """
    assert "ppu_data_buffer" in PPU.__dataclass_fields__

    ppu = PPU()

    assert ppu.ppu_data_buffer == 0


def test_first_ppudata_read_returns_old_buffer_and_loads_memory_value():
    """
    Objective:
    The first normal PPUDATA read should return the old buffer, then load the
    buffer from PPU memory at vram_addr.

    This test uses $2000, not palette range $3F00-$3FFF, to avoid the future
    palette read exception.
    """
    ppu = PPU()
    ppu.ppu_bus.write(0x2000, 0xAA)
    set_ppuaddr(ppu, 0x2000)

    value = ppu.read_register(0x2007)

    assert value == 0x00
    assert ppu.ppu_data_buffer == 0xAA


def test_second_ppudata_read_returns_value_loaded_by_previous_read():
    """
    Objective:
    The second normal PPUDATA read should return the value loaded into the buffer
    by the first read.
    """
    ppu = PPU()
    ppu.ppu_bus.write(0x2000, 0xAA)
    ppu.ppu_bus.write(0x2001, 0xBB)
    set_ppuaddr(ppu, 0x2000)

    assert ppu.read_register(0x2007) == 0x00
    assert ppu.read_register(0x2007) == 0xAA
    assert ppu.ppu_data_buffer == 0xBB


def test_ppudata_read_increments_vram_addr_by_one_when_increment_bit_is_clear():
    """
    Objective:
    PPUDATA reads increment vram_addr just like PPUDATA writes.

    With PPUCTRL bit 2 clear, the increment is 1.
    """
    ppu = PPU()
    ppu.write_register(0x2000, 0x00)
    set_ppuaddr(ppu, 0x2000)

    ppu.read_register(0x2007)

    assert ppu.vram_addr == 0x2001


def test_ppudata_read_increments_vram_addr_by_32_when_increment_bit_is_set():
    """
    Objective:
    With PPUCTRL bit 2 set, PPUDATA reads increment vram_addr by 32.
    """
    ppu = PPU()
    ppu.write_register(0x2000, CTRL_VRAM_INCREMENT_BY_32)
    set_ppuaddr(ppu, 0x2000)

    ppu.read_register(0x2007)

    assert ppu.vram_addr == 0x2020


def test_ppudata_read_updates_data_as_compatibility_debug_field():
    """
    Objective:
    Preserve `data` as the last value returned by PPUDATA for old tests and easy
    debugging.

    Important:
    `data` is not the real source of PPUDATA reads anymore. The real source is
    ppu_data_buffer and ppu_bus.read(vram_addr).
    """
    ppu = PPU()
    ppu.ppu_data_buffer = 0xCC
    set_ppuaddr(ppu, 0x2000)

    value = ppu.read_register(0x2007)

    assert value == 0xCC
    assert ppu.data == 0xCC


def test_ppudata_read_wraps_vram_addr_to_14_bit_ppu_address_space():
    """
    Objective:
    vram_addr should stay inside $0000-$3FFF after PPUDATA reads.
    """
    ppu = PPU()
    ppu.write_register(0x2000, CTRL_VRAM_INCREMENT_BY_32)
    set_ppuaddr(ppu, 0x3FF0)

    ppu.read_register(0x2007)

    assert ppu.vram_addr == ((0x3FF0 + 32) & 0x3FFF)
