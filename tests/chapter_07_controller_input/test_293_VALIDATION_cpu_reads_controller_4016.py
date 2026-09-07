"""
VALIDATION TEST: CPU program reads controller bits from $4016.

This is not a student implementation step.

There is nothing new to build in this file. This test validates that already-built
pieces work together:

    CPU instructions
        -> CpuBus.write($4016, value)
        -> Controller.write_strobe(value)
        -> CpuBus.read($4016)
        -> Controller.read_bit()
        -> CPU stores observed bits into RAM

Why this validation exists:
The previous tests proved the Controller object and CpuBus $4016 routing in
isolation. This test proves that a real CPU instruction sequence can use that path.

References:
    https://www.nesdev.org/wiki/Standard_controller
    https://www.nesdev.org/wiki/Controller_reading_code

NES controller polling shape:

    write 1 to $4016
    write 0 to $4016
    read $4016 eight times

The eight reads return:

    A, B, Select, Start, Up, Down, Left, Right

Tiny program used here:

    LDA #$01
    STA $4016     ; strobe high, capture live buttons

    LDA #$00
    STA $4016     ; strobe low, serial reads advance

    LDA $4016
    STA $0000     ; A bit

    LDA $4016
    STA $0001     ; B bit

    ... repeated through Right bit ...

Important distinction:
This validation stores each serial bit in a separate RAM byte for readability. Many
NES assembly examples shift the bits into one result byte. That is game-code
policy, not controller hardware behavior.

Out of scope:
    - pygame keyboard mapping
    - main.py loop
    - controller port 2
    - Famicom expansion controllers
    - DMC/controller read glitch behavior
    - commercial ROM fixtures
"""

from emulator.cpu.cpu import CPU
from emulator.bus.cpu_bus import CpuBus
from emulator.memory.fake_rom import FakeROM
from tests.helpers import load_program, write_reset_vector


def build_controller_poll_program() -> list[int]:
    """
    Build a tiny CPU program that polls controller port 1 and stores the eight
    serial read bits into RAM $0000-$0007.
    """
    program = [
        0xA9, 0x01,        # LDA #$01
        0x8D, 0x16, 0x40,  # STA $4016
        0xA9, 0x00,        # LDA #$00
        0x8D, 0x16, 0x40,  # STA $4016
    ]

    for ram_addr in range(0x0000, 0x0008):
        program.extend(
            [
                0xAD, 0x16, 0x40,        # LDA $4016
                0x8D, ram_addr, 0x00,    # STA $00xx
            ]
        )

    return program


def make_cpu_for_controller_validation() -> tuple[CPU, CpuBus]:
    """Create a CPU with a FakeROM containing the controller polling program."""
    rom = FakeROM()
    load_program(rom, 0x8000, build_controller_poll_program())
    write_reset_vector(rom, 0x8000)

    bus = CpuBus(program_rom=rom)
    cpu = CPU(bus)

    return cpu, bus


def test_VALIDATION_cpu_program_reads_controller_bits_from_4016_into_ram():
    """
    Validation objective:
    Prove CPU instructions can read controller port 1 through $4016.

    Pressed buttons:
        A, Select, Down, Right

    Expected serial bits:
        A      -> 1
        B      -> 0
        Select -> 1
        Start  -> 0
        Up     -> 0
        Down   -> 1
        Left   -> 0
        Right  -> 1
    """
    cpu, bus = make_cpu_for_controller_validation()
    bus.controller_1.a = True
    bus.controller_1.select = True
    bus.controller_1.down = True
    bus.controller_1.right = True

    cpu.reset()

    # 4 setup instructions + 8 * 2 instructions for LDA $4016 / STA RAM.
    for _ in range(20):
        cpu.step()

    assert [bus.read(addr) for addr in range(0x0000, 0x0008)] == [
        1,  # A
        0,  # B
        1,  # Select
        0,  # Start
        0,  # Up
        1,  # Down
        0,  # Left
        1,  # Right
    ]


def test_VALIDATION_cpu_controller_poll_uses_captured_snapshot():
    """
    Validation objective:
    Prove the CPU polling sequence captures a stable snapshot when strobe moves
    from high to low.

    The test changes live button state after the strobe sequence but before the CPU
    reads all stored values. The already-captured serial sequence should still
    reflect the buttons that were active during strobe.
    """
    cpu, bus = make_cpu_for_controller_validation()
    bus.controller_1.a = True
    bus.controller_1.right = True

    cpu.reset()

    # Execute only the strobe sequence:
    # LDA #$01, STA $4016, LDA #$00, STA $4016
    for _ in range(4):
        cpu.step()

    # Change live state after capture. Serial reads should still use captured data.
    bus.controller_1.a = False
    bus.controller_1.right = False

    # Execute the 8 LDA/STA read/store pairs.
    for _ in range(16):
        cpu.step()

    assert [bus.read(addr) for addr in range(0x0000, 0x0008)] == [
        1,  # A was captured as pressed
        0,
        0,
        0,
        0,
        0,
        0,
        1,  # Right was captured as pressed
    ]
