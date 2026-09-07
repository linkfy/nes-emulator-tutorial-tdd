"""
Preserve decoded nametable mirroring metadata in Cartridge.

File to update:
    emulator/cartridge/cartridge.py

Why this step exists:
Step 324 decodes iNES flags 6 bit 0 through:

    INesHeader.is_vertical_mirroring

That information must survive after parsing so later mapper and PpuBus steps can
choose the correct nametable address mapping.

Metadata path for this step:

    iNES flags 6
        -> INesHeader.is_vertical_mirroring
        -> Cartridge.is_vertical_mirroring

Suggested implementation changes:

    @dataclass
    class Cartridge:
        prg_rom: bytes
        chr_rom: bytes
        mapper_number: int
        chr_ram: bytearray | None = None

        # --- NEW LINE ---
        is_vertical_mirroring: bool = False
        # --- END NEW LINE ---


    @classmethod
    def from_ines_bytes(cls, data: bytes) -> "Cartridge":
        ines_rom = parse_ines_rom(data)

        return cls(
            prg_rom=ines_rom.prg_rom,
            chr_rom=ines_rom.chr_rom,
            mapper_number=ines_rom.header.mapper_number,

            # --- NEW LINE ---
            is_vertical_mirroring=ines_rom.header.is_vertical_mirroring,
            # --- END NEW LINE ---
        )

Why append a defaulted field?
Historical tutorial code directly constructs Cartridge using three or four
positional arguments. Appending a defaulted field preserves those constructor
shapes while allowing parsed ROMs to provide real metadata.

Meaning:

    False -> horizontal mirroring
    True  -> vertical mirroring

Out of scope:
    - changing Mapper000
    - changing MapperInterface
    - changing mapper_factory
    - changing PpuBus nametable mapping
    - four-screen mirroring
    - scrolling
    - commercial ROM fixtures
"""

from emulator.cartridge.cartridge import Cartridge
from emulator.cartridge.ines import INES_MAGIC


def make_ines_rom(
    flags_6: int,
    prg_banks: int = 1,
    chr_banks: int = 1,
) -> bytes:
    """Build a synthetic iNES ROM with valid PRG and CHR payload sizes."""
    header = bytes([
        *INES_MAGIC,
        prg_banks,
        chr_banks,
        flags_6,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    ])
    prg_rom = bytes([0xEA] * (prg_banks * 16 * 1024))
    chr_rom = bytes([0x00] * (chr_banks * 8 * 1024))
    return header + prg_rom + chr_rom


def test_direct_cartridge_construction_defaults_to_horizontal_mirroring():
    """
    Objective:
    Existing direct constructors remain valid, and a missing mirroring argument uses
    the flags-bit-clear interpretation: horizontal.
    """
    cartridge = Cartridge(
        prg_rom=bytes([0xEA]),
        chr_rom=bytes([0x00]),
        mapper_number=0,
    )

    assert cartridge.is_vertical_mirroring is False


def test_direct_cartridge_construction_can_request_vertical_mirroring():
    """
    Objective:
    Synthetic tests and future cartridge builders can explicitly provide vertical
    mirroring metadata.
    """
    cartridge = Cartridge(
        prg_rom=bytes([0xEA]),
        chr_rom=bytes([0x00]),
        mapper_number=0,
        is_vertical_mirroring=True,
    )

    assert cartridge.is_vertical_mirroring is True


def test_old_fourth_positional_argument_still_represents_chr_ram():
    """
    Objective:
    Appending mirroring metadata must not reinterpret the historical fourth
    positional argument.
    """
    chr_ram = bytearray(8 * 1024)

    cartridge = Cartridge(
        bytes([0xEA]),
        bytes(),
        0,
        chr_ram,
    )

    assert cartridge.chr_ram is chr_ram
    assert cartridge.is_vertical_mirroring is False


def test_horizontal_ines_header_produces_horizontal_cartridge():
    """
    Objective:
    iNES flags 6 bit 0 clear should remain False after the ROM becomes a Cartridge.
    """
    cartridge = Cartridge.from_ines_bytes(
        make_ines_rom(flags_6=0b0000_0000)
    )

    assert cartridge.is_vertical_mirroring is False


def test_vertical_ines_header_produces_vertical_cartridge():
    """
    Objective:
    iNES flags 6 bit 0 set should remain True after the ROM becomes a Cartridge.
    """
    cartridge = Cartridge.from_ines_bytes(
        make_ines_rom(flags_6=0b0000_0001)
    )

    assert cartridge.is_vertical_mirroring is True


def test_mirroring_propagation_preserves_existing_cartridge_data():
    """
    Objective:
    Adding metadata must not alter PRG ROM, CHR ROM, or mapper decoding.
    """
    data = make_ines_rom(
        flags_6=0b0010_0001,
        prg_banks=1,
        chr_banks=1,
    )

    cartridge = Cartridge.from_ines_bytes(data)

    assert cartridge.mapper_number == 2
    assert len(cartridge.prg_rom) == 16 * 1024
    assert len(cartridge.chr_rom) == 8 * 1024
    assert cartridge.is_vertical_mirroring is True


def test_new_metadata_is_appended_after_historical_cartridge_fields():
    """
    Objective:
    Preserve the positional compatibility invariant without freezing Cartridge
    against additional optional metadata in later tutorial steps.
    """
    field_names = list(Cartridge.__dataclass_fields__)
    historical_prefix = [
        "prg_rom",
        "chr_rom",
        "mapper_number",
        "chr_ram",
    ]

    assert field_names[: len(historical_prefix)] == historical_prefix
    assert "is_vertical_mirroring" in field_names[len(historical_prefix):]
