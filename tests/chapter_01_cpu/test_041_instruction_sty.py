"""
Test 041 - Add the core STY instruction.

File to update:
    emulator/cpu/instructions.py

Location:
    instructions.sty, beside ldy

Why this step exists:
STY completes the Y-register instruction pair. Like STA and STX, it receives an
already-resolved destination address and writes the register through the CPU bus.

Complete example implementation:

    # emulator/cpu/instructions.py
    def sty(cpu: CPU, address: int):
        value = cpu.y
        cpu.bus.write(address, value)

Important invariants:
    - sty receives an address, not a value
    - the value written is Y and the write goes through cpu.bus.write
    - Y and the processor flags remain unchanged

Common misconception:
Do not call `cpu._update_zero_and_negative_flags`; store instructions do not derive
flags from the byte they write, even when Y is $00 or has bit 7 set.

Out of scope:
    - all STY opcode handlers and opcode-table entries
    - adding or changing addressing-mode helpers
    - cycle timing and write-side hardware effects
"""
import inspect

from emulator.cpu import instructions
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG, make_cpu


def test_sty_instruction_exists():
    """
    Objective:
    Create in instructions.py:
        def sty(cpu, address):
            ...

    Example implementation:
        value = cpu.y
        cpu.bus.write(address, value)

    Important:
    STY receives an address, not a value.
    STY does not update flags.
    """
    assert hasattr(instructions, "sty")
    assert callable(instructions.sty)
    assert list(inspect.signature(instructions.sty).parameters) == ["cpu", "address"]


def test_sty_writes_register_y_to_address():
    """Objective: sty(cpu, address) must store register Y into memory."""
    cpu = make_cpu()
    cpu.y = 0x42

    instructions.sty(cpu, 0x0010)

    assert cpu.bus.read(0x0010) == 0x42


def test_sty_does_not_change_zero_or_negative_flags():
    """Objective: STY must not update Zero or Negative flags."""
    cpu = make_cpu()
    cpu.y = 0x00
    cpu.p = NEGATIVE_FLAG

    instructions.sty(cpu, 0x0010)

    assert (cpu.p & ZERO_FLAG) == 0
    assert (cpu.p & NEGATIVE_FLAG) != 0
