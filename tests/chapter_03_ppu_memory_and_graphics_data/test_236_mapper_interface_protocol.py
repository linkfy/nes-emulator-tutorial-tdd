"""
Create MapperInterface as a protocol for bus/mapper boundaries.

File to create:
    emulator/cartridge/mapper_interface.py

Protocol to implement:
    MapperInterface

Why this helper exists:
PpuBus should not depend on Mapper000 directly. Mapper000 is only one cartridge
mapper. Later mappers may bank-switch PRG/CHR differently, but PpuBus should only
need a small interface:

    read_prg(addr)
    read_chr(addr)

This keeps PpuBus mapper-aware without making it Mapper000-specific.

What is a Protocol?
A Protocol describes the methods an object must provide. A class does not need
to inherit from the Protocol explicitly. If it has the right methods, it matches
the protocol structurally.

Suggested implementation pseudocode:

    from typing import Protocol


    class MapperInterface(Protocol):
        def read_prg(self, addr: int) -> int:
            ...

        def read_chr(self, addr: int) -> int:
            ...

Future note:
When CHR RAM writes are implemented, this protocol may grow:

    write_chr(addr, value)

Do not require it yet, because Mapper000 does not implement CHR writes at this
stage.
"""

from pathlib import Path
from emulator.cartridge.mapper_interface import MapperInterface


def test_mapper_interface_file_exists():
    """
    Objective:
    Create emulator/cartridge/mapper_interface.py.
    """
    assert Path("emulator/cartridge/mapper_interface.py").exists()


def test_mapper_interface_is_protocol_with_required_methods():
    """
    Objective:
    Define the small mapper surface area needed by CpuBus/PpuBus.
    """
    assert getattr(MapperInterface, "_is_protocol", False) is True
    assert hasattr(MapperInterface, "read_prg")
    assert hasattr(MapperInterface, "read_chr")


def test_structural_mapper_can_be_used_without_inheriting_protocol():
    """
    Objective:
    Show why Protocol is useful: a mapper only needs matching methods.
    """

    class ExampleMapper:
        def read_prg(self, addr: int) -> int:
            return 0xEA

        def read_chr(self, addr: int) -> int:
            return 0x12

    mapper: MapperInterface = ExampleMapper()

    assert mapper.read_prg(0x8000) == 0xEA
    assert mapper.read_chr(0x0000) == 0x12
