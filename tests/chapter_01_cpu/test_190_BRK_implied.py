"""Step 190: wire implied BRK opcode $00.

Prerequisite: step 189 completed ``brk`` with the required status-bit behavior.
In this step, add this import and direct mapping in ``emulator/cpu/opcodes.py``:

    from emulator.cpu.instructions import brk

    OPCODE_TABLE = {
        # existing entries...
        0x00: brk,
    }

Opcode:
    0x00 -> BRK

Goal:
add opcode 0x00 to OPCODE_TABLE.

Student guidance:
BRK is usually listed as an implied instruction, but it has a special length:

    opcode byte:       $00
    padding byte:      one ignored byte after $00
    total length:      2 bytes

This does NOT mean there are two opcode entries for BRK.
There is only one official opcode:

    0x00

The byte after BRK can be any value. The CPU skips it and pushes the return
address after that byte.

Example:
    $8000: 00    BRK opcode
    $8001: AB    padding/signature byte, ignored by BRK
    $8002: EA    next real instruction

After CPU.step() executes BRK, the pushed return address should be $8002.

Why this step exists:
``CPU.step`` fetches $00 and advances PC once; direct dispatch to
``brk`` accounts for the implicit padding byte and performs all stack/vector
work.  Invariants: there is one table entry and no addressing-mode fetch;
padding contents do not affect A or the destination; the step-189 BRK state
and stack rules remain unchanged.  Misconception: BRK's two-byte architectural
length does not imply a two-byte opcode or an operand-decoding wrapper.

Out of scope: RTI/$40 are steps 191-192.  Hardware interrupt dispatch, NMI,
shared stack helpers, and later opcode APIs are not part of this transition.
"""
import inspect

from emulator.bus.cpu_bus import CpuBus
from emulator.cpu import opcodes
from emulator.cpu.cpu import CPU
from emulator.cpu.instructions import brk
from emulator.memory.fake_rom import FakeROM


INTERRUPT_DISABLE_FLAG = 1 << 2
BREAK_FLAG = 1 << 4
ONE_FLAG = 1 << 5
STACK_BASE = 0x0100


def make_cpu_with_rom():
    rom = FakeROM()
    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)
    rom.write(0x7FFE, 0x00)
    rom.write(0x7FFF, 0x90)
    bus = CpuBus(program_rom=rom)
    return CPU(bus), bus, rom


def test_brk_implied_is_in_opcode_table():
    """Objective: opcode 0x00 is the official BRK opcode."""
    assert opcodes.OPCODE_TABLE[0x00] is brk


def test_brk_instruction_signature_takes_only_cpu():
    """Objective: BRK dispatch does not need an addressing-mode argument."""
    assert list(inspect.signature(brk).parameters) == ["cpu"]


def test_opcode_00_brk_loads_pc_from_irq_brk_vector():
    """Objective: executing opcode 0x00 jumps to the vector stored at $FFFE/$FFFF."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x00)
    rom.write(0x0001, 0xAB)

    cpu.reset()
    cpu.p = 0x00
    cpu.step()

    assert cpu.pc == 0x9000


def test_opcode_00_brk_pushes_address_after_padding_byte():
    """
    Objective:
    BRK is treated as 2 bytes.

    Timeline:
        Before step: PC = $8000
        CPU.step fetches $00, so PC becomes $8001
        brk(cpu) skips padding byte and pushes $8002

    The padding byte can be $AB, $00, $FF, or anything else.
    """
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x00)
    rom.write(0x0001, 0xAB)

    cpu.reset()
    cpu.p = 0x00
    cpu.step()

    assert bus.read(STACK_BASE | 0xFD) == 0x80
    assert bus.read(STACK_BASE | 0xFC) == 0x02


def test_opcode_00_brk_pushes_status_with_break_flag_set():
    """Objective: opcode BRK pushes P with Break and ONE bits set."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x00)
    rom.write(0x0001, 0xAB)

    cpu.reset()
    cpu.p = 0x00
    cpu.step()

    pushed_status = bus.read(STACK_BASE | 0xFB)
    assert (pushed_status & BREAK_FLAG) != 0
    assert (pushed_status & ONE_FLAG) != 0


def test_opcode_00_brk_sets_interrupt_disable_and_clears_cpu_break_state():
    """
    Objective:
    After BRK finishes, Interrupt Disable is set, but Break is not kept as a
    persistent CPU status bit in this emulator model.
    """
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x00)
    rom.write(0x0001, 0xAB)

    cpu.reset()
    cpu.p = 0x00
    cpu.step()

    assert (cpu.p & INTERRUPT_DISABLE_FLAG) != 0
    assert cpu.flags.get_interrupt_disable_flag() is True
    assert cpu.flags.get_break_flag() is False
    assert cpu.flags.get_one_flag() is False


def test_opcode_00_brk_padding_byte_is_ignored_not_executed():
    """
    Objective:
    The byte after BRK is skipped by BRK. It is not executed as the next opcode.

    If the padding byte is $A9, that might look like LDA Immediate, but BRK must
    ignore it and jump to the interrupt vector instead.
    """
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x00)
    rom.write(0x0001, 0xA9)
    rom.write(0x0002, 0x42)

    cpu.reset()
    cpu.a = 0x00
    cpu.p = 0x00
    cpu.step()

    assert cpu.pc == 0x9000
    assert cpu.a == 0x00
    assert bus.read(STACK_BASE | 0xFC) == 0x02
