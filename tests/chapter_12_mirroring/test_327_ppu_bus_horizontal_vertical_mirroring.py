"""
Apply horizontal or vertical nametable mirroring in PpuBus.

File to update:
    emulator/bus/ppu_bus.py

Why this step exists:
The mirroring bit now travels through:

    INesHeader
        -> Cartridge
        -> Mapper000
        -> PpuBus.mapper

PpuBus can finally use that metadata when mapping four logical nametables onto two
physical nametable RAM regions.

Logical nametables:

    table 0: $2000-$23FF
    table 1: $2400-$27FF
    table 2: $2800-$2BFF
    table 3: $2C00-$2FFF

Each table is $400 bytes. The complete logical window is $1000 bytes, while the
current physical backing window is $800 bytes.

Vertical mirroring:

    logical:  0 1 2 3
    physical: 0 1 0 1

    [A B]
    [A B]

Horizontal mirroring:

    logical:  0 1 2 3
    physical: 0 0 1 1

    [A A]
    [B B]

Suggested implementation example:

    # emulator/bus/ppu_bus.py

    NAMETABLE_SIZE = 0x800
    NAMETABLE_BYTES_PER_TABLE = 0x400
    NAMETABLE_LOGICAL_SIZE = 0x1000


    def normalize_nametable_addr(self, addr: int) -> int:
        if 0x3000 <= addr <= 0x3EFF:
            addr -= 0x1000

        logical_offset = (
            addr - NAMETABLE_START
        ) % NAMETABLE_LOGICAL_SIZE

        logical_table = logical_offset // NAMETABLE_BYTES_PER_TABLE
        offset_inside_table = logical_offset % NAMETABLE_BYTES_PER_TABLE

        is_vertical_mirroring = (
            True
            if self.mapper is None
            else self.mapper.is_vertical_mirroring
        )

        if is_vertical_mirroring:
            physical_table = logical_table % 2
        else:
            physical_table = logical_table // 2

        return (
            NAMETABLE_START
            + physical_table * NAMETABLE_BYTES_PER_TABLE
            + offset_inside_table
        )

Why preserve vertical behavior without a mapper?
Historical tutorial tests construct PpuBus directly and introduced the old fixed
$800 wrapping behavior before cartridge mirroring existed. Mapper-backed buses use
real cartridge metadata; mapper-less buses preserve that historical test model.

Important distinction:
Mirroring determines memory aliases. It does not move the visible viewport. The
current renderer still draws a fixed nametable region, so horizontal scrolling is a
separate future chapter.

Out of scope:
    - scroll-position extraction
    - viewport cropping across adjacent nametables
    - four-screen mirroring
    - mapper-controlled dynamic mirroring
    - commercial ROM fixtures
"""

from emulator.bus.ppu_bus import (
    NAMETABLE_BYTES_PER_TABLE,
    NAMETABLE_LOGICAL_SIZE,
    NAMETABLE_SIZE,
    PpuBus,
)
from emulator.cartridge.mapper000 import Mapper000


def make_mapper(is_vertical_mirroring: bool) -> Mapper000:
    return Mapper000(
        prg_rom=bytes([0xEA] * (16 * 1024)),
        chr_rom=bytes([0x00] * (8 * 1024)),
        is_vertical_mirroring=is_vertical_mirroring,
    )


def test_nametable_constants_distinguish_logical_and_physical_sizes():
    """
    Objective:
    Name the four-table logical window separately from the two-table physical RAM
    window.
    """
    assert NAMETABLE_BYTES_PER_TABLE == 0x400
    assert NAMETABLE_LOGICAL_SIZE == 0x1000
    assert NAMETABLE_SIZE == 0x800


def test_vertical_mirroring_maps_logical_tables_as_zero_one_zero_one():
    """
    Objective:
    Vertical mirroring keeps left/right tables distinct and repeats them vertically.
    """
    bus = PpuBus(mapper=make_mapper(is_vertical_mirroring=True))

    assert bus.normalize_nametable_addr(0x2000) == 0x2000
    assert bus.normalize_nametable_addr(0x2400) == 0x2400
    assert bus.normalize_nametable_addr(0x2800) == 0x2000
    assert bus.normalize_nametable_addr(0x2C00) == 0x2400


def test_horizontal_mirroring_maps_logical_tables_as_zero_zero_one_one():
    """
    Objective:
    Horizontal mirroring repeats left/right addresses and keeps top/bottom tables
    distinct.
    """
    bus = PpuBus(mapper=make_mapper(is_vertical_mirroring=False))

    assert bus.normalize_nametable_addr(0x2000) == 0x2000
    assert bus.normalize_nametable_addr(0x2400) == 0x2000
    assert bus.normalize_nametable_addr(0x2800) == 0x2400
    assert bus.normalize_nametable_addr(0x2C00) == 0x2400


def test_vertical_mirroring_preserves_offset_inside_each_table():
    """
    Objective:
    Mirroring changes the physical table selection, not the byte position inside the
    selected table.
    """
    bus = PpuBus(mapper=make_mapper(is_vertical_mirroring=True))

    assert bus.normalize_nametable_addr(0x2A34) == 0x2234
    assert bus.normalize_nametable_addr(0x2E34) == 0x2634


def test_horizontal_mirroring_preserves_offset_inside_each_table():
    """
    Objective:
    Logical tables 0/1 share physical table 0, while 2/3 share physical table 1.
    """
    bus = PpuBus(mapper=make_mapper(is_vertical_mirroring=False))

    assert bus.normalize_nametable_addr(0x2634) == 0x2234
    assert bus.normalize_nametable_addr(0x2A34) == 0x2634


def test_vertical_mirroring_read_write_aliases():
    """
    Objective:
    Public PpuBus reads/writes should observe the vertical alias pairs, not only the
    normalization helper's return value.
    """
    bus = PpuBus(mapper=make_mapper(is_vertical_mirroring=True))

    bus.write(0x2000, 0x11)
    bus.write(0x2400, 0x22)

    assert bus.read(0x2800) == 0x11
    assert bus.read(0x2C00) == 0x22


def test_horizontal_mirroring_read_write_aliases():
    """
    Objective:
    Public PpuBus reads/writes should observe the horizontal alias pairs.
    """
    bus = PpuBus(mapper=make_mapper(is_vertical_mirroring=False))

    bus.write(0x2000, 0x33)
    bus.write(0x2800, 0x44)

    assert bus.read(0x2400) == 0x33
    assert bus.read(0x2C00) == 0x44


def test_horizontal_physical_tables_remain_independent():
    """
    Objective:
    Horizontal mirroring aliases 0/1 and 2/3, but physical tables A and B must still
    store independent values.
    """
    bus = PpuBus(mapper=make_mapper(is_vertical_mirroring=False))

    bus.write(0x2000, 0x55)
    bus.write(0x2800, 0x66)

    assert bus.read(0x2000) == 0x55
    assert bus.read(0x2400) == 0x55
    assert bus.read(0x2800) == 0x66
    assert bus.read(0x2C00) == 0x66


def test_3000_range_is_mirrored_before_cartridge_nametable_mapping():
    """
    Objective:
    $3000-$3EFF first mirrors down by $1000, then horizontal/vertical mapping is
    applied to the resulting logical nametable address.
    """
    vertical_bus = PpuBus(mapper=make_mapper(is_vertical_mirroring=True))
    horizontal_bus = PpuBus(mapper=make_mapper(is_vertical_mirroring=False))

    assert vertical_bus.normalize_nametable_addr(0x3000) == 0x2000
    assert vertical_bus.normalize_nametable_addr(0x3400) == 0x2400
    assert horizontal_bus.normalize_nametable_addr(0x3000) == 0x2000
    assert horizontal_bus.normalize_nametable_addr(0x3400) == 0x2000


def test_mapperless_ppu_bus_preserves_historical_vertical_mapping():
    """
    Objective:
    Older direct PpuBus tests remain valid until every synthetic caller explicitly
    provides cartridge mirroring metadata.
    """
    bus = PpuBus()

    assert bus.normalize_nametable_addr(0x2000) == 0x2000
    assert bus.normalize_nametable_addr(0x2400) == 0x2400
    assert bus.normalize_nametable_addr(0x2800) == 0x2000
    assert bus.normalize_nametable_addr(0x2C00) == 0x2400
