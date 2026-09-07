"""
Test 088 - Add memory-targeted ASL behavior.

In this step, add the reusable memory instruction. Accumulator behavior is
Test 089, and opcode wrappers start at Test 090.

Production location and symbol:
    emulator/cpu/instructions.py: `asl(cpu: CPU, addr: int)`

Why this step exists:
Memory ASL is a read-modify-write operation. The instruction function receives
an already resolved address so later opcode handlers can share the same logic.

Suggested implementation:

    def asl(cpu: CPU, addr: int):
        value = cpu.bus.read(addr)
        result = value << 1
        result_8 = result & 0xFF

        # Set flags
        cpu.flags.set_carry_flag((value & 0b1000_0000) != 0)
        cpu.flags.set_negative_flag((result_8 & 0b1000_0000) != 0)
        cpu.flags.set_zero_flag(result_8 == 0)

        cpu.bus.write(addr, result_8)

Important invariants:
    - Carry receives old bit 7, before the result is masked
    - Zero and Negative reflect the final 8-bit result
    - exactly the supplied address is read and written; A is unchanged
    - all status bits other than C, Z, and N are preserved

Common misconception:
Carry does not come from the shifted result's bit 7; it captures the bit shifted
out of the original value.

Out of scope:
    - accumulator-specific `asl_a` (test 089)
    - opcode 0x0A and memory addressing wrappers (tests 090-094)
    - cycle timing and bus-accurate dummy writes
"""

from emulator.cpu.instructions import asl
from tests.helpers import NEGATIVE_FLAG, ZERO_FLAG, make_cpu


CARRY_FLAG = 1 << 0


def test_asl_memory_shifts_value_left_and_writes_result_back():
    """Objective: memory value 0b0000_0011 becomes 0b0000_0110."""
    cpu = make_cpu()
    cpu.bus.write(0x0020, 0b0000_0011)

    asl(cpu, 0x0020)

    assert cpu.bus.read(0x0020) == 0b0000_0110


def test_asl_memory_sets_carry_from_old_bit_7():
    """Objective: old bit 7 is moved into Carry before the 8-bit wrap."""
    cpu = make_cpu()
    cpu.bus.write(0x0020, 0b1000_0001)

    asl(cpu, 0x0020)

    assert cpu.bus.read(0x0020) == 0b0000_0010
    assert (cpu.p & CARRY_FLAG) != 0


def test_asl_memory_clears_carry_when_old_bit_7_was_clear():
    """Objective: Carry is cleared when the original value did not have bit 7 set."""
    cpu = make_cpu()
    cpu.p |= CARRY_FLAG
    cpu.bus.write(0x0020, 0b0100_0000)

    asl(cpu, 0x0020)

    assert cpu.bus.read(0x0020) == 0b1000_0000
    assert (cpu.p & CARRY_FLAG) == 0


def test_asl_memory_sets_zero_flag_when_result_is_zero():
    """Objective: 0x80 << 1 becomes 0x00 and sets Zero flag."""
    cpu = make_cpu()
    cpu.bus.write(0x0020, 0x80)

    asl(cpu, 0x0020)

    assert cpu.bus.read(0x0020) == 0x00
    assert (cpu.p & ZERO_FLAG) != 0
    assert (cpu.p & NEGATIVE_FLAG) == 0


def test_asl_memory_sets_negative_flag_from_result_bit_7():
    """Objective: 0x40 << 1 becomes 0x80, so Negative flag is set."""
    cpu = make_cpu()
    cpu.bus.write(0x0020, 0x40)

    asl(cpu, 0x0020)

    assert cpu.bus.read(0x0020) == 0x80
    assert (cpu.p & NEGATIVE_FLAG) != 0
    assert (cpu.p & ZERO_FLAG) == 0
