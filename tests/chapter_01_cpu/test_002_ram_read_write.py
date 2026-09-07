"""
Test 002 — Implement raw 2 KiB RAM storage.

File to update:
    emulator/memory/ram.py

Location:
    class RAM

Why this step exists:
The NES contains 2 KiB of internal CPU RAM. This class owns only physical byte
storage; the CPU bus will introduce address mirroring in the next lesson.

Complete example implementation:

    from dataclasses import dataclass, field


    @dataclass
    class RAM:
        _data: bytearray = field(
            default_factory=lambda: bytearray(0x800),
            init=False,
        )

        def write(self, addr: int, value: int) -> None:
            self._data[addr] = value

        def read(self, addr: int) -> int:
            return self._data[addr]

Important invariants:
    - storage contains exactly 0x800 bytes
    - a write changes the byte read from the same physical address
    - RAM does not translate or mirror CPU addresses

Common misconception:
RAM does not need to understand addresses $0800, $1000, or $1800. Those are CPU bus
aliases of physical RAM and belong to the mapping mechanism introduced in Test 003.

Out of scope:
    - a shared memory-device interface
    - ROM storage
    - CPU bus routing
"""

from emulator.memory.ram import RAM

def test_ram_class_exists():
    assert RAM is not None

def test_create_ram_instance():
    ram = RAM()

    assert isinstance(ram, RAM)

def test_ram_has_2kb_capacity():
    ram = RAM()

    assert len(ram._data) == 2048


def test_write_read_ram():
    ram = RAM()

    for i in range(0x0, 0x800):
        test_value = i & 0xFF

        ram.write(i, test_value)

        assert ram.read(i) == test_value
