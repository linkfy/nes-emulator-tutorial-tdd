"""
Propagate nametable mirroring metadata from Cartridge into Mapper000.

Files to update:
    emulator/cartridge/mapper000.py
    emulator/cartridge/mapper_factory.py
    emulator/cartridge/mapper_interface.py

Why this step exists:
PpuBus already receives the cartridge mapper. Exposing mirroring through the mapper
keeps one cartridge-hardware ownership path:

    INesHeader
        -> Cartridge
        -> Mapper000
        -> PpuBus (next step)

This is preferable to separately connecting Cartridge directly to PpuBus. Future
mappers may control mirroring through mapper registers, so the mapper is the useful
long-term boundary.

Suggested implementation changes:

    # emulator/cartridge/mapper000.py

    @dataclass
    class Mapper000:
        prg_rom: bytes
        chr_rom: bytes

        # --- NEW LINE ---
        is_vertical_mirroring: bool = False
        # --- END NEW LINE ---

        ...


    # emulator/cartridge/mapper_factory.py

    def create_mapper(cartridge: Cartridge):
        if cartridge.mapper_number == 0:
            return Mapper000(
                prg_rom=cartridge.prg_rom,
                chr_rom=cartridge.chr_rom,

                # --- NEW LINE ---
                is_vertical_mirroring=cartridge.is_vertical_mirroring,
                # --- END NEW LINE ---
            )

        ...


    # emulator/cartridge/mapper_interface.py

    class MapperInterface(Protocol):
        # --- NEW LINE ---
        is_vertical_mirroring: bool
        # --- END NEW LINE ---

        def read_prg(self, addr: int) -> int:
            ...

Why append a defaulted Mapper000 field?
Historical tests and tutorial code construct Mapper000 with only PRG and CHR ROM.
Appending a False default preserves that constructor and means horizontal mirroring
when no metadata is supplied.

Meaning:

    False -> horizontal mirroring
    True  -> vertical mirroring

Out of scope:
    - changing PpuBus address mapping
    - changing CpuBus ownership
    - four-screen mirroring
    - scrolling
    - commercial ROM fixtures
"""

from emulator.cartridge.cartridge import Cartridge
from emulator.cartridge.mapper000 import Mapper000
from emulator.cartridge.mapper_factory import create_mapper
from emulator.cartridge.mapper_interface import MapperInterface


def make_cartridge(is_vertical_mirroring: bool) -> Cartridge:
    return Cartridge(
        prg_rom=bytes([0xEA] * (16 * 1024)),
        chr_rom=bytes([0x00] * (8 * 1024)),
        mapper_number=0,
        is_vertical_mirroring=is_vertical_mirroring,
    )


def test_mapper_interface_exposes_vertical_mirroring_metadata():
    """
    Objective:
    PpuBus should eventually be able to obtain mirroring through the common mapper
    contract rather than depending directly on Cartridge.
    """
    assert MapperInterface.__annotations__["is_vertical_mirroring"] is bool


def test_direct_mapper000_construction_defaults_to_horizontal_mirroring():
    """
    Objective:
    Preserve the historical two-argument Mapper000 constructor.
    """
    mapper = Mapper000(
        prg_rom=bytes([0xEA] * (16 * 1024)),
        chr_rom=bytes([0x00] * (8 * 1024)),
    )

    assert mapper.is_vertical_mirroring is False


def test_direct_mapper000_construction_can_request_vertical_mirroring():
    """
    Objective:
    Mapper000 can explicitly represent fixed vertical cartridge wiring.
    """
    mapper = Mapper000(
        prg_rom=bytes([0xEA] * (16 * 1024)),
        chr_rom=bytes([0x00] * (8 * 1024)),
        is_vertical_mirroring=True,
    )

    assert mapper.is_vertical_mirroring is True


def test_mapper_factory_preserves_horizontal_cartridge_mirroring():
    """
    Objective:
    A horizontal Cartridge should create a horizontal Mapper000.
    """
    cartridge = make_cartridge(is_vertical_mirroring=False)

    mapper = create_mapper(cartridge)

    assert isinstance(mapper, Mapper000)
    assert mapper.is_vertical_mirroring is False


def test_mapper_factory_preserves_vertical_cartridge_mirroring():
    """
    Objective:
    A vertical Cartridge should create a vertical Mapper000.
    """
    cartridge = make_cartridge(is_vertical_mirroring=True)

    mapper = create_mapper(cartridge)

    assert isinstance(mapper, Mapper000)
    assert mapper.is_vertical_mirroring is True


def test_mapper_factory_still_forwards_original_rom_data():
    """
    Objective:
    Adding mirroring metadata must not alter or copy away the existing PRG/CHR
    ownership inputs.
    """
    cartridge = make_cartridge(is_vertical_mirroring=True)

    mapper = create_mapper(cartridge)

    assert mapper.prg_rom is cartridge.prg_rom
    assert mapper.chr_rom is cartridge.chr_rom


def test_new_mapper_metadata_is_appended_after_historical_fields():
    """
    Objective:
    Preserve positional compatibility while allowing optional mapper metadata.
    """
    field_names = list(Mapper000.__dataclass_fields__)

    assert field_names[:2] == ["prg_rom", "chr_rom"]
    assert "is_vertical_mirroring" in field_names[2:]
