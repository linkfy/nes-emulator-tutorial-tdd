"""
Create a mapper factory.

File to create:
    emulator/cartridge/mapper_factory.py

Function to implement:
    create_mapper(cartridge: Cartridge)

Why this step exists:
The Cartridge object stores facts loaded from the ROM:

    Cartridge(prg_rom, chr_rom, mapper_number)

But the CPU/PPU do not talk directly to raw PRG/CHR bytes. They talk through a
mapper, because the mapper is the cartridge hardware that translates emulator
addresses into ROM offsets.

Current flow:

    raw .nes bytes
        -> Cartridge.from_ines_bytes(data)
        -> create_mapper(cartridge)
        -> Mapper000(prg_rom, chr_rom)

Responsibilities of the factory:
    - inspect cartridge.mapper_number
    - create the correct mapper object
    - fail loudly for unsupported mappers

What the factory should NOT do:
    - parse iNES bytes
    - perform CPU address translation
    - know about CpuBus routing
    - mutate the Cartridge

Expected implementation shape:

    from emulator.cartridge.cartridge import Cartridge
    from emulator.cartridge.mapper000 import Mapper000


    def create_mapper(cartridge: Cartridge):
        if cartridge.mapper_number == 0:
            return Mapper000(
                prg_rom=cartridge.prg_rom,
                chr_rom=cartridge.chr_rom,
            )

        raise ValueError(f"Unsupported mapper: {cartridge.mapper_number}")

Why this is separate from CpuBus:
CpuBus should route reads and writes. It should not become responsible for every
cartridge mapper selection rule. Keeping mapper creation here reduces coupling
before we integrate cartridge-backed PRG ROM reads into the bus.
"""

from pathlib import Path

import pytest

from emulator.cartridge.cartridge import Cartridge
from emulator.cartridge.mapper000 import CHR_ROM_SIZE, Mapper000, NROM_128_SIZE
from emulator.cartridge.mapper_factory import create_mapper


def test_mapper_factory_file_exists():
    """
    Objective:
    Create emulator/cartridge/mapper_factory.py.

    Why:
    Mapper construction is a small policy decision: mapper number 0 means
    Mapper000, mapper number 1 will later mean something else, and so on.
    """
    assert Path("emulator/cartridge/mapper_factory.py").exists()


def test_create_mapper_exists_and_is_callable():
    """
    Objective:
    Expose create_mapper(cartridge).

    The caller should not need to know which concrete mapper class corresponds
    to each mapper number.
    """
    assert callable(create_mapper)


def test_create_mapper_returns_mapper000_for_mapper_number_zero():
    """
    Objective:
    Mapper number 0 should create Mapper000 / NROM.

    This is the simplest NES cartridge mapping and the only mapper supported at
    this tutorial stage.
    """
    cartridge = Cartridge(
        prg_rom=bytes([0xEA]) * NROM_128_SIZE,
        chr_rom=bytes([0x00]) * CHR_ROM_SIZE,
        mapper_number=0,
    )

    mapper = create_mapper(cartridge)

    assert isinstance(mapper, Mapper000)


def test_create_mapper_preserves_prg_and_chr_rom_data():
    """
    Objective:
    The factory must pass both PRG ROM and CHR ROM into Mapper000 unchanged.

    Why this matters:
    PRG ROM will be used by CPU bus reads in $8000-$FFFF.
    CHR ROM will be used later by PPU pattern-table reads in $0000-$1FFF.
    """
    prg_rom = bytes([0xA9]) * NROM_128_SIZE
    chr_rom = bytes([0xBB]) * CHR_ROM_SIZE
    cartridge = Cartridge(
        prg_rom=prg_rom,
        chr_rom=chr_rom,
        mapper_number=0,
    )

    mapper = create_mapper(cartridge)

    assert mapper.prg_rom == prg_rom
    assert mapper.chr_rom == chr_rom


def test_create_mapper_rejects_unsupported_mapper_number():
    """
    Objective:
    Unsupported mappers should fail loudly.

    Why:
    If the emulator silently treats an unsupported mapper as Mapper000, games may
    run with incorrect memory mapping. That kind of bug is hard to debug because
    the CPU may execute plausible but wrong bytes.
    """
    cartridge = Cartridge(
        prg_rom=bytes([0x00]) * NROM_128_SIZE,
        chr_rom=bytes([0x00]) * CHR_ROM_SIZE,
        mapper_number=1,
    )

    with pytest.raises(ValueError, match="Unsupported mapper: 1"):
        create_mapper(cartridge)
