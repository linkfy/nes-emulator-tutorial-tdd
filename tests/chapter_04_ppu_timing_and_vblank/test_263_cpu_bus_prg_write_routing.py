"""
Route CPU PRG-space writes through the mapper before CPU NMI tests.

Files to update:
    emulator/cartridge/mapper_interface.py
    emulator/cartridge/mapper000.py
    emulator/bus/cpu_bus.py

Why this step exists:
The next CPU interrupt test will need to place the NMI vector bytes at:

    $FFFA = NMI vector low byte
    $FFFB = NMI vector high byte

Those addresses live inside the CPU PRG area:

    $8000-$FFFF

Before testing CPU.interrupt_nmi(), we need the CPU bus write behavior in that
range to be explicit and safe.

What is PRG write routing?
PRG write routing means CpuBus does not mutate cartridge ROM bytes directly.
Instead, writes in $8000-$FFFF are forwarded to the cartridge mapper:

    CpuBus.write($8000-$FFFF, value)
        -> mapper.write_prg(addr, value)

Minimal example:

    CPU writes $8000 = $12
    CpuBus calls mapper.write_prg($8000, $12)
    Mapper000/NROM ignores it because it has no PRG write registers
    Later mappers may treat the same write as a bank-switch command

Common misconception:
Writing to $8000 does not mean the CPU changes ROM bytes. On real cartridges,
writes in this range are usually ignored by simple boards or interpreted as
mapper control signals by more advanced boards.

Important split:

    Real cartridge path:
        CpuBus.write($8000-$FFFF) -> mapper.write_prg(...)

    Tutorial FakeROM path:
        CpuBus.write($8000-$FFFF) -> FakeROM.write(addr - $8000, value)

The FakeROM path is only a test setup convenience. It lets upcoming interrupt
tests install vector bytes at $FFFA/$FFFB without making real Mapper000 PRG ROM
writable.

Suggested implementation examples:

    class MapperInterface(Protocol):
        def read_prg(self, addr: int) -> int:
            ...

        def write_prg(self, addr: int, value: int) -> None:
            ...

        def read_chr(self, addr: int) -> int:
            ...

        def write_chr(self, addr: int, value: int) -> None:
            ...

    class Mapper000:
        def write_prg(self, addr: int, value: int) -> None:
            if not (PRG_ROM_START <= addr <= PRG_ROM_END):
                raise ValueError(f"Address out of PRG ROM range: {addr:04X}")

            # Mapper000/NROM has no writable PRG registers.
            # Real hardware ignores writes to PRG ROM space, so we ignore them too.
            return

    class CpuBus:
        def write(self, addr: int, value: int) -> None:
            ...

            if 0x8000 <= addr <= 0xFFFF:
                if self.mapper is not None:
                    self.mapper.write_prg(addr, value)
                    return

                if self.program_rom is not None:
                    self.program_rom.write(addr - 0x8000, value)
                    return

            raise ValueError(f"Unsupported CPU bus write: {addr:04X}")

Out of scope:
    - CPU.interrupt_nmi() behavior
    - PPU requesting NMI consumption by the CPU
    - Mapper001/MMC bank switching
    - Making real PRG ROM writable
"""

from emulator.bus.cpu_bus import CpuBus
from emulator.cartridge.mapper000 import (
    CHR_ROM_SIZE,
    Mapper000,
    NROM_128_SIZE,
    NROM_256_SIZE,
)
from emulator.cartridge.mapper_interface import MapperInterface
from emulator.memory.fake_rom import FakeROM


class FakeMapperForPrgWrites:
    """Small test double that records PRG write calls from CpuBus."""

    def __init__(self):
        self.write_prg_calls = []

    def read_prg(self, addr: int) -> int:
        raise AssertionError("read_prg is not used by this test")

    def write_prg(self, addr: int, value: int) -> None:
        self.write_prg_calls.append((addr, value))

    def read_chr(self, addr: int) -> int:
        raise AssertionError("read_chr is not used by this test")

    def write_chr(self, addr: int, value: int) -> None:
        raise AssertionError("write_chr is not used by this test")


def make_mapper000(prg_rom: bytes | None = None) -> Mapper000:
    """Create a minimal official Mapper000-style mapper."""
    if prg_rom is None:
        prg_rom = bytes([0xEA]) * NROM_256_SIZE

    return Mapper000(
        prg_rom=prg_rom,
        chr_rom=bytes([0x00]) * CHR_ROM_SIZE,
    )


def test_mapper_interface_requires_write_prg_method():
    """
    Objective:
    Mappers expose write_prg so CpuBus can delegate writes in $8000-$FFFF.
    """
    assert hasattr(MapperInterface, "write_prg")

    mapper = make_mapper000()

    assert hasattr(mapper, "write_prg")
    assert callable(mapper.write_prg)


def test_mapper000_ignores_valid_prg_writes_without_changing_prg_data():
    """
    Objective:
    Official Mapper000/NROM has PRG ROM, not PRG RAM or PRG write registers.
    Valid writes in $8000-$FFFF are ignored for real-ROM compatibility.

    Example:
        STA $8000 should not mutate the byte returned by read_prg($8000).
    """
    prg_rom = bytes([0xAA]) + bytes([0x00]) * (NROM_256_SIZE - 1)
    mapper = make_mapper000(prg_rom=prg_rom)

    before = mapper.read_prg(0x8000)

    mapper.write_prg(0x8000, 0x12)

    after = mapper.read_prg(0x8000)
    assert before == 0xAA
    assert after == 0xAA


def test_mapper000_valid_prg_write_to_mirrored_16kb_rom_is_also_ignored():
    """
    Objective:
    The ignore rule applies to the whole PRG address range, including the mirrored
    upper bank in NROM-128.

    Example:
        With 16KB PRG ROM, $C000 mirrors $8000. A write to $C000 still must not
        mutate the underlying PRG ROM byte.
    """
    prg_rom = bytes([0x55]) + bytes([0x00]) * (NROM_128_SIZE - 1)
    mapper = make_mapper000(prg_rom=prg_rom)

    mapper.write_prg(0xC000, 0x99)

    assert mapper.read_prg(0x8000) == 0x55
    assert mapper.read_prg(0xC000) == 0x55


def test_mapper000_rejects_prg_writes_outside_prg_range_with_range_error():
    """
    Objective:
    Mapper000 ignores valid PRG-space writes, but it should still reject addresses
    outside $8000-$FFFF because those addresses do not belong to Mapper000 PRG.
    """
    mapper = make_mapper000()

    try:
        mapper.write_prg(0x7FFF, 0x12)
    except ValueError as error:
        assert "Address out of PRG ROM range" in str(error)
    else:
        raise AssertionError("Expected Mapper000.write_prg to reject address $7FFF")


def test_cpu_bus_delegates_prg_space_writes_to_mapper_when_mapper_exists():
    """
    Objective:
    CpuBus should route $8000-$FFFF writes to mapper.write_prg when a mapper is
    attached.

    This keeps future mapper behavior possible:
        Mapper000: ignore valid PRG writes
        MMC1/MMC3: use PRG writes as bank-switch or IRQ control signals
    """
    mapper = FakeMapperForPrgWrites()
    bus = CpuBus()
    bus.mapper = mapper

    bus.write(0x8000, 0x12)
    bus.write(0xFFFA, 0x34)
    bus.write(0xFFFF, 0x56)

    assert mapper.write_prg_calls == [
        (0x8000, 0x12),
        (0xFFFA, 0x34),
        (0xFFFF, 0x56),
    ]


def test_cpu_bus_fake_rom_path_can_prepare_nmi_vector_bytes():
    """
    Objective:
    In the tutorial FakeROM path, CpuBus.write can prepare bytes in $8000-$FFFF.
    This is needed before CPU.interrupt_nmi() tests.

    Example:
        CPU interrupt code reads the NMI vector from $FFFA/$FFFB.
        This test setup writes those vector bytes through CpuBus using FakeROM.

    Address translation:
        $FFFA on CPU bus -> FakeROM offset $7FFA
        $FFFB on CPU bus -> FakeROM offset $7FFB
    """
    rom = FakeROM()
    bus = CpuBus(program_rom=rom)

    bus.write(0xFFFA, 0x34)
    bus.write(0xFFFB, 0x12)

    assert bus.read(0xFFFA) == 0x34
    assert bus.read(0xFFFB) == 0x12
    assert rom.read(0x7FFA) == 0x34
    assert rom.read(0x7FFB) == 0x12


def test_cpu_bus_uses_mapper_in_preference_to_fake_rom_when_mapper_exists():
    """
    Objective:
    If a mapper is attached, PRG-space writes belong to the mapper path. This
    protects real cartridge behavior from accidentally becoming FakeROM behavior.
    """
    rom = FakeROM()
    mapper = FakeMapperForPrgWrites()
    bus = CpuBus(program_rom=rom)
    bus.mapper = mapper

    bus.write(0x8000, 0xAB)

    assert mapper.write_prg_calls == [(0x8000, 0xAB)]
    assert rom.read(0x0000) == 0x00
