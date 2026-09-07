"""Step 182: wire JMP absolute opcode $4C.

Prerequisite: step 181 added ``jmp``. In this step, add these changes in
``emulator/cpu/opcodes.py`` (including imports and table entry):

    from emulator.cpu.instructions import jmp
    from emulator.cpu.addressing_modes import absolute

    def jmp_absolute(cpu: CPU):
        addr = absolute(cpu)
        jmp(cpu, addr)

    OPCODE_TABLE = {
        # existing entries...
        0x4C: jmp_absolute,
    }

Opcode:
    0x4C -> JMP $hhhh

Goal:
create jmp_absolute(cpu), use absolute(cpu), then jmp(cpu, addr).

Student guidance:
JMP absolute is different from LDA absolute.

For LDA $1234:
    A = memory[$1234]

For JMP $1234:
    PC = $1234

So the opcode handler must not read from memory at the target address. The
absolute operand is already the new PC value.

Why this step exists:
``absolute`` consumes the two little-endian operand bytes and
returns their 16-bit value; ``jmp`` assigns it.  Invariants: one step consumes
three bytes before replacing PC, preserves flags/registers/stack/memory, and
maps only $4C.  Misconception: unlike load handlers, this handler must not read
``cpu.bus.read(addr)``.

Out of scope: JMP indirect and opcode $6C are step 183; JSR and its stack
effects are steps 184-185.
"""
import inspect

from emulator.bus.cpu_bus import CpuBus
from emulator.cpu import opcodes
from emulator.cpu.cpu import CPU
from emulator.memory.fake_rom import FakeROM


def make_cpu_with_rom():
    rom = FakeROM()
    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)
    bus = CpuBus(program_rom=rom)
    return CPU(bus), bus, rom


def test_jmp_absolute_handler_exists_and_is_in_opcode_table():
    """Objective: create jmp_absolute(cpu) and add 0x4C to OPCODE_TABLE."""
    assert hasattr(opcodes, "jmp_absolute")
    assert callable(opcodes.jmp_absolute)
    assert list(inspect.signature(opcodes.jmp_absolute).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x4C] is opcodes.jmp_absolute


def test_opcode_4C_jmp_absolute_sets_pc_to_operand_address():
    """Objective: 4C 34 12 means JMP $1234, so PC becomes $1234."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x4C)
    rom.write(0x0001, 0x34)
    rom.write(0x0002, 0x12)

    cpu.reset()
    cpu.step()

    assert cpu.pc == 0x1234


def test_opcode_4C_jmp_absolute_does_not_read_target_memory_as_new_pc():
    """
    Objective:
    JMP $1234 jumps to $1234 directly.

    It must not do:
        PC = memory[$1234]
    """
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x4C)
    rom.write(0x0001, 0x34)
    rom.write(0x0002, 0x12)
    bus.write(0x1234, 0x99)

    cpu.reset()
    cpu.step()

    assert cpu.pc == 0x1234
