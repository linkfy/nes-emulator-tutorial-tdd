"""
Test 005 — Introduce the common memory-device interface.

File to create:
    emulator/memory/memory_device.py

File to update:
    emulator/memory/ram.py

Locations:
    class MemoryDevice
    class RAM(MemoryDevice)

Why this step exists:
CpuBus will soon route accesses to different devices. A small abstract interface lets
the bus depend on read/write behavior instead of the concrete RAM representation.

Complete example implementation:

    # emulator/memory/memory_device.py
    from abc import ABC, abstractmethod


    class MemoryDevice(ABC):
        @abstractmethod
        def read(self, addr: int) -> int:
            ...

        @abstractmethod
        def write(self, addr: int, value: int) -> None:
            ...


    # emulator/memory/ram.py
    from dataclasses import dataclass, field

    from emulator.memory.memory_device import MemoryDevice


    @dataclass
    class RAM(MemoryDevice):
        _data: bytearray = field(
            default_factory=lambda: bytearray(0x800),
            init=False,
        )

        def read(self, addr: int) -> int:
            return self._data[addr]

        def write(self, addr: int, value: int) -> None:
            self._data[addr] = value

Important invariant:
MemoryDevice defines the operations but does not own storage or address mapping.

Common misconception:
An abstract base class does not make RAM contents abstract. RAM still owns concrete
byte storage; only its callable boundary is shared.

Out of scope:
    - FakeROM, introduced in Test 006
    - program-ROM bus mapping
    - read-only cartridge behavior
"""

from inspect import signature
from pathlib import Path

from emulator.memory.ram import RAM

def test_memory_abstract_class_exists():
    assert Path("emulator/memory/memory_device.py").exists()

def test_memory_device_has_read_write_methods():
    """You should create a Memory Device abstract class with read and write methods"""

    from emulator.memory.memory_device import MemoryDevice
    abstract_methods = MemoryDevice.__abstractmethods__

    assert "read" in abstract_methods
    assert "write" in abstract_methods

def test_memory_read_has_corrrect_parameters():
    """Read should have:
        read(self, addr:int)
    """
    
    from emulator.memory.memory_device import MemoryDevice
    params = signature(MemoryDevice.read).parameters
    assert "self" in params
    assert "addr" in params
    assert len(params) == 2

def test_memory_write_has_corrrect_parameters():
    """Write should have:
        write(self, addr:int, value:int)
    """
 
    from emulator.memory.memory_device import MemoryDevice
    params = signature(MemoryDevice.write).parameters
    assert "self" in params
    assert "addr" in params
    assert "value" in params 
    assert len(params) == 3

def test_ram_uses_memory_device_abstract_class():
    """
    Now our ram should use the new abstract class Memory Device
    """

    from emulator.memory.memory_device import MemoryDevice
    ram = RAM()
    assert isinstance(ram, MemoryDevice)
