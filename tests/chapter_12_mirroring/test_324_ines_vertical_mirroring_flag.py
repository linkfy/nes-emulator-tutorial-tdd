"""
Decode horizontal/vertical nametable mirroring from iNES flags 6 bit 0.

File to update:
    emulator/cartridge/ines.py
Reference:
    https://www.nesdev.org/wiki/Mirroring#Nametable_Mirroring

Why this step exists:
Before implementing a scrolling viewport, the emulator must know how the cartridge
wires logical PPU nametables onto physical nametable RAM.

Mirroring does not visually flip an image. It controls memory mapping between the
four logical nametable regions:

    $2000
    $2400
    $2800
    $2C00

iNES flags 6 bit 0 selects the basic mirroring mode:

    bit 0 clear -> horizontal mirroring
    bit 0 set   -> vertical mirroring

For the current incremental scope, expose this as one boolean property:

    is_vertical_mirroring is False -> horizontal
    is_vertical_mirroring is True  -> vertical

Suggested implementation example:

    FLAGS6_VERTICAL_MIRRORING = 1 << 0


    @dataclass(frozen=True)
    class INesHeader:
        prg_rom_banks: int
        chr_rom_banks: int
        mapper_number: int
        has_trainer: bool
        flags_6: int
        flags_7: int

        @property
        def is_vertical_mirroring(self) -> bool:
            return (self.flags_6 & FLAGS6_VERTICAL_MIRRORING) != 0

Why a computed property?
flags_6 remains the single source of truth, and the existing INesHeader constructor
does not need to change. That preserves older tutorial callers and tests.

Future extension:
Four-screen mirroring can later add an is_four_screen property checked before
is_vertical_mirroring. Four-screen storage and routing are not implemented here.

Out of scope:
    - changing Cartridge
    - changing Mapper000
    - changing PpuBus nametable mapping
    - four-screen nametable RAM
    - scrolling
    - commercial ROM fixtures
"""

from emulator.cartridge.ines import (
    FLAGS6_VERTICAL_MIRRORING,
    INES_MAGIC,
    INesHeader,
    parse_ines_header,
)


def make_header_bytes(flags_6: int = 0, flags_7: int = 0) -> bytes:
    """Build a minimal 16-byte iNES header with configurable flag bytes."""
    return bytes([
        *INES_MAGIC,
        1,
        1,
        flags_6,
        flags_7,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    ])


def test_flags6_vertical_mirroring_constant_names_bit_zero():
    """
    Objective:
    Give iNES flags 6 bit 0 a domain-specific name instead of repeating a magic
    binary literal.
    """
    assert FLAGS6_VERTICAL_MIRRORING == 1 << 0


def test_ines_header_exposes_vertical_mirroring_property():
    """
    Objective:
    Mirroring metadata should be available directly from an INesHeader instance.
    """
    header = INesHeader(
        prg_rom_banks=1,
        chr_rom_banks=1,
        mapper_number=0,
        has_trainer=False,
        flags_6=0,
        flags_7=0,
    )

    assert hasattr(header, "is_vertical_mirroring")
    assert isinstance(header.is_vertical_mirroring, bool)


def test_flags6_bit_zero_clear_means_horizontal_mirroring():
    """
    Objective:
    False means horizontal mirroring; it does not mean mirroring is disabled.
    """
    header = parse_ines_header(make_header_bytes(flags_6=0b0000_0000))

    assert header.is_vertical_mirroring is False


def test_flags6_bit_zero_set_means_vertical_mirroring():
    """
    Objective:
    Setting flags 6 bit 0 requests vertical nametable mirroring.
    """
    header = parse_ines_header(
        make_header_bytes(flags_6=FLAGS6_VERTICAL_MIRRORING)
    )

    assert header.is_vertical_mirroring is True


def test_unrelated_flags6_bits_do_not_select_vertical_mirroring():
    """
    Objective:
    Trainer and mapper bits must not be confused with the mirroring bit.
    """
    unrelated_bits = 0b1010_0100
    assert (unrelated_bits & FLAGS6_VERTICAL_MIRRORING) == 0

    header = parse_ines_header(make_header_bytes(flags_6=unrelated_bits))

    assert header.is_vertical_mirroring is False


def test_vertical_mirroring_bit_can_coexist_with_other_flags():
    """
    Objective:
    Mirroring decoding should inspect bit 0 without discarding trainer or mapper
    information from the same flags byte.
    """
    flags_6 = 0b0010_0101

    header = parse_ines_header(make_header_bytes(flags_6=flags_6))

    assert header.is_vertical_mirroring is True
    assert header.has_trainer is True
    assert header.mapper_number == 2


def test_mirroring_property_does_not_change_ines_header_constructor_shape():
    """
    Objective:
    The property is computed from existing flags_6 metadata, so historical direct
    INesHeader construction remains valid.
    """
    header = INesHeader(1, 1, 0, False, 0, 0)

    assert header.prg_rom_banks == 1
    assert header.chr_rom_banks == 1
    assert header.is_vertical_mirroring is False
