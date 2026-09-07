"""
Test 016 — Replace CPU.step branches with an opcode table.

File to create:
    emulator/cpu/opcodes.py

File to update:
    emulator/cpu/cpu.py

Locations:
    opcodes.lda_immediate
    opcodes.lda_zero_page
    opcodes.lda_absolute
    opcodes.OPCODE_TABLE
    CPU.step

Why this step exists:
Direct branches work for three opcodes but scale poorly across the 6502 instruction
set. A table makes byte-to-handler dispatch data-driven while retaining the existing
addressing and instruction boundaries.

Complete example implementation:

    # emulator/cpu/opcodes.py
    from emulator.cpu.addressing_modes import absolute, immediate, zero_page
    from emulator.cpu.instructions import lda


    def lda_immediate(cpu) -> None:
        lda(cpu, immediate(cpu))


    def lda_zero_page(cpu) -> None:
        address = zero_page(cpu)
        lda(cpu, cpu.bus.read(address))


    def lda_absolute(cpu) -> None:
        address = absolute(cpu)
        lda(cpu, cpu.bus.read(address))


    OPCODE_TABLE = {
        0xA9: lda_immediate,
        0xA5: lda_zero_page,
        0xAD: lda_absolute,
    }


    # emulator/cpu/cpu.py
    from emulator.cpu.opcodes import OPCODE_TABLE


    class CPU:
        def step(self) -> None:
            opcode = self.fetch_byte()
            handler = OPCODE_TABLE.get(opcode)

            if handler is None:
                raise NotImplementedError(
                    f"Opcode ${opcode:02X} is not implemented"
                )

            return handler(self)

Important boundary:
CPU.step dispatches; an opcode handler coordinates addressing, memory access, and the
instruction; `lda` performs the register-and-flags state transition.

Common misconception:
An opcode handler is not the same as an instruction. Three LDA opcodes share one `lda`
instruction but use different operand acquisition mechanisms.

Out of scope:
    - indexed LDA handlers
    - cycle-count return values
    - a generic instruction decoder object
"""
import inspect
from pathlib import Path

from emulator.cpu import opcodes
from emulator.cpu.cpu import CPU


def test_opcodes_file_exists():
    """
    Objective:
    Create this file:

        emulator/cpu/opcodes.py

    Why:
    CPU.step() should not grow with many if/elif blocks.
    The opcode table will connect opcode bytes with opcode handlers.

    Example:
        0xA9 means LDA Immediate.
        0xA5 means LDA Zero Page.
        0xAD means LDA Absolute.
    """
    assert Path("emulator/cpu/opcodes.py").exists()


def test_lda_opcode_handlers_exist():
    """
    Objective:
    Create these opcode handlers inside opcodes.py:

        def lda_immediate(cpu):
            lda(cpu, immediate(cpu))

        def lda_zero_page(cpu):
            addr = zero_page(cpu)
            value = cpu.bus.read(addr)
            lda(cpu, value)

        def lda_absolute(cpu):
            addr = absolute(cpu)
            value = cpu.bus.read(addr)
            lda(cpu, value)

    Important idea:
    Opcode handlers include decoding/addressing details.
    They are not the same as instructions.

    Example:
    lda(cpu, value) only changes register A and flags.
    lda_zero_page(cpu) gets the zero page address, reads memory,
    and then calls lda(cpu, value).
    """
    assert hasattr(opcodes, "lda_immediate")
    assert callable(opcodes.lda_immediate)
    assert list(inspect.signature(opcodes.lda_immediate).parameters) == ["cpu"]

    assert hasattr(opcodes, "lda_zero_page")
    assert callable(opcodes.lda_zero_page)
    assert list(inspect.signature(opcodes.lda_zero_page).parameters) == ["cpu"]

    assert hasattr(opcodes, "lda_absolute")
    assert callable(opcodes.lda_absolute)
    assert list(inspect.signature(opcodes.lda_absolute).parameters) == ["cpu"]


def test_opcode_table_exists_and_maps_lda_opcodes_to_handlers():
    """
    Objective:
    Create OPCODE_TABLE inside opcodes.py.

    Example:
        OPCODE_TABLE = {
            0xA9: lda_immediate,
            0xA5: lda_zero_page,
            0xAD: lda_absolute,
        }

    Why:
    CPU.step() can fetch one opcode byte and ask the table which function
    should run.
    """
    assert hasattr(opcodes, "OPCODE_TABLE")
    assert isinstance(opcodes.OPCODE_TABLE, dict)

    assert opcodes.OPCODE_TABLE[0xA9] is opcodes.lda_immediate
    assert opcodes.OPCODE_TABLE[0xA5] is opcodes.lda_zero_page
    assert opcodes.OPCODE_TABLE[0xAD] is opcodes.lda_absolute


def test_cpu_step_uses_opcode_table():
    """
    Objective:
    Refactor CPU.step() so it uses OPCODE_TABLE.

    CPU.step() should follow this shape:

        def step(self):
            opcode = self.fetch_byte()
            handler = OPCODE_TABLE.get(opcode) # Returns None if not exists
            if handler is None:
                raise NotImplementedError(f"Opcode {opcode:02X} not implemented")
             
            handler(self)

    Why:
    CPU.step() is now responsible for:
    - fetch opcode
    - find handler
    - run handler

    The opcode handler is responsible for:
    - use the addressing mode
    - read/write memory if needed
    - call the instruction
    """
    step_source = inspect.getsource(CPU.step)

    assert "OPCODE_TABLE.get(opcode)" in step_source
    assert "handler is None" in step_source
    assert "NotImplementedError" in step_source
    assert "handler(self)" in step_source
