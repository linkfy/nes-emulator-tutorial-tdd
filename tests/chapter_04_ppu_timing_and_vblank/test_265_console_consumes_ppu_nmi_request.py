"""
Model Console as the coordinator that consumes PPU NMI requests.

References:
    https://www.nesdev.org/wiki/CPU_interrupts
    https://www.nesdev.org/wiki/PPU_registers#Vblank_NMI

File to create:
    emulator/console.py

Why this step exists:
The emulator now has the two separate mechanisms needed for VBlank NMI:

    PPU mechanism:
        PPU enters VBlank and sets ppu.nmi_requested = True

    CPU mechanism:
        CPU.interrupt_nmi() pushes PC/status and jumps through $FFFA/$FFFB

Now we need a small coordinator that connects those mechanisms without making
CPU and PPU depend directly on each other.

What is Console?
Console is the future top-level emulated NES machine. Over time it can own and
coordinate subsystems such as:

    CPU
    PPU
    cartridge/mapper
    controllers
    APU/audio
    frame stepping

At this stage, Console starts very small. Its first job is only to consume a PPU
NMI request and call CPU.interrupt_nmi().

Correct responsibility split:

    PPU:
        produces nmi_requested

    CPU:
        implements interrupt_nmi()

    Console:
        connects the PPU signal to the CPU mechanism

Important architecture rule:
Do not put PPU ownership inside CPU. The CPU should not ask the PPU whether an
NMI is pending. That would create hidden coupling between CPU execution and video
hardware.

Minimal implementation example:

    from dataclasses import dataclass

    from emulator.cpu.cpu import CPU
    from emulator.ppu.ppu import PPU


    @dataclass
    class Console:
        cpu: CPU
        ppu: PPU

        def consume_nmi_if_requested(self) -> None:
            if not self.ppu.nmi_requested:
                return

            self.ppu.nmi_requested = False
            self.cpu.interrupt_nmi()

Future shape, introduced in a later timing test:

    class Console:
        ...

        def step(self) -> None:
            cpu_cycles = self.cpu.step()
            self.ppu.step(cpu_cycles * 3)
            self.consume_nmi_if_requested()

This file does not test Console.step(). CPU/PPU timing integration is tested as a
separate step after CPU.step() returns instruction cycles.

Common misconception:
Because the PPU causes NMI, it may feel natural to make CPU own PPU. Avoid that.
The CPU receives interrupt signals; it should not own the video device.

Out of scope:
    - CPU/PPU cycle ratio
    - Console.step()
    - rendering
    - controllers
    - APU/audio
    - exact NMI latency
"""

from dataclasses import is_dataclass

from emulator.console import Console
from emulator.cpu.cpu import CPU
from emulator.ppu.ppu import PPU
from tests.helpers import make_cpu_with_rom


def write_nmi_vector(rom, addr: int) -> None:
    """
    Install the NMI vector in FakeROM for CPU.interrupt_nmi().

    CPU address $FFFA maps to FakeROM offset $7FFA because CpuBus maps
    $8000-$FFFF to program_rom offsets $0000-$7FFF.
    """
    rom.write(0x7FFA, addr & 0xFF)
    rom.write(0x7FFB, (addr >> 8) & 0xFF)


def make_console_with_fake_rom():
    """
    Build a coherent small console for NMI tests.

    Important:
    Use the PPU already owned by cpu.bus. That keeps this test close to the real
    emulator shape where CPU register accesses and Console coordination should be
    observing the same PPU instance.
    """
    cpu, bus, rom = make_cpu_with_rom()
    ppu = bus.ppu
    return Console(cpu=cpu, ppu=ppu), cpu, ppu, rom


def test_console_is_small_machine_coordinator_for_cpu_and_ppu():
    """
    Objective:
    Console starts as a small coordinator that stores CPU and PPU references.
    """
    assert is_dataclass(Console)

    console, cpu, ppu, _rom = make_console_with_fake_rom()

    assert console.cpu is cpu
    assert console.ppu is ppu
    assert isinstance(console.cpu, CPU)
    assert isinstance(console.ppu, PPU)


def test_console_exposes_nmi_consumption_method():
    """
    Objective:
    Console exposes the boundary method that connects PPU NMI requests to CPU NMI
    handling.
    """
    assert hasattr(Console, "consume_nmi_if_requested")
    assert callable(Console.consume_nmi_if_requested)


def test_console_does_nothing_when_ppu_has_no_nmi_request():
    """
    Objective:
    If ppu.nmi_requested is False, Console must not interrupt the CPU.
    """
    console, cpu, ppu, rom = make_console_with_fake_rom()
    write_nmi_vector(rom, 0xC000)
    cpu.pc = 0x8123
    cpu.s = 0xFD
    ppu.nmi_requested = False

    console.consume_nmi_if_requested()

    assert cpu.pc == 0x8123
    assert cpu.s == 0xFD
    assert ppu.nmi_requested is False


def test_console_consumes_ppu_nmi_request_and_interrupts_cpu():
    """
    Objective:
    When ppu.nmi_requested is True, Console calls CPU.interrupt_nmi() and clears
    the request.

    Example:
        PPU request: nmi_requested = True
        NMI vector:  $FFFA/$FFFB -> $C000
        CPU before:  PC = $8123
        CPU after:   PC = $C000
        PPU after:   nmi_requested = False
    """
    console, cpu, ppu, rom = make_console_with_fake_rom()
    write_nmi_vector(rom, 0xC000)
    cpu.pc = 0x8123
    cpu.s = 0xFD
    ppu.nmi_requested = True

    console.consume_nmi_if_requested()

    assert cpu.pc == 0xC000
    assert cpu.s == 0xFA
    assert ppu.nmi_requested is False


def test_console_consumes_each_ppu_nmi_request_only_once():
    """
    Objective:
    A single PPU NMI request should produce at most one CPU NMI.

    Why this matters:
    If Console forgot to clear ppu.nmi_requested, every coordinator check would
    interrupt the CPU again from the same stale request.
    """
    console, cpu, ppu, rom = make_console_with_fake_rom()
    write_nmi_vector(rom, 0xC000)
    cpu.pc = 0x8123
    cpu.s = 0xFD
    ppu.nmi_requested = True

    console.consume_nmi_if_requested()
    pc_after_first_consume = cpu.pc
    stack_after_first_consume = cpu.s

    console.consume_nmi_if_requested()

    assert cpu.pc == pc_after_first_consume
    assert cpu.s == stack_after_first_consume
    assert ppu.nmi_requested is False


def test_console_keeps_cpu_and_ppu_coupling_out_of_subsystems():
    """
    Objective:
    Document the desired dependency direction.

    Console may import CPU and PPU because it coordinates the machine. CPU should
    not need to import PPU just to handle NMI, and PPU should not call CPU directly.

    This test checks behavior through the public coordinator instead of adding a
    CPU -> PPU dependency.
    """
    console, cpu, ppu, rom = make_console_with_fake_rom()
    write_nmi_vector(rom, 0x9000)
    cpu.pc = 0x8000
    cpu.s = 0xFD

    ppu.nmi_requested = True
    console.consume_nmi_if_requested()

    assert cpu.pc == 0x9000
    assert ppu.nmi_requested is False
