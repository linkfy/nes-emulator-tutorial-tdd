"""
Add explicit APU/audio no-op register behavior on CpuBus.

File to update:
    emulator/bus/cpu_bus.py

Why this step exists:
Real NES ROMs commonly touch APU/audio registers during startup. Audio is outside
this tutorial's current scope, but crashing on every audio register access makes
manual ROM experiments stop before we can observe CPU/PPU/controller behavior.

This step teaches an intentional no-op:

    recognized address + documented out-of-scope behavior

not a broad fake hardware implementation.

What is the APU?
The APU, or Audio Processing Unit, is the NES hardware block responsible for sound
generation. The CPU controls it through memory-mapped registers.

Minimal example:

    CPU writes $4000
        real NES: configure pulse channel audio
        this tutorial for now: accept the write and produce no sound

Common misconception:

    "If the emulator accepts APU writes, APU is implemented."

No. In this step, APU/audio is explicitly recognized as out of scope. The emulator
only avoids crashing on those addresses.

Suggested implementation example:

    def read(self, addr: int) -> int:
        ...

        # APU/audio registers are intentionally out of scope.
        if 0x4000 <= addr <= 0x4013:
            return 0
        if addr == 0x4015:
            return 0

        # Controller port 2 / expansion input is also out of scope for now.
        # Returning 0 means "no controller-2 buttons pressed" in this simplified model.
        if addr == 0x4017:
            return 0

        ...

    def write(self, addr: int, value: int) -> None:
        ...

        # APU/audio registers are intentionally out of scope.
        if 0x4000 <= addr <= 0x4013:
            return
        if addr == 0x4015:
            return

        # $4017 writes control the APU frame counter on the NES.
        # Audio/APU timing is intentionally out of scope, so this is a no-op.
        if addr == 0x4017:
            return

        ...

Why these addresses:

    $4000-$4013
        APU sound-channel registers

    $4015
        APU status/control register

    $4017
        Writes: APU frame counter register, intentionally no-op for now.
        Reads: controller port 2 / expansion input, intentionally returns 0 for now.

Important exclusions:

    $4014 is OAMDMA, not audio.
        Writing $02 to $4014 should later copy CPU $0200-$02FF into PPU OAM.
        Do not swallow it as an APU no-op.

    $4016 is controller port 1, not audio.
        It will be implemented intentionally in the controller chapter.
        Do not fake it by returning 0 here.

Out of scope:
    - actual sound generation
    - APU timers/envelopes/sweep/length counters
    - IRQ/frame-counter timing
    - OAMDMA $4014
    - controller $4016
    - controller port 2 / expansion input reads from $4017
    - broad catch-all handling for all unsupported I/O addresses
"""

import pytest

from emulator.bus.cpu_bus import CpuBus
from emulator.memory.fake_rom import FakeROM


def test_apu_audio_register_writes_are_explicit_noops():
    """
    Objective:
    Writes to the current out-of-scope APU/audio register set should be accepted
    without raising.

    This keeps real-ROM startup experiments from failing only because the ROM
    initializes audio.
    """
    bus = CpuBus(program_rom=FakeROM())

    for addr in [0x4000, 0x4001, 0x400F, 0x4013, 0x4015, 0x4017]:
        bus.write(addr, 0xAB)


def test_apu_audio_register_reads_return_deterministic_zero():
    """
    Objective:
    Reads from out-of-scope APU/audio/controller-2-adjacent registers return a
    deterministic value.

    Returning 0 is intentionally simple. For $4017 reads, it means controller port 2
    is currently modeled as "no buttons pressed" rather than fully implemented.
    """
    bus = CpuBus(program_rom=FakeROM())

    for addr in [0x4000, 0x4001, 0x400F, 0x4013, 0x4015, 0x4017]:
        assert bus.read(addr) == 0


def test_oamdma_4014_is_not_swallowed_by_apu_noop():
    """
    Objective:
    $4014 belongs to OAMDMA, not APU/audio.

    After the OAMDMA step exists, writes to $4014 should perform the DMA copy.
    The important invariant from this APU/audio step is that $4014 is not treated
    as an audio no-op.

    Reads from $4014 remain unsupported because OAMDMA is a write-triggered
    register in this tutorial.
    """
    bus = CpuBus(program_rom=FakeROM())

    for offset in range(256):
        bus.write(0x0200 + offset, offset)

    bus.write(0x4014, 0x02)

    assert list(bus.ppu.oam) == list(range(256))

    with pytest.raises(ValueError, match="Unsupported CPU bus read: 4014"):
        bus.read(0x4014)


def test_unknown_io_address_still_raises_instead_of_catch_all_noop():
    """
    Objective:
    The no-op must be explicit, not a broad catch-all for every unsupported I/O
    address.

    This keeps missing hardware visible during debugging.
    """
    bus = CpuBus(program_rom=FakeROM())

    with pytest.raises(ValueError, match="Unsupported CPU bus write: 4020"):
        bus.write(0x4020, 0x55)

    with pytest.raises(ValueError, match="Unsupported CPU bus read: 4020"):
        bus.read(0x4020)


def test_existing_ram_routing_still_works_after_apu_noop_step():
    """
    Objective:
    Adding APU/audio no-op handling must not disturb existing RAM routing.
    """
    bus = CpuBus(program_rom=FakeROM())

    bus.write(0x0002, 0x44)

    assert bus.read(0x0002) == 0x44
    assert bus.read(0x0802) == 0x44  # internal RAM mirror


def test_existing_ppu_register_routing_still_works_after_apu_noop_step():
    """
    Objective:
    Adding APU/audio no-op handling must not disturb PPU register routing.
    """
    bus = CpuBus(program_rom=FakeROM())

    bus.write(0x2000, 0x80)

    assert bus.ppu.ctrl == 0x80


def test_existing_prg_rom_routing_still_works_after_apu_noop_step():
    """
    Objective:
    Adding APU/audio no-op handling must not disturb test PRG ROM routing.
    """
    rom = FakeROM()
    rom.write(0x0000, 0xEA)
    bus = CpuBus(program_rom=rom)

    assert bus.read(0x8000) == 0xEA
