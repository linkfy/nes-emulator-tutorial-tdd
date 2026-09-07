"""
Implement CPU-side NMI interrupt mechanics.

References:
    https://www.nesdev.org/wiki/CPU_interrupts
    https://www.nesdev.org/wiki/PPU_registers#Vblank_NMI

Files to update:
    emulator/cpu/cpu.py

Why this step exists:
The PPU can already produce an nmi_requested signal. Before connecting that signal
to the CPU through a system/console coordinator, the CPU must know how to perform
the NMI sequence by itself.

What is NMI?
NMI means Non-Maskable Interrupt. On the NES, the PPU can request NMI at VBlank
so game code can run its vertical blank handler.

Intuitive model:
NMI is like a hardware emergency jump. The CPU pauses its current path, saves
enough state to return later, then jumps to the address stored in the NMI vector.

Mechanistic model:
When NMI is accepted, the CPU performs this sequence:

    1. Push PC high byte
    2. Push PC low byte
    3. Push status with:
           ONE_FLAG set
           B_FLAG clear
    4. Set INTERRUPT_FLAG in CPU status
    5. Read low byte from $FFFA
    6. Read high byte from $FFFB
    7. Set PC = high << 8 | low

Important distinction:
NMI does not write to $FFFA/$FFFB. The CPU reads those addresses. In a real ROM,
the vector bytes already exist in PRG ROM. In these tests, FakeROM lets us prepare
those bytes as test setup.

Example implementation:

    NMI_VECTOR_LOW = 0xFFFA
    NMI_VECTOR_HIGH = 0xFFFB

    class CPU:
        ...

        def interrupt_nmi(self) -> None:
            # Save the current PC so RTI can restore it later.
            pc_high = (self.pc >> 8) & 0xFF
            pc_low = self.pc & 0xFF
            self.push_stack(pc_high)
            self.push_stack(pc_low)

            # Hardware interrupts push status with B clear and bit 5 set.
            status_to_push = self.p | ONE_FLAG
            status_to_push &= ~B_FLAG
            self.push_stack(status_to_push)

            # After accepting an interrupt, set the interrupt-disable flag.
            self.p |= INTERRUPT_FLAG

            # NMI vector bytes are read from PRG space. NMI does not write them.
            low = self.bus.read(NMI_VECTOR_LOW)
            high = self.bus.read(NMI_VECTOR_HIGH)
            self.pc = low | (high << 8)

Concrete runtime example:

    FakeROM setup:
        $FFFA = $00
        $FFFB = $C0

    CPU before NMI:
        PC = $8123
        S  = $FD

    CPU.interrupt_nmi()

    CPU after NMI:
        stack contains return PC/status
        PC = $C000

Stack example with S = $FD and PC = $8123:

    write $81 to $01FD, S becomes $FC
    write $23 to $01FC, S becomes $FB
    write status to $01FB, S becomes $FA

Common misconception:
The B flag is not set for hardware interrupts. BRK/PHP push status with B set,
but NMI pushes status with B clear. Bit 5, ONE_FLAG, is still set in the pushed
status byte.

Out of scope:
    - PPU calling CPU.interrupt_nmi()
    - clearing ppu.nmi_requested
    - exact interrupt latency/cycle counts
    - IRQ/APU/mapper interrupts
    - RTI behavior, which was tested earlier in the CPU chapter
"""

from emulator.cpu import cpu as cpu_module
from emulator.cpu.flags_handler import (
    B_FLAG,
    CARRY_FLAG,
    DECIMAL_FLAG,
    INTERRUPT_FLAG,
    NEGATIVE_FLAG,
    ONE_FLAG,
    ZERO_FLAG,
)
from tests.helpers import make_cpu_with_rom


def write_nmi_vector(rom, addr: int) -> None:
    """
    Install the NMI vector in FakeROM.

    CPU address $FFFA maps to FakeROM offset $7FFA because CpuBus maps
    $8000-$FFFF to program_rom offsets $0000-$7FFF.
    """
    rom.write(0x7FFA, addr & 0xFF)
    rom.write(0x7FFB, (addr >> 8) & 0xFF)


def test_cpu_declares_nmi_vector_constants():
    """
    Objective:
    Name the NMI vector addresses used by CPU.interrupt_nmi().
    """
    assert cpu_module.NMI_VECTOR_LOW == 0xFFFA
    assert cpu_module.NMI_VECTOR_HIGH == 0xFFFB


def test_interrupt_nmi_loads_pc_from_nmi_vector():
    """
    Objective:
    CPU.interrupt_nmi() reads $FFFA/$FFFB and jumps to that address.

    Example:
        $FFFA = $00
        $FFFB = $C0
        PC becomes $C000
    """
    cpu, _bus, rom = make_cpu_with_rom()
    write_nmi_vector(rom, 0xC000)
    cpu.pc = 0x8123
    cpu.s = 0xFD

    cpu.interrupt_nmi()

    assert cpu.pc == 0xC000


def test_interrupt_nmi_pushes_current_pc_high_then_low_to_stack():
    """
    Objective:
    NMI saves the current PC on the stack before jumping to the vector target.

    With PC=$8123 and S=$FD:
        $01FD receives $81
        $01FC receives $23
    """
    cpu, bus, rom = make_cpu_with_rom()
    write_nmi_vector(rom, 0xC000)
    cpu.pc = 0x8123
    cpu.s = 0xFD

    cpu.interrupt_nmi()

    assert bus.read(0x01FD) == 0x81
    assert bus.read(0x01FC) == 0x23


def test_interrupt_nmi_pushes_status_with_one_set_and_break_clear():
    """
    Objective:
    Hardware interrupts push a status byte with ONE_FLAG set and B_FLAG clear.

    This differs from BRK/PHP, which push B_FLAG set.
    """
    cpu, bus, rom = make_cpu_with_rom()
    write_nmi_vector(rom, 0xC000)
    cpu.pc = 0x8123
    cpu.s = 0xFD

    cpu.p = CARRY_FLAG | ZERO_FLAG | DECIMAL_FLAG | B_FLAG | NEGATIVE_FLAG

    cpu.interrupt_nmi()

    pushed_status = bus.read(0x01FB)

    assert pushed_status & CARRY_FLAG
    assert pushed_status & ZERO_FLAG
    assert pushed_status & DECIMAL_FLAG
    assert pushed_status & NEGATIVE_FLAG
    assert pushed_status & ONE_FLAG
    assert not (pushed_status & B_FLAG)


def test_interrupt_nmi_sets_interrupt_disable_flag_in_cpu_status():
    """
    Objective:
    After accepting NMI, the CPU sets the interrupt-disable flag in its live status
    register.
    """
    cpu, _bus, rom = make_cpu_with_rom()
    write_nmi_vector(rom, 0xC000)
    cpu.pc = 0x8123
    cpu.s = 0xFD
    cpu.p = 0x00

    cpu.interrupt_nmi()

    assert cpu.p & INTERRUPT_FLAG


def test_interrupt_nmi_consumes_three_stack_bytes():
    """
    Objective:
    NMI pushes PC high, PC low, and status. That consumes exactly three stack
    bytes.

    Example:
        S starts at $FD
        after three pushes, S is $FA
    """
    cpu, _bus, rom = make_cpu_with_rom()
    write_nmi_vector(rom, 0xC000)
    cpu.pc = 0x8123
    cpu.s = 0xFD

    cpu.interrupt_nmi()

    assert cpu.s == 0xFA


def test_interrupt_nmi_full_stack_layout_example():
    """
    Objective:
    Validate the complete NMI stack layout in one readable example.

    Given:
        PC = $ABCD
        S  = $80
        P  = ZERO_FLAG | B_FLAG

    Expected pushes:
        $0180 = $AB
        $017F = $CD
        $017E = status with ZERO_FLAG set, ONE_FLAG set, B_FLAG clear
    """
    cpu, bus, rom = make_cpu_with_rom()
    write_nmi_vector(rom, 0x9000)
    cpu.pc = 0xABCD
    cpu.s = 0x80
    cpu.p = ZERO_FLAG | B_FLAG

    cpu.interrupt_nmi()

    assert bus.read(0x0180) == 0xAB
    assert bus.read(0x017F) == 0xCD

    pushed_status = bus.read(0x017E)
    assert pushed_status & ZERO_FLAG
    assert pushed_status & ONE_FLAG
    assert not (pushed_status & B_FLAG)

    assert cpu.s == 0x7D
    assert cpu.pc == 0x9000
    assert cpu.p & INTERRUPT_FLAG
