"""
Test 010 — Update Zero and Negative flags after immediate LDA.

File to update:
    emulator/cpu/cpu.py

Location:
    CPU.step, inside the existing $A9 immediate-LDA branch

Why this step exists:
The 6502 records whether an LDA result is zero and whether bit 7 is set. Later branch
instructions consume these status bits, so both setting and clearing must work.

Complete example implementation:

    class CPU:
        # Keep the existing methods from Tests 004, 008, and 009.

        def step(self) -> None:
            opcode = self.fetch_byte()

            if opcode == 0xA9:
                self.a = self.fetch_byte()

                if self.a == 0:
                    self.p |= 1 << 1
                else:
                    self.p &= ~(1 << 1)

                if self.a & (1 << 7):
                    self.p |= 1 << 7
                else:
                    self.p &= ~(1 << 7)

                return

            raise NotImplementedError(
                f"Opcode ${opcode:02X} is not implemented"
            )

Result table:
    A=$00 -> Z=1, N=0
    A=$7F -> Z=0, N=0
    A=$80 -> Z=0, N=1

Important invariant:
Only the Zero and Negative bits are changed; reset's Interrupt Disable bit and every
other status bit retain their previous values.

Common misconception:
"Negative" does not perform signed arithmetic here. It means that bit 7 of the
8-bit result is set.

Out of scope:
    - named flag constants and the shared helper, introduced in Test 012
    - absolute and zero-page LDA
    - instruction cycle counts
"""

from emulator.cpu.cpu import CPU
from emulator.bus.cpu_bus import CpuBus
from emulator.memory.fake_rom import FakeROM

def test_lda_clears_zero_flag():
    """Now it's time configure LDA flags
    Ensure that zero flag is unset (clear)

    If result == 0 -> Flag Zero is set 

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
    
    Pseudocode:
    if LDA:
      if self.a == 0:
        set flag Z
     else: 
        clear flag Z

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
    assert (cpu.p & (1 << 1)) == 0 # Flag Zero is clear (0)


def test_lda_sets_zero_flag():
    """
    Ensure that zero flag is set

    if self.a == 0 -> set flag Z else Z is cleared
    Pseudocode:
    if LDA:
     if self.a == 0:
        set flag Z
     else: 
        clear flag Z

    """
    rom = FakeROM()
    
    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)

    rom.write(0x0000, 0xA9)
    rom.write(0x0001, 0x00)

    bus = CpuBus(program_rom=rom)
    cpu = CPU(bus)

    cpu.reset()
    cpu.step() 

    assert cpu.a == 0x00
    assert (cpu.p & (1 << 1)) != 0 # Flag Zero is set

def test_lda_sets_negative_flag():
    """
    Ensure that Negastive Flag is set on bit 7 active
    for cpu.a
    """
    rom = FakeROM()
    
    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)
                            #        bit 7
    rom.write(0x0000, 0xA9) #         v
    rom.write(0x0001, 0x80) # 0x80 = b1000_0000

    bus = CpuBus(program_rom=rom)
    cpu = CPU(bus)

    cpu.reset()
    cpu.step()

    assert cpu.a == 0x80
    assert (cpu.p & ( 1 << 7 )) != 0 # N 


def test_lda_clears_negative_flag():
    """
    Ensure that Negastive Flag is unset on bit 7 inactive
    for cpu.a
    """
    rom = FakeROM()
    
    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)
                            #        bit 7
    rom.write(0x0000, 0xA9) #         v
    rom.write(0x0001, 0x7F) # 0x00 = b0111_1111

    bus = CpuBus(program_rom=rom)
    cpu = CPU(bus)

    cpu.reset()
    cpu.step()

    assert cpu.a == 0x7F
    assert (cpu.p & ( 1 << 7 )) == 0 # N = 0
