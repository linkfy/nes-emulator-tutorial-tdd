"""
Add Indirect addressing for JMP.

Create one function inside emulator/cpu/addressing_modes.py:

    def indirect(cpu):
        ...

Why this step exists:
JMP needs this special addressing mode to resolve an indirect target from the
16-bit pointer encoded by ``JMP ($hhhh)``.

Student guidance:
This is different from indirect_x(cpu) and indirect_y(cpu).

JMP indirect uses a 16-bit operand as a pointer anywhere in memory:

    JMP ($0200)

Step by step:
    1. Fetch the 16-bit pointer operand from the instruction stream.
       Example bytes: 00 02 -> pointer address $0200.

    2. Read the low byte of the target from memory[pointer].
       Example: memory[$0200] = $34.

    3. Read the high byte of the target from memory[pointer + 1].
       Example: memory[$0201] = $12.

    4. Return the final target address.
       Example: $1234.

Important hardware bug:
The 6502 has a JMP indirect page-boundary bug.

If the pointer ends in $FF, the high byte is read from the same page instead of
the next page:

    JMP ($02FF)

Real CPU reads:
    low  = memory[$02FF]
    high = memory[$0200]

It does NOT read high from $0300.

Useful implementation shape:

    ptr = cpu.fetch_word()
    low = cpu.bus.read(ptr)
    high_addr = (ptr & 0xFF00) | ((ptr + 1) & 0x00FF)
    high = cpu.bus.read(high_addr)
    return low | (high << 8)
"""
import inspect

from emulator.bus.cpu_bus import CpuBus
from emulator.cpu import addressing_modes
from emulator.cpu.cpu import CPU
from emulator.memory.fake_rom import FakeROM


def make_cpu_with_rom():
    rom = FakeROM()
    rom.write(0x7FFC, 0x00)
    rom.write(0x7FFD, 0x80)
    bus = CpuBus(program_rom=rom)
    return CPU(bus), bus, rom


def test_indirect_addressing_mode_exists():
    """
    Objective:
    Create in addressing_modes.py:
        def indirect(cpu):
            ...

    What it does:
    - Fetch a 16-bit pointer operand from the instruction stream.
    - Read a 16-bit target address from memory through that pointer.
    - Return the target address.

    Important:
    This function returns the address. It does not assign cpu.pc directly.
    JMP will use the returned address later.
    """
    assert hasattr(addressing_modes, "indirect")
    assert callable(addressing_modes.indirect)
    assert list(inspect.signature(addressing_modes.indirect).parameters) == ["cpu"]


def test_indirect_fetches_pointer_and_reads_target_address():
    """
    Objective:
    If the instruction operand is $0200, and memory[$0200:$0201] contains
    low=$34 and high=$12, indirect(cpu) returns $1234.

    Instruction stream example:
        00 02   -> pointer $0200

    Memory example:
        RAM[$0200] = $34
        RAM[$0201] = $12

    Result:
        target = $1234
    """
    cpu, bus, rom = make_cpu_with_rom()

    cpu.reset()
    rom.write(0x0000, 0x00)
    rom.write(0x0001, 0x02)
    bus.write(0x0200, 0x34)
    bus.write(0x0201, 0x12)

    target = addressing_modes.indirect(cpu)

    assert target == 0x1234
    assert cpu.pc == 0x8002


def test_indirect_uses_little_endian_target_bytes():
    """
    Objective:
    The target address stored in memory is little-endian.

    That means:
        low byte first
        high byte second

    Example:
        memory[$0300] = $CD
        memory[$0301] = $AB

    Target:
        $ABCD
    """
    cpu, bus, rom = make_cpu_with_rom()

    cpu.reset()
    rom.write(0x0000, 0x00)
    rom.write(0x0001, 0x03)
    bus.write(0x0300, 0xCD)
    bus.write(0x0301, 0xAB)

    target = addressing_modes.indirect(cpu)

    assert target == 0xABCD
    assert cpu.pc == 0x8002


def test_indirect_reproduces_jmp_page_boundary_bug():
    """
    Objective:
    Reproduce the real 6502 JMP indirect bug.

    If the pointer address ends in $FF, the CPU reads the high byte from the
    beginning of the same page, not from the next page.

    Example:
        pointer = $02FF

    Real CPU reads:
        low  = memory[$02FF]
        high = memory[$0200]

    It does NOT read:
        high = memory[$0300]

    This is required for NES accuracy.
    """
    cpu, bus, rom = make_cpu_with_rom()

    cpu.reset()
    rom.write(0x0000, 0xFF)
    rom.write(0x0001, 0x02)
    bus.write(0x02FF, 0x34)
    bus.write(0x0200, 0x12)
    bus.write(0x0300, 0x99)

    target = addressing_modes.indirect(cpu)

    assert target == 0x1234
    assert cpu.pc == 0x8002


def test_indirect_does_not_force_all_high_byte_reads_to_zero_page():
    """
    Objective:
    Normal pointers must read the high byte from pointer + 1 in the same 16-bit
    address range.

    This prevents a common bug:
        high = cpu.bus.read((ptr + 1) & 0xFF)

    That would incorrectly read from zero page for normal pointers.

    Example:
        pointer = $0400
        high byte must come from $0401, not $0001.
    """
    cpu, bus, rom = make_cpu_with_rom()

    cpu.reset()
    rom.write(0x0000, 0x00)
    rom.write(0x0001, 0x04)
    bus.write(0x0400, 0x78)
    bus.write(0x0401, 0x56)
    bus.write(0x0001, 0x99)

    target = addressing_modes.indirect(cpu)

    assert target == 0x5678
    assert cpu.pc == 0x8002
