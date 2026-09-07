"""
Create a simple VRAM memory device.

File to create:
    emulator/memory/vram.py

Class to implement:
    VRAM

Why this step exists:
The PPU has its own address space, separate from the CPU address space. CPU RAM
is not where background/sprite graphics state normally lives. The PPU needs
video-facing memory that it can access through PPUADDR/PPUDATA and, later,
through rendering logic.

Important mental model:

    CPU address space: $0000-$FFFF
        handled by CpuBus

    PPU address space: $0000-$3FFF
        will be handled by PpuBus

For this early step, VRAM is a simple writable backing store for the PPU-side
address space. Later, PpuBus will decide how PPU addresses map to CHR ROM,
nametable VRAM, palette RAM, and mirrors.

Why VRAM is separate from PPU registers:
PPU registers such as $2006 and $2007 are CPU-visible control/data ports. They
are not the memory itself.

Example flow later:

    CPU writes $20 to $2006
    CPU writes $00 to $2006
    CPU writes $AA to $2007

Meaning:

    PPU internal address becomes $2000
    PPUDATA writes $AA into PPU-side memory at $2000

The CPU touches register $2007, but the actual video memory address is the PPU's
internal address, not CPU address $2007.

Current scope:
    - VRAM is a MemoryDevice
    - VRAM stores 0x4000 bytes
    - VRAM.read(addr) returns stored byte at addr
    - VRAM.write(addr, value) stores only the low byte of value

Important responsibility split:
VRAM should not apply addr & 0x3FFF. Address normalization/routing belongs to
PpuBus, because PpuBus owns the PPU address map. VRAM is only storage.

Suggested implementation pseudocode:

    from dataclasses import dataclass, field
    from emulator.memory.memory_device import MemoryDevice

    VRAM_SIZE = 0x4000


    @dataclass
    class VRAM(MemoryDevice):
        _data: bytearray = field(
            default_factory=lambda: bytearray(VRAM_SIZE),
            init=False,
        )

        def write(self, addr: int, value: int) -> None:
            self._data[addr] = value & 0xFF

        def read(self, addr: int) -> int:
            return self._data[addr]

Out of scope:
    - PpuBus routing
    - CHR ROM mapping
    - nametable mirroring
    - palette RAM
    - rendering
"""

import dataclasses
from pathlib import Path

from emulator.memory.memory_device import MemoryDevice
from emulator.memory.vram import VRAM, VRAM_SIZE


def test_vram_file_exists():
    """
    Objective:
    Create emulator/memory/vram.py.
    """
    assert Path("emulator/memory/vram.py").exists()


def test_vram_is_memory_device_with_expected_size():
    """
    Objective:
    VRAM should be a MemoryDevice with a 0x4000-byte backing store.

    Why 0x4000:
    The PPU address space is 14-bit: $0000-$3FFF.
    """
    assert VRAM_SIZE == 0x4000
    assert dataclasses.is_dataclass(VRAM)
    assert issubclass(VRAM, MemoryDevice)

    vram = VRAM()

    assert len(vram._data) == VRAM_SIZE


def test_vram_can_store_and_read_bytes():
    """
    Objective:
    VRAM should store values by address and return them later.
    """
    vram = VRAM()

    vram.write(0x2000, 0xAA)

    assert vram.read(0x2000) == 0xAA


def test_vram_write_stores_only_low_byte():
    """
    Objective:
    VRAM stores bytes, so writes keep only the low 8 bits.

    Example:
    0x123 becomes 0x23.
    """
    vram = VRAM()

    vram.write(0x0000, 0x123)

    assert vram.read(0x0000) == 0x23


def test_vram_does_not_hide_address_routing_rules():
    """
    Objective:
    VRAM should behave like simple storage, not like the final PPU memory map.

    Why:
    PPU address normalization, mirroring, and routing belong to PpuBus. Keeping
    VRAM simple prevents hidden address-map behavior from leaking into storage.

    This test intentionally writes and reads a direct in-range address only.
    """
    vram = VRAM()

    vram.write(VRAM_SIZE - 1, 0x77)

    assert vram.read(VRAM_SIZE - 1) == 0x77
