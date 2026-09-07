"""
Make CPU.step() return base instruction cycles.

Reference:
    https://www.nesdev.org/wiki/Visual6502wiki/6502_all_256_Opcodes

Files to update:
    emulator/cpu/cpu.py

Why this step exists:
The emulator now has a standalone OPCODE_CYCLES table. The next timing bridge is
for CPU.step() to return the base cycle count for the opcode it executed.

This prepares the future Console.step() shape:

    cpu_cycles = cpu.step()
    ppu.step(cpu_cycles * 3)
    console.consume_nmi_if_requested()

What is a base instruction cycle count?
A base instruction cycle count is the normal number of CPU cycles an opcode takes
before dynamic penalties are added.

Minimal examples:

    NOP implied      opcode $EA -> 2 cycles
    LDA immediate   opcode $A9 -> 2 cycles
    JSR absolute    opcode $20 -> 6 cycles

Common misconception:
Cycles are not the same as bytes fetched. JSR is 3 bytes but takes 6 cycles.
Do not count cycles inside fetch_byte().

Suggested implementation example:

    from emulator.cpu.opcodes import OPCODE_CYCLES, OPCODE_TABLE


    class CPU:
        ...

        def step(self) -> int:
            opcode = self.fetch_byte()
            handler = OPCODE_TABLE.get(opcode)
            if handler is None:
                raise NotImplementedError(f"Opcode {opcode:02X} not implemented")

            handler(self)
            return OPCODE_CYCLES[opcode]

Why this avoids a large refactor:
OPCODE_TABLE remains the existing opcode -> handler mapping. OPCODE_CYCLES is a
parallel metadata table. Old instruction behavior tests should continue to pass
because CPU.step() still executes the same handler.

Important limitation:
This returns base cycles only. Dynamic timing is intentionally out of scope here:

    branch taken penalties
    branch page-cross penalties
    indexed load page-cross penalties

Those should be modeled later as a separate step.

Out of scope:
    - refactoring OPCODE_TABLE into dataclass entries
    - adding cycles to fetch_byte()
    - Console.step()
    - PPU advancement by CPU cycles * 3
    - dynamic extra cycles
"""

import pytest

from emulator.cpu.opcodes import OPCODE_CYCLES
from tests.helpers import load_program, make_cpu_with_rom


def test_cpu_step_returns_nop_base_cycles():
    """
    Objective:
    CPU.step() returns the base cycle count for the opcode it executes.

    Example:
        NOP implied is opcode $EA and takes 2 CPU cycles.
    """
    cpu, _bus, rom = make_cpu_with_rom()
    load_program(rom, 0x8000, [0xEA])
    cpu.pc = 0x8000

    cycles = cpu.step()

    assert cycles == 2
    assert cycles == OPCODE_CYCLES[0xEA]
    assert cpu.pc == 0x8001


def test_cpu_step_returns_cycles_and_still_executes_instruction_behavior():
    """
    Objective:
    Returning cycles must not replace instruction behavior. The opcode handler
    still runs exactly as before.

    Example:
        LDA #$42 is opcode sequence $A9 $42.
        It loads A with $42 and returns 2 cycles.
    """
    cpu, _bus, rom = make_cpu_with_rom()
    load_program(rom, 0x8000, [0xA9, 0x42])
    cpu.pc = 0x8000

    cycles = cpu.step()

    assert cycles == 2
    assert cycles == OPCODE_CYCLES[0xA9]
    assert cpu.a == 0x42
    assert cpu.pc == 0x8002


def test_cpu_step_returns_different_cycles_for_different_opcodes():
    """
    Objective:
    CPU.step() should return opcode-specific timing, not a constant value.

    Example:
        JSR absolute is opcode $20 and takes 6 CPU cycles.
    """
    cpu, _bus, rom = make_cpu_with_rom()
    load_program(rom, 0x8000, [0x20, 0x00, 0x90])
    cpu.pc = 0x8000
    cpu.s = 0xFD

    cycles = cpu.step()

    assert cycles == 6
    assert cycles == OPCODE_CYCLES[0x20]
    assert cpu.pc == 0x9000


def test_cpu_step_still_raises_for_unknown_opcode():
    """
    Objective:
    Adding cycle returns must not make unsupported opcodes silently executable.

    Example:
        $02 is not implemented in the current OPCODE_TABLE. It should still raise
        NotImplementedError instead of returning OPCODE_CYCLES[$02].
    """
    cpu, _bus, rom = make_cpu_with_rom()
    load_program(rom, 0x8000, [0x02])
    cpu.pc = 0x8000

    with pytest.raises(NotImplementedError, match="Opcode 02 not implemented"):
        cpu.step()


def test_cpu_step_does_not_use_fetch_count_as_cycle_count():
    """
    Objective:
    Guard the mental model: cycles come from opcode metadata, not from how many
    bytes were fetched.

    Example:
        JSR absolute fetches 3 instruction bytes but takes 6 CPU cycles.
    """
    cpu, _bus, rom = make_cpu_with_rom()
    load_program(rom, 0x8000, [0x20, 0x00, 0x90])
    cpu.pc = 0x8000
    cpu.s = 0xFD

    cycles = cpu.step()

    assert cpu.pc == 0x9000
    assert cycles == 6
    assert cycles != 3
