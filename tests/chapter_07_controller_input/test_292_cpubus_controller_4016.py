"""
Route CpuBus $4016 reads/writes to controller port 1.

File to update:
    emulator/bus/cpu_bus.py

Why this step exists:
The previous controller steps created a pure Controller object. Now the CPU bus
must expose that controller through the NES memory-mapped controller port:

    $4016 = controller port 1

Normal NES polling sequence:

    write 1 to $4016
    write 0 to $4016
    read $4016 eight times

Those eight reads return:

    A, B, Select, Start, Up, Down, Left, Right

References:
    https://www.nesdev.org/wiki/Standard_controller
    https://www.nesdev.org/wiki/Controller_reading_code

Suggested implementation example:

    from emulator.input.controller import Controller


    @dataclass
    class CpuBus:
        ...
        controller_1: Controller = field(default_factory=Controller)

        def read(self, addr: int) -> int:
            ...

            # Controller port 1
            if addr == 0x4016:
                return self.controller_1.read_bit()

            # Controller port 2 / expansion input is out of scope for now.
            if addr == 0x4017:
                return 0

            ...

        def write(self, addr: int, value: int) -> None:
            ...

            # Controller port 1 strobe
            if addr == 0x4016:
                self.controller_1.write_strobe(value)
                return

            # $4017 writes are APU frame-counter writes, no-op for now.
            if addr == 0x4017:
                return

            ...

Important distinction:
    $4016 read/write belongs to controller port 1.
    $4017 read is controller port 2 / expansion input, out of scope for now.
    $4017 write is APU frame counter, out of scope for now.

Common misconception:
    "Controller input should be handled by pygame directly in CpuBus."

No. CpuBus should only talk to the pure Controller object. Pygame keyboard mapping
will later update Controller button booleans from a manual/frontend entry point.

Out of scope:
    - pygame keyboard mapping
    - controller port 2 implementation
    - Famicom expansion controllers
    - DMC/controller read glitch behavior
    - open bus upper-bit behavior
"""

from pathlib import Path

from emulator.bus.cpu_bus import CpuBus
from emulator.input.controller import Controller
from emulator.memory.fake_rom import FakeROM


def test_cpubus_has_controller_1_by_default():
    """
    Objective:
    CpuBus owns a controller port 1 device by default.

    This lets CPU code poll $4016 without manually wiring a controller for every
    basic console/bus setup.
    """
    bus = CpuBus(program_rom=FakeROM())

    assert hasattr(bus, "controller_1")
    assert isinstance(bus.controller_1, Controller)


def test_cpubus_4016_write_controls_controller_strobe():
    """
    Objective:
    CPU writes to $4016 should control controller port 1 strobe.
    """
    bus = CpuBus(program_rom=FakeROM())

    bus.write(0x4016, 0x01)

    assert bus.controller_1.strobe is True

    bus.write(0x4016, 0x00)

    assert bus.controller_1.strobe is False


def test_cpubus_4016_write_uses_only_bit_0_for_strobe():
    """
    Objective:
    The controller strobe signal is controlled by bit 0 of the value written to
    $4016. Higher bits should not matter.
    """
    bus = CpuBus(program_rom=FakeROM())

    bus.write(0x4016, 0xFE)
    assert bus.controller_1.strobe is False

    bus.write(0x4016, 0xFF)
    assert bus.controller_1.strobe is True


def test_cpubus_4016_read_returns_controller_serial_bits():
    """
    Objective:
    CPU reads from $4016 should return one controller bit at a time in NES order:

        A, B, Select, Start, Up, Down, Left, Right
    """
    bus = CpuBus(program_rom=FakeROM())
    bus.controller_1.a = True
    bus.controller_1.select = True
    bus.controller_1.down = True
    bus.controller_1.right = True

    bus.write(0x4016, 0x01)
    bus.write(0x4016, 0x00)

    assert [bus.read(0x4016) for _ in range(8)] == [1, 0, 1, 0, 0, 1, 0, 1]


def test_cpubus_4016_polling_sequence_captures_snapshot_on_strobe():
    """
    Objective:
    The common polling sequence captures a stable button snapshot.

    If a button changes after strobe goes low, the current captured sequence should
    not change until the next strobe capture.
    """
    bus = CpuBus(program_rom=FakeROM())
    bus.controller_1.a = True

    bus.write(0x4016, 0x01)
    bus.write(0x4016, 0x00)

    bus.controller_1.a = False

    assert bus.read(0x4016) == 1


def test_cpubus_4016_strobe_high_keeps_returning_live_a_button():
    """
    Objective:
    While strobe is high, controller reads keep recapturing current state and
    return the A button bit repeatedly.
    """
    bus = CpuBus(program_rom=FakeROM())
    bus.controller_1.a = True

    bus.write(0x4016, 0x01)

    assert [bus.read(0x4016) for _ in range(3)] == [1, 1, 1]

    bus.controller_1.a = False

    assert bus.read(0x4016) == 0


def test_cpubus_4017_remains_simplified_out_of_scope():
    """
    Objective:
    Adding controller port 1 must not accidentally turn $4017 into a partial fake
    controller port 2 implementation.

    For now:
        read $4017  -> 0, meaning controller port 2 / expansion input out of scope
        write $4017 -> no-op APU frame-counter behavior out of scope
    """
    bus = CpuBus(program_rom=FakeROM())

    bus.write(0x4017, 0xFF)

    assert bus.read(0x4017) == 0


def test_cpubus_controller_routing_does_not_break_oamdma_or_apu_noop():
    """
    Objective:
    $4016 controller routing must coexist with the nearby I/O behavior introduced
    in the ROM startup preparation chapter.
    """
    bus = CpuBus(program_rom=FakeROM())

    # APU/audio no-op still works.
    bus.write(0x4000, 0x12)
    assert bus.read(0x4000) == 0

    # OAMDMA still works.
    for offset in range(256):
        bus.write(0x0200 + offset, offset)

    bus.write(0x4014, 0x02)

    assert list(bus.ppu.oam) == list(range(256))


def test_cpubus_controller_routing_keeps_pygame_out_of_emulator_core():
    """
    Objective:
    CpuBus should route to the pure Controller object. It should not import pygame
    or know about keyboard events.
    """
    core_files = [
        Path("emulator/bus/cpu_bus.py"),
        Path("emulator/input/controller.py"),
    ]

    for file_path in core_files:
        assert "import pygame" not in file_path.read_text()
