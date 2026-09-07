"""Step 189: add addressing-independent BRK behavior.

Prerequisite: step 188 added the I, B, and unused-bit helpers. In this step, add
this complete ``emulator/cpu/instructions.py::brk`` implementation:

    def brk(cpu: CPU):
        return_addr = (cpu.pc + 1) & 0xFFFF
        STACK_BASE = 0x0100
        high = (return_addr >> 8) & 0xFF
        low = return_addr & 0xFF

        cpu.bus.write(STACK_BASE | cpu.s, high)
        cpu.s = (cpu.s - 1) & 0xFF
        cpu.bus.write(STACK_BASE | cpu.s, low)
        cpu.s = (cpu.s - 1) & 0xFF

        cpu.flags.set_break_flag(True)
        cpu.flags.set_one_flag(True)
        cpu.bus.write(STACK_BASE | cpu.s, cpu.p)
        cpu.s = (cpu.s - 1) & 0xFF
        cpu.flags.set_interrupt_disable_flag(True)
        cpu.flags.set_break_flag(False)
        cpu.flags.set_one_flag(False)

        low = cpu.bus.read(0xFFFE)
        high = cpu.bus.read(0xFFFF)
        cpu.pc = (high << 8) | low

Instruction:
    BRK -> Force Interrupt / Software Interrupt

Goal:
implement brk(cpu) in instructions.py.

Student guidance:
BRK is one of the easiest 6502 instructions to misunderstand.

The opcode is one byte:

    00 -> BRK

But BRK is treated as a 2-byte instruction by the CPU. The byte after opcode
$00 is skipped. That byte can be any value. It is sometimes called a padding
byte or signature byte.

Important timeline:
    If BRK is stored at $8000:

        $8000: 00    BRK opcode
        $8001: XX    padding/signature byte, ignored by normal BRK behavior
        $8002: ...   next real instruction

    CPU.step() fetches opcode $00 and increments PC to $8001.
    Then brk(cpu) must add one more to produce return address $8002.

BRK must:
    1. Compute return address as PC + 1.
    2. Push return address high byte.
    3. Push return address low byte.
    4. Push status with Break flag set and ONE/unused bit set.
    5. Set Interrupt Disable flag.
    6. Clear Break again if your emulator models B only in the pushed status byte.
    7. Load PC from IRQ/BRK vector $FFFE/$FFFF.

Common mistakes:
    - Pushing $8001 instead of $8002.
    - Thinking the padding byte must be $00. It can be anything.
    - Writing status to $0100 | P instead of $0100 | S.
    - Loading only one vector byte from $FFFE.

Why this step exists:
Direct calls enter with PC on the padding byte because opcode fetch
already advanced it; BRK saves the post-padding return address and pre-I status,
then vectors through little-endian $FFFE/$FFFF.  Invariants: pushes are PC high,
PC low, status; S wraps after each; pushed P has B/ONE set; live P ends with I
set and B/ONE clear.  Misconception: BRK does not execute or require a zero
padding byte, and B is a property of the stacked status copy.

Out of scope: importing/mapping opcode $00 is step 190.  RTI, hardware
IRQ/NMI entry, and later ``CPU.push_byte``/``CPU.push_word`` helpers must not be
introduced here.
"""

from emulator.bus.cpu_bus import CpuBus
from emulator.cpu.cpu import CPU
from emulator.cpu.instructions import brk
from emulator.memory.fake_rom import FakeROM


INTERRUPT_DISABLE_FLAG = 1 << 2
BREAK_FLAG = 1 << 4
ONE_FLAG = 1 << 5
STACK_BASE = 0x0100


def make_cpu_with_rom():
    rom = FakeROM()
    bus = CpuBus(program_rom=rom)
    return CPU(bus), bus, rom


def write_brk_vector(rom, addr):
    """Write the IRQ/BRK vector used by BRK at CPU addresses $FFFE/$FFFF."""
    rom.write(0x7FFE, addr & 0xFF)
    rom.write(0x7FFF, (addr >> 8) & 0xFF)


def test_brk_loads_program_counter_from_irq_brk_vector():
    """Objective: BRK jumps to the interrupt handler address stored at $FFFE/$FFFF."""
    cpu, bus, rom = make_cpu_with_rom()
    cpu.pc = 0x8001
    cpu.s = 0xFD
    write_brk_vector(rom, 0x9000)

    brk(cpu)

    assert cpu.pc == 0x9000


def test_brk_pushes_return_address_high_then_low():
    """
    Objective:
    At brk(cpu) time, PC already points to BRK's padding byte.

    If PC is $8001, BRK skips the padding byte and pushes return address $8002:
        high byte $80 goes to $01FD
        low byte  $02 goes to $01FC
    """
    cpu, bus, rom = make_cpu_with_rom()
    cpu.pc = 0x8001
    cpu.s = 0xFD
    write_brk_vector(rom, 0x9000)

    brk(cpu)

    assert bus.read(STACK_BASE | 0xFD) == 0x80
    assert bus.read(STACK_BASE | 0xFC) == 0x02


def test_brk_decrements_stack_pointer_three_times():
    """Objective: BRK pushes PC high, PC low, and status, so S decreases by 3."""
    cpu, bus, rom = make_cpu_with_rom()
    cpu.pc = 0x8001
    cpu.s = 0xFD
    write_brk_vector(rom, 0x9000)

    brk(cpu)

    assert cpu.s == 0xFA


def test_brk_pushes_status_with_break_flag_set():
    """
    Objective:
    The status byte pushed by BRK must have the Break flag set.

    This is different from saying BRK's opcode is $00. The B flag is bit 4 in
    the pushed status byte.
    """
    cpu, bus, rom = make_cpu_with_rom()
    cpu.pc = 0x8001
    cpu.s = 0xFD
    cpu.p = 0x00
    write_brk_vector(rom, 0x9000)

    brk(cpu)

    pushed_status = bus.read(STACK_BASE | 0xFB)
    assert (pushed_status & BREAK_FLAG) != 0
    assert (pushed_status & ONE_FLAG) != 0


def test_brk_sets_interrupt_disable_flag_after_pushing_status():
    """
    Objective:
    BRK sets the Interrupt Disable flag so maskable IRQs are disabled while the
    interrupt handler starts running.
    """
    cpu, bus, rom = make_cpu_with_rom()
    cpu.pc = 0x8001
    cpu.s = 0xFD
    cpu.p = 0x00
    write_brk_vector(rom, 0x9000)

    brk(cpu)

    assert cpu.flags.get_interrupt_disable_flag() is True
    assert (cpu.p & INTERRUPT_DISABLE_FLAG) != 0


def test_brk_clears_break_flag_from_cpu_state_after_pushing_status():
    """
    Objective:
    In this emulator model, B is represented in the pushed status byte, not as a
    persistent CPU state after BRK finishes.
    """
    cpu, bus, rom = make_cpu_with_rom()
    cpu.pc = 0x8001
    cpu.s = 0xFD
    cpu.p = 0x00
    write_brk_vector(rom, 0x9000)

    brk(cpu)

    pushed_status = bus.read(STACK_BASE | 0xFB)
    assert (pushed_status & BREAK_FLAG) != 0
    assert (pushed_status & ONE_FLAG) != 0
    assert cpu.flags.get_break_flag() is False
    assert cpu.flags.get_one_flag() is False


def test_brk_stack_pointer_wraps_to_8_bits():
    """Objective: S is an 8-bit stack pointer and wraps during BRK pushes."""
    cpu, bus, rom = make_cpu_with_rom()
    cpu.pc = 0x8001
    cpu.s = 0x01
    write_brk_vector(rom, 0x9000)

    brk(cpu)

    assert bus.read(STACK_BASE | 0x01) == 0x80
    assert bus.read(STACK_BASE | 0x00) == 0x02
    assert bus.read(STACK_BASE | 0xFF) & BREAK_FLAG
    assert bus.read(STACK_BASE | 0xFF) & ONE_FLAG
    assert cpu.s == 0xFE
