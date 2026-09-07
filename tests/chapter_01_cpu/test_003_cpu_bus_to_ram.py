"""
Test 003 — Route CPU RAM addresses through CpuBus.

File to update:
    emulator/bus/cpu_bus.py

Location:
    class CpuBus

Reference:
    https://www.nesdev.org/wiki/CPU_memory_map

Why this step exists:
The CPU uses a 16-bit address space, while internal RAM contains only 0x800 physical
bytes. Addresses $0000-$1FFF repeat that same RAM four times.

Complete example implementation:

    from dataclasses import dataclass, field

    from emulator.memory.ram import RAM


    @dataclass
    class CpuBus:
        ram: RAM = field(default_factory=RAM)

        def read(self, addr: int) -> int:
            if 0x0000 <= addr <= 0x1FFF:
                return self.ram.read(addr & 0x07FF)

            raise ValueError(f"Unsupported CPU bus read: {addr:04X}")

        def write(self, addr: int, value: int) -> None:
            if 0x0000 <= addr <= 0x1FFF:
                self.ram.write(addr & 0x07FF, value)
                return

            raise ValueError(f"Unsupported CPU bus write: {addr:04X}")

Important invariant:
    physical_ram_address = cpu_address & 0x07FF

Minimal example:
Writing $42 to CPU address $0800 changes physical RAM byte $0000, so reading $0000,
$0800, $1000, or $1800 observes the same storage.

Common misconception:
Mirroring does not allocate four RAM arrays. The bus translates four CPU ranges onto
one RAM device. At this step, unsupported addresses raise ValueError, while bytearray
itself rejects values outside the unsigned 8-bit range.

Out of scope:
    - program ROM routing
    - PPU and controller registers
    - CPU execution
"""
import pytest
from emulator.bus.cpu_bus import CpuBus
from emulator.memory.ram import RAM

def test_cpu_buss_class_exists():
    assert CpuBus is not None

def test_create_ram_instance():
    cpu_bus = CpuBus()

    assert isinstance(cpu_bus, CpuBus)

def test_cpu_bus_contains_ram_instance():
    cpu_bus = CpuBus()

    assert hasattr(cpu_bus, "ram")
    assert isinstance(cpu_bus.ram, RAM)


def test_cpu_bus_reads_and_writes_internal_ram():
    bus = CpuBus()
    bus.write(0x0000, 0x42)

    assert bus.read(0x0000) == 0x42
    
def test_cpu_bus_reads_and_writes_internal_ram_mirrors():
    bus = CpuBus()

    mirrors = [0x800, 0x1000, 0x1800]
    test_addresses = [0x0, 0x1, 0x42, 0x7FF]
    # Write different values in mirror address
    value = 0
    for base_address in mirrors:
        for address in test_addresses:
            bus.write(base_address + address, value & 0xFF)
            assert bus.read(address) == value & 0xFF
            value+=1
    
def test_cpu_bus_rejects_invalid_addresses():
    """Addresses should be unsigned 16 bits"""
    bus = CpuBus()

    invalid_addresses = [
        -1,
        0x10000,
        0x20000,
    ]

    for addr in invalid_addresses:
        with pytest.raises(ValueError):
            bus.write(addr, 0x42)


def test_cpu_bus_rejects_invalid_values():
    """Values should be unsigned 8 bits"""
    bus = CpuBus()

    invalid_values = [
        -1,
        0x100,
        0xFFFF,
    ]

    for value in invalid_values:
        with pytest.raises(ValueError):
            bus.write(0x0000, value)
