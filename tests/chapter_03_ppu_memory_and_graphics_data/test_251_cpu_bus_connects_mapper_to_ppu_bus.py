"""
Connect the cartridge mapper to PpuBus.

File to update:
    emulator/bus/cpu_bus.py

Why this step exists:
The CPU uses the mapper for PRG ROM reads. The PPU also needs the same mapper for
CHR ROM reads in $0000-$1FFF.

Expected wiring:

    if cartridge is not None:
        self.mapper = create_mapper(cartridge)
        self.ppu.ppu_bus.mapper = self.mapper

Important:
Use the same mapper object for CpuBus and PpuBus. Later mappers may have internal
bank-switching state, so CPU and PPU must see the same mapper state.
"""

from emulator.bus.cpu_bus import CpuBus
from emulator.cartridge.cartridge import Cartridge
from emulator.cartridge.mapper000 import CHR_ROM_SIZE, Mapper000, NROM_128_SIZE
from emulator.memory.fake_rom import FakeROM


def make_mapper000_cartridge() -> Cartridge:
    """Create a small Mapper000-compatible cartridge with visible CHR data."""
    chr_rom = bytearray(CHR_ROM_SIZE)
    chr_rom[0x0000] = 0x12
    chr_rom[0x1FFF] = 0x34

    return Cartridge(
        prg_rom=bytes([0xEA]) * NROM_128_SIZE,
        chr_rom=bytes(chr_rom),
        mapper_number=0,
    )


def test_cpu_bus_connects_created_mapper_to_ppu_bus():
    """
    Objective:
    CpuBus(cartridge=...) should attach the created mapper to PpuBus too.
    """
    bus = CpuBus(cartridge=make_mapper000_cartridge())

    assert isinstance(bus.mapper, Mapper000)
    assert bus.ppu.ppu_bus.mapper is bus.mapper


def test_ppu_bus_can_read_chr_rom_through_connected_mapper():
    """
    Objective:
    Once connected, PpuBus reads in $0000-$1FFF should use mapper.read_chr.
    """
    bus = CpuBus(cartridge=make_mapper000_cartridge())

    assert bus.ppu.ppu_bus.read(0x0000) == 0x12
    assert bus.ppu.ppu_bus.read(0x1FFF) == 0x34


def test_program_rom_path_does_not_attach_ppu_mapper():
    """
    Objective:
    Old CPU tests using program_rom=FakeROM should not require a cartridge mapper.
    """
    bus = CpuBus(program_rom=FakeROM())

    assert bus.mapper is None
    assert bus.ppu.ppu_bus.mapper is None
