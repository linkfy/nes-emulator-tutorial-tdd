"""
Test 009 — Execute the first opcode: immediate LDA ($A9).

File to update:
    emulator/cpu/cpu.py

Location:
    CPU.step

Reference:
    https://www.nesdev.org/wiki/Instruction_reference#LDA

Why this step exists:
CPU.step introduces the minimum fetch-decode-execute loop. Immediate LDA reads the
byte directly following opcode $A9 and stores it in accumulator A.

Complete example implementation:

    class CPU:
        # Keep the state, fetch, and reset behavior from earlier tests.

        def step(self) -> None:
            opcode = self.fetch_byte()

            if opcode == 0xA9:
                self.a = self.fetch_byte()
                return

            raise NotImplementedError(
                f"Opcode ${opcode:02X} is not implemented"
            )

Execution timeline:
    PC=$8000 -> fetch $A9 -> PC=$8001
    PC=$8001 -> fetch operand $42 -> PC=$8002 -> A=$42

Important invariants:
    - one step executes exactly one instruction
    - an unknown opcode fails visibly
    - immediate LDA consumes two bytes in total

Common misconception:
The operand $42 is a value, not an address. Immediate mode does not perform another
bus lookup using $0042.

Out of scope:
    - Zero and Negative flag updates, introduced in Test 010
    - other LDA addressing modes
    - opcode tables and cycle counts
"""

from emulator.cpu.cpu import CPU
from emulator.bus.cpu_bus import CpuBus
from emulator.memory.fake_rom import FakeROM


def test_lda_inmediate_without_flags():
    """This is yout first opcode resoultion.
    You should define a step function inside CPU
    cpu.step() and implement opcode LDA 0xA9
    It should: 
        - Fetch opcode [fetch_byte]
        - Decode opcode [if opcode == 0xA9 ... then ... return]
        - raise NotImplementedError if Opcode Not Implemented
    
    Baby steps:
    
    def step(self) -> None:
        opcode = self.fetch_byte()

        if opcode == 0xA9
            self.a = self.fetch_byte()
            return
        raise NotImplementedError(f"{opcode:02X} not implemented")

    LDA Reference:
    https://www.nesdev.org/wiki/Instruction_reference#LDA
    """
    
    # Current flow CPU Status: Reset -> Fetch -> Decode
    rom = FakeROM()
    
    # Reset Vector
    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)

    # LDA #$42
    rom.write(0x0000, 0xA9)
    rom.write(0x0001, 0x42)

    bus = CpuBus(program_rom=rom)
    cpu = CPU(bus)

    cpu.reset()
    cpu.step() # LDA should fetch_byte and put it on register A

    assert cpu.a == 0x42

def test_lda_flags():
    """Now it's time configure LDA flags
    If result == 0 -> Flag Zero is set 
    If result is negative -> Flag N is set 

    7  bit  0
    ---- ----
    NV1B DIZC
    |||| ||||
    |||| |||+- Carry
    |||| ||+-- Zero
    |||| |+--- Interrupt Disable
    |||| +---- Decimal
    |||+------ (No CPU effect; see: the B flag)
    ||+------- (No CPU effect; always pushed as 1)
    |+-------- Overflow
    +--------- Negative
    """
    rom = FakeROM()
    
    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)

    rom.write(0x0000, 0xA9)
    rom.write(0x0001, 0x42)

    bus = CpuBus(program_rom=rom)
    cpu = CPU(bus)

    cpu.reset()
    cpu.step() 

    assert cpu.a == 0x42
