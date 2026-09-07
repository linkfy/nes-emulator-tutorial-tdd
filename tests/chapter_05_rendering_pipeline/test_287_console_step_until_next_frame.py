"""
Add Console.step_until_next_frame() for frame-level stepping.

File to update:
    emulator/console.py

Why this step exists:
Console already has a one-instruction stepping method:

    console.step()

That is the smallest machine-time operation in this emulator. It executes one CPU
instruction, advances the PPU by CPU cycles * 3, then consumes any pending NMI.

Manual runners and future frontends usually need a larger operation:

    run emulation until one full PPU frame completes
    then ask for a framebuffer explicitly

This step adds:

    console.step_until_next_frame(max_cpu_instructions: int | None = None) -> int

Example implementation:

    def step_until_next_frame(
        self,
        max_cpu_instructions: int | None = None,
    ) -> int:
        start_frame = self.ppu.frame
        executed = 0

        while self.ppu.frame == start_frame:
            if max_cpu_instructions is not None:
                if executed >= max_cpu_instructions:
                    raise RuntimeError("Frame did not complete before instruction limit")

            self.step()
            executed += 1

        return executed

Difference between step() and step_until_next_frame():

    step()
        executes exactly one CPU instruction
        advances PPU by that instruction's cycles * 3
        returns CPU cycles for that instruction

    step_until_next_frame()
        calls step() repeatedly until ppu.frame changes
        returns how many CPU instructions were executed

Example usage:

    console.step_until_next_frame()
    framebuffer = console.render_background_framebuffer()

Why max_cpu_instructions is optional:
This parameter is not NES hardware behavior. It is an emulator debugging/testing
guard.

With None, there is no artificial instruction limit. This is useful for real or
manual execution:

    console.step_until_next_frame()

With an integer, the helper raises if that many CPU instructions execute without a
new frame. This is useful for tests and debugging because it prevents infinite
loops if the CPU gets stuck, an opcode is missing, or a frame never completes:

    console.step_until_next_frame(max_cpu_instructions=10)

Important separation:

    step_until_next_frame()
        advances emulation time

    render_background_framebuffer()
        observes current PPU memory and returns Framebuffer data

Do not render automatically inside step_until_next_frame().

Out of scope:
    - pygame display
    - sprites
    - OAMDMA
    - exact NMI latency
    - dynamic CPU cycle penalties
    - controller input
"""

import pytest

from emulator.bus.cpu_bus import CpuBus
from emulator.console import Console
from emulator.cpu.cpu import CPU
from emulator.memory.fake_rom import FakeROM
from emulator.ppu.ppu import PPU_CYCLES_PER_SCANLINE, PPU_SCANLINES_PER_FRAME
from tests.helpers import load_program


def make_console_with_nop_rom(program_size: int = 0x8000) -> tuple[Console, CPU, FakeROM]:
    """
    Build a Console with FakeROM filled with NOP instructions.

    NOP is useful here because it is implemented, deterministic, and takes 2 CPU
    cycles. Console.step() will therefore advance the PPU by 6 cycles per
    instruction.
    """
    rom = FakeROM()
    load_program(rom, 0x8000, [0xEA] * program_size)
    bus = CpuBus(program_rom=rom)
    cpu = CPU(bus)
    cpu.pc = 0x8000
    return Console(cpu=cpu, ppu=bus.ppu), cpu, rom


def test_console_exposes_step_until_next_frame_method():
    """
    Objective:
    Console exposes a frame-level stepping helper.
    """
    assert hasattr(Console, "step_until_next_frame")
    assert callable(Console.step_until_next_frame)


def test_step_until_next_frame_advances_ppu_frame_counter():
    """
    Objective:
    The helper repeatedly calls Console.step() until the PPU frame changes.
    """
    console, _cpu, _rom = make_console_with_nop_rom()
    assert console.ppu.frame == 0

    executed = console.step_until_next_frame(max_cpu_instructions=20_000)

    assert executed > 0
    assert console.ppu.frame == 1


def test_step_until_next_frame_returns_instruction_count():
    """
    Objective:
    Returning the executed instruction count gives tests and debug logs useful
    evidence about frame progression.

    With NOP:
        2 CPU cycles * 3 = 6 PPU cycles per instruction
    """
    console, _cpu, _rom = make_console_with_nop_rom()

    executed = console.step_until_next_frame(max_cpu_instructions=20_000)

    ppu_cycles_per_frame = PPU_CYCLES_PER_SCANLINE * PPU_SCANLINES_PER_FRAME

    assert executed > 0
    assert executed * 6 >= ppu_cycles_per_frame


def test_step_until_next_frame_raises_when_instruction_limit_is_too_small():
    """
    Objective:
    The optional max_cpu_instructions limit prevents tests/debug runs from hanging
    forever if a frame never completes.
    """
    console, _cpu, _rom = make_console_with_nop_rom()

    with pytest.raises(RuntimeError, match="Frame did not complete before instruction limit"):
        console.step_until_next_frame(max_cpu_instructions=1)


def test_step_until_next_frame_allows_no_limit_when_argument_is_none():
    """
    Objective:
    max_cpu_instructions=None means no artificial limit. This is useful for manual
    runs or future real-ROM loops.

    The test starts the PPU close to frame completion so it finishes quickly.
    """
    console, _cpu, _rom = make_console_with_nop_rom()

    console.ppu.scanline = PPU_SCANLINES_PER_FRAME - 1
    console.ppu.cycle = PPU_CYCLES_PER_SCANLINE - 6

    executed = console.step_until_next_frame()

    assert executed == 1
    assert console.ppu.frame == 1


def test_step_until_next_frame_does_not_render_automatically():
    """
    Objective:
    Frame stepping advances time only. Rendering remains an explicit separate call.

    This protects the boundary:
        step_until_next_frame() -> timing
        render_background_framebuffer() -> observation/rendering
    """
    console, _cpu, _rom = make_console_with_nop_rom()

    def fail_if_render_called():
        raise AssertionError("step_until_next_frame must not render automatically")

    console.render_background_framebuffer = fail_if_render_called

    console.ppu.scanline = PPU_SCANLINES_PER_FRAME - 1
    console.ppu.cycle = PPU_CYCLES_PER_SCANLINE - 6

    executed = console.step_until_next_frame()

    assert executed == 1
    assert console.ppu.frame == 1
