"""Step 183: wire JMP indirect opcode $6C.

Prerequisites: step 180 added ``indirect`` and step 181 added ``jmp``. In this
step, add these changes to ``emulator/cpu/opcodes.py``:

    from emulator.cpu.instructions import jmp
    from emulator.cpu.addressing_modes import indirect

    def jmp_indirect(cpu: CPU):
        addr = indirect(cpu)
        jmp(cpu, addr)

    OPCODE_TABLE = {
        # existing entries...
        0x6C: jmp_indirect,
    }

Opcode:
    0x6C -> JMP ($hhhh)

Goal:
create jmp_indirect(cpu), use indirect(cpu), then jmp(cpu, addr).

Student guidance:
JMP indirect uses the operand as a pointer to the target address.

Example:
    6C 00 02 means JMP ($0200)

If:
    memory[$0200] = $34
    memory[$0201] = $12

Then:
    PC = $1234

Important:
indirect(cpu) already returns the final target address. The opcode handler must
not read memory again at that returned address.

NES/6502 bug:
If the pointer ends in $FF, the high byte wraps inside the same page:
    JMP ($02FF) reads high byte from $0200, not $0300.

Why this step exists:
``addressing_modes.indirect`` consumes the pointer operand, follows
it with the 6502 page-boundary behavior, and returns the final target; ``jmp``
then assigns it.  Invariants: the handler performs no extra target read,
preserves flags/registers/stack/memory, and maps only $6C.  Misconception: the
value returned by ``indirect`` is not another pointer.

Out of scope: implementing or changing ``addressing_modes.indirect`` belongs
to step 180. JSR starts at step 184; RTS and interrupts are later steps.
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


def test_jmp_indirect_handler_exists_and_is_in_opcode_table():
    """Objective: create jmp_indirect(cpu) and add 0x6C to OPCODE_TABLE."""
    assert hasattr(opcodes, "jmp_indirect")
    assert callable(opcodes.jmp_indirect)
    assert list(inspect.signature(opcodes.jmp_indirect).parameters) == ["cpu"]
    assert opcodes.OPCODE_TABLE[0x6C] is opcodes.jmp_indirect


def test_opcode_6C_jmp_indirect_sets_pc_to_address_stored_at_pointer():
    """Objective: 6C 00 02 means JMP ($0200), so PC becomes memory[$0200:$0201]."""
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x6C)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0200, 0x34)
    bus.write(0x0201, 0x12)

    cpu.reset()
    cpu.step()

    assert cpu.pc == 0x1234


def test_opcode_6C_jmp_indirect_does_not_read_target_memory_again():
    """
    Objective:
    indirect(cpu) returns the final target address. jmp_indirect must jump to
    that returned address directly.

    It must not do:
        target = indirect(cpu)
        PC = memory[target]
    """
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x6C)
    rom.write(0x0001, 0x00)
    rom.write(0x0002, 0x02)
    bus.write(0x0200, 0x34)
    bus.write(0x0201, 0x12)
    bus.write(0x1234, 0x99)

    cpu.reset()
    cpu.step()

    assert cpu.pc == 0x1234


def test_opcode_6C_jmp_indirect_reproduces_page_boundary_bug():
    """
    Objective:
    Reproduce the real 6502 JMP indirect page-boundary bug.

    For JMP ($02FF), the high byte is read from $0200, not $0300.
    """
    cpu, bus, rom = make_cpu_with_rom()
    rom.write(0x0000, 0x6C)
    rom.write(0x0001, 0xFF)
    rom.write(0x0002, 0x02)
    bus.write(0x02FF, 0x34)
    bus.write(0x0200, 0x12)
    bus.write(0x0300, 0x99)

    cpu.reset()
    cpu.step()

    assert cpu.pc == 0x1234
