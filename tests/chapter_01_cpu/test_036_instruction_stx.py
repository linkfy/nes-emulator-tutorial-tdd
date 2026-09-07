"""
Test 036 - Add the core STX instruction.

File to update:
    emulator/cpu/instructions.py

Location:
    instructions.stx, beside ldx

Why this step exists:
STX introduces the store counterpart to LDX. It follows the boundary established by
STA: the core instruction receives an already-resolved destination address and writes
the register through the CPU bus without changing flags.

Complete example implementation:

    # emulator/cpu/instructions.py
    def stx(cpu: CPU, address: int):
        value = cpu.x
        cpu.bus.write(address, value)

Important invariants:
    - stx receives an address, not a value
    - the written value is X and the write goes through cpu.bus.write
    - X and the processor flags remain unchanged

Common misconception:
Do not update Zero or Negative from X. Store instructions only write memory, even
when the stored byte is $00 or has bit 7 set.

Out of scope:
    - all STX opcode handlers and opcode-table entries
    - changes to addressing-mode helpers
    - cycle timing and write-side hardware effects
"""
import inspect

from emulator.cpu import instructions
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG, make_cpu


def test_stx_instruction_exists():
    """
    Objective:
    Create in instructions.py:
        def stx(cpu, address):
            ...

    Example implementation:
        value = cpu.x
        cpu.bus.write(address, value)

    Important:
    STX receives an address, not a value.
    STX does not update flags.
    """
    assert hasattr(instructions, "stx")
    assert callable(instructions.stx)
    assert list(inspect.signature(instructions.stx).parameters) == ["cpu", "address"]


def test_stx_writes_register_x_to_address():
    """
    Objective:
    stx(cpu, address) must store register X into memory.
    """
    cpu = make_cpu()
    cpu.x = 0x42

    instructions.stx(cpu, 0x0010)

    assert cpu.bus.read(0x0010) == 0x42


def test_stx_does_not_change_zero_or_negative_flags():
    """
    Objective:
    STX must not update Zero or Negative flags.
    """
    cpu = make_cpu()
    cpu.x = 0x00
    cpu.p = NEGATIVE_FLAG

    instructions.stx(cpu, 0x0010)

    assert (cpu.p & ZERO_FLAG) == 0
    assert (cpu.p & NEGATIVE_FLAG) != 0
