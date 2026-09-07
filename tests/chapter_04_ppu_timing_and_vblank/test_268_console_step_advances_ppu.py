"""
Make Console.step() advance PPU time from CPU cycles.

References:
    https://www.nesdev.org/wiki/CPU
    https://www.nesdev.org/wiki/PPU_rendering#Line-by-line_timing

File to update:
    emulator/console.py

Why this step exists:
The emulator now has the pieces needed to connect CPU time to PPU time:

    CPU.step() returns base CPU cycles
    PPU.step(cycles) advances PPU timing counters
    Console.consume_nmi_if_requested() connects PPU NMI requests to CPU NMI

Console.step() is where those pieces become one machine-level step.

What is machine-level stepping?
Machine-level stepping means advancing multiple emulated chips together according
to their clock relationship.

Minimal NES timing rule:

    1 CPU cycle = 3 PPU cycles

Minimal example:

    CPU executes NOP
    NOP takes 2 CPU cycles
    PPU advances 2 * 3 = 6 PPU cycles

Common misconception:
Do not make CPU.step() call PPU.step(). The CPU should not own video timing.
Console owns the coordination between chips.

Suggested implementation example:

    @dataclass
    class Console:
        cpu: CPU
        ppu: PPU

        def consume_nmi_if_requested(self) -> None:
            if not self.ppu.nmi_requested:
                return

            self.ppu.nmi_requested = False
            self.cpu.interrupt_nmi()

        def step(self) -> int:
            # This is base timing only. Later steps can add branch penalties,
            # NMI latency, DMA stalls, and other timing details.
            cpu_cycles = self.cpu.step()
            self.ppu.step(cpu_cycles * 3)
            self.consume_nmi_if_requested()
            return cpu_cycles

Important limitation:
This is still simplified timing. CPU.step() currently returns base cycles only.
Later improvements can account for:

    branch taken extra cycles
    branch page-cross extra cycles
    indexed addressing page-cross extra cycles
    NMI latency
    OAM DMA stalls

Out of scope:
    - dynamic CPU cycle penalties
    - dot-accurate NMI latency
    - OAM DMA
    - rendering pixels
    - pygame/frontend loop
    - controller input
"""

from emulator.console import Console
from emulator.ppu.ppu import (
    CTRL_NMI_ENABLE,
    PPU_CYCLES_PER_SCANLINE,
    PPU_VBLANK_START_SCANLINE,
)
from tests.helpers import load_program, make_cpu_with_rom


def write_nmi_vector(rom, addr: int) -> None:
    """Install the NMI vector in FakeROM for CPU.interrupt_nmi()."""
    rom.write(0x7FFA, addr & 0xFF)
    rom.write(0x7FFB, (addr >> 8) & 0xFF)


def make_console_with_fake_rom():
    """
    Build a small coherent console.

    Use cpu.bus.ppu so CPU bus register access and Console timing observe the same
    PPU instance.
    """
    cpu, bus, rom = make_cpu_with_rom()
    ppu = bus.ppu
    return Console(cpu=cpu, ppu=ppu), cpu, ppu, rom


def test_console_exposes_step_method():
    """
    Objective:
    Console has a machine-level step method for CPU/PPU coordination.
    """
    assert hasattr(Console, "step")
    assert callable(Console.step)


def test_console_step_executes_one_cpu_instruction_and_returns_cpu_cycles():
    """
    Objective:
    Console.step() executes one CPU instruction and returns that instruction's CPU
    cycle count.

    Example:
        NOP is opcode $EA and returns 2 CPU cycles.
    """
    console, cpu, _ppu, rom = make_console_with_fake_rom()
    load_program(rom, 0x8000, [0xEA])
    cpu.pc = 0x8000

    cycles = console.step()

    assert cycles == 2
    assert cpu.pc == 0x8001


def test_console_step_advances_ppu_by_three_times_cpu_cycles():
    """
    Objective:
    Console.step() applies the NES clock ratio:

        1 CPU cycle = 3 PPU cycles

    Example:
        NOP takes 2 CPU cycles, so PPU advances 6 cycles.
    """
    console, cpu, ppu, rom = make_console_with_fake_rom()
    load_program(rom, 0x8000, [0xEA])
    cpu.pc = 0x8000
    ppu.cycle = 10

    cycles = console.step()

    assert cycles == 2
    assert ppu.cycle == 16


def test_console_step_advances_ppu_scanline_when_ppu_cycles_cross_scanline_boundary():
    """
    Objective:
    Console.step() should use PPU.step(), not manually increment ppu.cycle.
    Therefore normal PPU scanline wrapping still applies.

    Example:
        If PPU is 2 cycles before the end of a scanline and CPU executes NOP
        for 2 CPU cycles, the PPU advances 6 cycles total and enters the next
        scanline with 4 cycles remaining.
    """
    console, cpu, ppu, rom = make_console_with_fake_rom()
    load_program(rom, 0x8000, [0xEA])
    cpu.pc = 0x8000
    ppu.cycle = PPU_CYCLES_PER_SCANLINE - 2
    ppu.scanline = 7

    cycles = console.step()

    assert cycles == 2
    assert ppu.scanline == 8
    assert ppu.cycle == 4


def test_console_step_consumes_nmi_after_ppu_advancement():
    """
    Objective:
    If PPU stepping enters VBlank and requests NMI, Console.step() consumes that
    request after advancing PPU time.

    Setup:
        PPU is 6 cycles before entering scanline 241.
        CPU executes NOP for 2 CPU cycles.
        Console advances PPU by 2 * 3 = 6 cycles.
        PPU enters VBlank and requests NMI.
        Console consumes the request and CPU jumps to the NMI vector.
    """
    console, cpu, ppu, rom = make_console_with_fake_rom()
    load_program(rom, 0x8000, [0xEA])
    write_nmi_vector(rom, 0xC000)

    cpu.pc = 0x8000
    cpu.s = 0xFD
    ppu.write_register(0x2000, CTRL_NMI_ENABLE)
    ppu.scanline = PPU_VBLANK_START_SCANLINE - 1
    ppu.cycle = PPU_CYCLES_PER_SCANLINE - 6
    ppu.nmi_requested = False

    cycles = console.step()

    assert cycles == 2
    assert ppu.scanline == PPU_VBLANK_START_SCANLINE
    assert ppu.cycle == 0
    assert ppu.nmi_requested is False
    assert cpu.pc == 0xC000
    assert cpu.s == 0xFA


def test_console_step_does_not_create_cpu_to_ppu_coupling():
    """
    Objective:
    Document the boundary: Console coordinates CPU and PPU timing. CPU.step()
    returns cycles; it does not directly step the PPU.

    This test observes the effect through Console.step(), not by adding PPU logic
    inside CPU.
    """
    console, cpu, ppu, rom = make_console_with_fake_rom()
    load_program(rom, 0x8000, [0xEA, 0xEA])
    cpu.pc = 0x8000

    first_cycles = console.step()
    second_cycles = console.step()

    assert first_cycles == 2
    assert second_cycles == 2
    assert cpu.pc == 0x8002
    assert ppu.cycle == 12
