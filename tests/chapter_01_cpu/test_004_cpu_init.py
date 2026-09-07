"""
Test 004 — Create basic CPU state and fetch helpers.

File to update:
    emulator/cpu/cpu.py

Location:
    class CPU

Reference:
    https://www.nesdev.org/wiki/CPU_registers

Why this step exists:
The CPU needs explicit registers and a bus dependency before it can fetch or execute
instructions. Fetching advances the program counter because instruction bytes are
consumed sequentially.

Complete example implementation:

    from dataclasses import dataclass

    from emulator.bus.cpu_bus import CpuBus


    @dataclass
    class CPU:
        bus: CpuBus
        a: int = 0
        x: int = 0
        y: int = 0
        pc: int = 0
        s: int = 0
        p: int = 0

        def fetch_byte(self) -> int:
            value = self.bus.read(self.pc)
            self.pc += 1
            return value

        def fetch_word(self) -> int:
            low = self.fetch_byte()
            high = self.fetch_byte()
            return low | (high << 8)

Important invariants:
    - CPU retains the exact bus object supplied by its caller
    - fetch_byte advances PC by one
    - fetch_word consumes low byte first and advances PC by two

Common misconception:
Little-endian storage changes byte order in memory, not the numeric result. Bytes
$34 then $12 produce the integer $1234.

Out of scope:
    - reset-vector behavior
    - opcode decoding
    - hardware-accurate power-up register values
"""
import pytest
from emulator.bus.cpu_bus import CpuBus
from emulator.cpu.cpu import CPU


@pytest.fixture(scope="session")
def cpu():
    bus = CpuBus()
    default_cpu = CPU(bus)
    return default_cpu

def test_cpu_can_be_created():
    bus = CpuBus()
    cpu = CPU(bus)
    assert cpu.bus is bus

def test_cpu_has_registers(cpu):
    assert hasattr(cpu, "a") # Accumulator register
    assert hasattr(cpu, "x") # Index register X
    assert hasattr(cpu, "y") # Index register Y
    assert hasattr(cpu, "pc") # program counter
    assert hasattr(cpu, "s") # stack register
    assert hasattr(cpu, "p") # status register (Flags)

def test_cpu_registers_are_initialized_to_0(cpu):
    """ Initial register values set to 0
    Later on future tests we will implement cpu.reset() that put the starting values
    """
    assert (cpu.a, cpu.x, cpu.y, cpu.pc, cpu.s, cpu.p) == (0, 0, 0, 0, 0, 0)

def test_cpu_fetch_byte(cpu):
    cpu.pc = 0 # Temporal PC value for testing
    """Get current value from register PC and then pc+=1"""
    cpu.bus.write(0x0000, 0x42)

    value = cpu.fetch_byte()

    assert value == 0x42
    assert cpu.pc == 1


def test_cpu_fetch_word(cpu):
    cpu.pc = 0 # Temporal PC value for testing
    cpu.bus.write(0x0000, 0x34)
    cpu.bus.write(0x0001, 0x12) # Write 0x34 , 0x12 (Little endian 0x1234)

    assert cpu.fetch_word() == 0x1234
