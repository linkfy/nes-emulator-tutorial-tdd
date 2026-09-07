"""
Test 013 — Extract immediate and absolute addressing modes.

Files to update:
    emulator/cpu/addressing_modes.py
    emulator/cpu/cpu.py

Locations:
    addressing_modes.immediate
    addressing_modes.absolute
    CPU.step, existing $A9 and $AD branches

Why this step exists:
Addressing modes determine where an instruction gets its operand. Separating that
mechanism keeps CPU.step focused on opcode selection while preserving the behavior
already established for immediate and absolute LDA.

Complete example implementation:

    # emulator/cpu/addressing_modes.py
    def immediate(cpu) -> int:
        return cpu.fetch_byte()


    def absolute(cpu) -> int:
        return cpu.fetch_word()


    # emulator/cpu/cpu.py
    from emulator.cpu.addressing_modes import absolute, immediate


    class CPU:
        def step(self) -> None:
            opcode = self.fetch_byte()

            if opcode == 0xA9:
                self.a = immediate(self)
            elif opcode == 0xAD:
                address = absolute(self)
                self.a = self.bus.read(address)
            else:
                raise NotImplementedError(
                    f"Opcode ${opcode:02X} is not implemented"
                )

            self._update_zero_and_negative_flags(self.a)

Important distinction:
`immediate(cpu)` returns a value. `absolute(cpu)` returns an address that the opcode
path must dereference through the bus.

Common misconception:
Do not make every addressing mode return a loaded value. Store instructions will also
need addresses, so address-producing modes should remain independent of LDA.

Out of scope:
    - instructions.lda, introduced in Test 014
    - zero-page and indexed addressing
    - an opcode table
"""
import inspect

from emulator.cpu import addressing_modes
from tests.helpers import make_cpu


def test_immediate_addressing_mode_exists():
    """
    Objective:
    Move the immediate mode code from CPU.step() to this function.

    Create in addressing_modes.py:
        def immediate(cpu):
            ...

    What it does:
    - Read the next byte from the CPU bus.
    - Move PC to the next position.
    - Return that byte.

    Example:
    A9 42 means LDA #$42.
    The value 0x42 is just after the opcode.
    """
    cpu = make_cpu()

    assert hasattr(addressing_modes, "immediate")
    assert callable(addressing_modes.immediate)
    assert list(inspect.signature(addressing_modes.immediate).parameters) == ["cpu"]
    assert cpu is not None


def test_absolute_addressing_mode_exists():
    """
    Objective:
    Move the absolute mode code from CPU.step() to this function.

    Create in addressing_modes.py:
        def absolute(cpu):
            ...

    What it does:
    - Read the next two bytes from the CPU bus.
    - The first byte is low.
    - The second byte is high.
    - Return the final address without reading from it.

    Example:
    AD 34 12 means LDA $1234.
    The function must return address 0x1234.
    """
    cpu = make_cpu()

    assert hasattr(addressing_modes, "absolute")
    assert callable(addressing_modes.absolute)
    assert list(inspect.signature(addressing_modes.absolute).parameters) == ["cpu"]
    assert cpu is not None
