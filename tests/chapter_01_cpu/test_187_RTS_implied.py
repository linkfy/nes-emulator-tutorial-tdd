"""Step 187: wire implied RTS opcode $60.

Prerequisite: step 186 supplied ``rts``. In this step, add its import and direct
table mapping in
``emulator/cpu/opcodes.py``:

    from emulator.cpu.instructions import rts

    OPCODE_TABLE = {
        # existing entries...
        0x60: rts,
    }

Opcode:
    0x60 -> RTS

Goal:
add opcode 0x60 to OPCODE_TABLE.

Student guidance:
RTS uses implied addressing. That means the opcode has no operand bytes.
The instruction gets all information it needs from the CPU stack.

Example:
    60 -> RTS

Execution steps:
    1. CPU.step() fetches opcode 0x60.
    2. OPCODE_TABLE dispatches directly to rts(cpu).
    3. RTS pulls the return address from the stack.
    4. RTS sets PC to pulled_address + 1.

Common mistake:
Do not fetch an operand byte for RTS. It is an implied instruction.

Why this step exists:
``CPU.step`` has already consumed the sole opcode byte, and ``rts``
gets its return word from the stack, so no wrapper or addressing mode is
needed.  Invariants: $60 maps directly to the one-argument function; dispatch
does not consume $8001; RTS alone performs the two pulls and PC update.
Misconception: every opcode does not require a named handler.

Out of scope: flag helpers and BRK are steps 188-190; RTI and opcode $40 are
steps 191-192.
"""
import inspect

from emulator.bus.cpu_bus import CpuBus
from emulator.cpu import opcodes
from emulator.cpu.cpu import CPU
from emulator.cpu.instructions import rts
from emulator.memory.fake_rom import FakeROM


STACK_BASE = 0x0100


def make_cpu_with_rom():
    rom = FakeROM()
    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)
    bus = CpuBus(program_rom=rom)
    return CPU(bus), bus, rom


def test_rts_implied_is_in_opcode_table():
    """Objective: opcode 0x60 is the official RTS opcode."""
    assert opcodes.OPCODE_TABLE[0x60] is rts


def test_rts_instruction_signature_takes_only_cpu():
    """Objective: RTS is implied, so rts(cpu) does not need an operand argument."""
    assert list(inspect.signature(rts).parameters) == ["cpu"]


def test_opcode_60_rts_restores_program_counter_from_stack():
    """Objective: executing opcode 0x60 returns to the address saved on the stack."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x60)

    cpu.reset()
    cpu.s = 0xFB
    bus.write(STACK_BASE | 0xFC, 0x02)
    bus.write(STACK_BASE | 0xFD, 0x80)

    cpu.step()

    assert cpu.pc == 0x8003
    assert cpu.s == 0xFD


def test_opcode_60_rts_does_not_fetch_operand_bytes():
    """
    Objective:
    RTS is one byte long. The byte after RTS must not be consumed as an operand.

    If RTS incorrectly fetched an operand byte, stack behavior or PC behavior could
    accidentally depend on the byte at $8001. This test makes the return target
    come only from the stack.
    """
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x60)
    rom.write(0x0001, 0x99)

    cpu.reset()
    cpu.s = 0xFB
    bus.write(STACK_BASE | 0xFC, 0x34)
    bus.write(STACK_BASE | 0xFD, 0x12)

    cpu.step()

    assert cpu.pc == 0x1235
    assert cpu.s == 0xFD


def test_opcode_60_rts_can_return_after_jsr_style_stack_contents():
    """
    Objective:
    JSR to a subroutine at $9000 would push return address $8002.
    RTS then returns to $8003, the instruction after JSR.
    """
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x1000, 0x60)

    cpu.reset()
    cpu.pc = 0x9000
    cpu.s = 0xFB
    bus.write(STACK_BASE | 0xFC, 0x02)
    bus.write(STACK_BASE | 0xFD, 0x80)

    cpu.step()

    assert cpu.pc == 0x8003
    assert cpu.s == 0xFD
