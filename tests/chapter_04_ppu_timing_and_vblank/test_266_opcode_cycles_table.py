"""
Validate opcode cycle metadata before changing CPU.step().

Reference:
    https://www.nesdev.org/wiki/Visual6502wiki/6502_all_256_Opcodes

File to update:
    emulator/cpu/opcodes.py

Why this intermediate step exists:
The emulator already has working opcode dispatch through:

    OPCODE_TABLE[opcode] -> handler(cpu)

We do not want to refactor that table yet, because old CPU chapter tests already
depend on the current instruction execution path.

Instead, this step introduces timing as separate metadata:

    OPCODE_CYCLES[opcode] -> base CPU cycle count

This lets a future CPU.step() return cycles without changing every instruction
handler or replacing the existing opcode dispatch table.

Suggested implementation example:
Copy this table into emulator/cpu/opcodes.py. It was created from the opcode
timing reference linked above:

OPCODE_CYCLES = [
    7,6,0,8,3,3,5,5,3,2,2,2,4,4,6,6,
    3,5,0,8,4,4,6,6,2,4,2,7,4,4,7,7,
    6,6,0,8,3,3,5,5,4,2,2,2,4,4,6,6,
    2,5,0,8,4,4,6,6,2,4,2,7,4,4,7,7,
    6,6,0,8,3,3,5,5,3,2,2,2,3,4,6,6,
    3,5,0,8,4,4,6,6,2,4,2,7,4,4,7,7,
    6,6,0,8,3,3,5,5,4,2,2,2,5,4,6,6,
    2,5,0,8,4,4,6,6,2,4,2,7,4,4,7,7,
    2,6,2,6,3,3,3,3,2,2,2,2,4,4,4,4,
    3,6,0,6,4,4,4,4,2,5,2,5,5,5,5,5,
    2,6,2,6,3,3,3,3,2,2,2,2,4,4,4,4,
    2,5,0,5,4,4,4,4,2,4,2,4,4,4,4,4,
    2,6,2,8,3,3,5,5,2,2,2,2,4,4,6,6,
    3,5,0,8,4,4,6,6,2,4,2,7,4,4,7,7,
    2,6,2,8,3,3,5,5,2,2,2,2,4,4,6,6,
    2,5,0,8,4,4,6,6,2,4,2,7,4,4,7,7
]

Important correction:
The first value must be 7 because opcode $00 is BRK, and BRK takes 7 CPU cycles.
If your copied table has 0 at index $00, fix it to 7 because this emulator already
implements BRK.

What is an opcode cycle table?
An opcode cycle table is a 256-entry lookup table where each index is an opcode
byte and each value is the base number of CPU cycles for that opcode.

Minimal example:

    OPCODE_CYCLES[0xEA] == 2   # NOP implied
    OPCODE_CYCLES[0xA9] == 2   # LDA immediate
    OPCODE_CYCLES[0x20] == 6   # JSR absolute

Common misconception:
Cycle count is not the same thing as instruction length or number of fetches.
For example, JSR is 3 bytes but takes 6 CPU cycles.

How this appears in the emulator:

    Current step shape:
        opcode = cpu.fetch_byte()
        handler = OPCODE_TABLE[opcode]
        handler(cpu)

    Future step shape, without refactoring OPCODE_TABLE:
        opcode = cpu.fetch_byte()
        handler = OPCODE_TABLE[opcode]
        handler(cpu)
        return OPCODE_CYCLES[opcode]

Important limitation:
These are base cycle counts. Some instructions later need dynamic extra cycles,
for example:

    branch taken
    branch crosses page
    indexed load crosses page

Do not solve those dynamic penalties in this step. First make the base timing
metadata explicit and testable.

Out of scope:
    - changing CPU.step() to return cycles
    - refactoring OPCODE_TABLE entries into dataclasses
    - modifying old CPU instruction tests
    - dynamic page-crossing or branch cycle penalties
    - Console.step() advancing PPU by CPU cycles * 3
"""

import pytest

from emulator.cpu.opcodes import OPCODE_CYCLES, OPCODE_TABLE


def test_opcode_cycles_table_has_one_entry_for_each_possible_opcode_byte():
    """
    Objective:
    OPCODE_CYCLES is indexable by any 8-bit opcode value from $00 to $FF.
    """
    assert len(OPCODE_CYCLES) == 256


def test_opcode_cycles_table_contains_non_negative_integer_cycle_counts():
    """
    Objective:
    Cycle metadata should be numeric and non-negative.

    A value of 0 is allowed only for unsupported/illegal opcodes in this tutorial
    table. Implemented opcodes are checked separately below.
    """
    for opcode, cycles in enumerate(OPCODE_CYCLES):
        assert isinstance(cycles, int), f"Opcode ${opcode:02X} cycle count is not int"
        assert cycles >= 0, f"Opcode ${opcode:02X} has negative cycle count"


@pytest.mark.parametrize(
    "opcode, expected_cycles, name",
    [
        (0xEA, 2, "NOP implied"),
        (0xA9, 2, "LDA immediate"),
        (0xA5, 3, "LDA zero page"),
        (0xAD, 4, "LDA absolute"),
        (0x20, 6, "JSR absolute"),
        (0x60, 6, "RTS implied"),
        (0x40, 6, "RTI implied"),
        (0x00, 7, "BRK implied"),
    ],
)
def test_opcode_cycles_table_matches_known_base_cycles(opcode, expected_cycles, name):
    """
    Objective:
    Lock a few well-known official opcode timings before CPU.step() starts using
    the table.
    """
    assert OPCODE_CYCLES[opcode] == expected_cycles, name


def test_every_implemented_opcode_has_nonzero_base_cycles():
    """
    Objective:
    If an opcode exists in OPCODE_TABLE, CPU.step() can eventually return a useful
    nonzero base cycle count for it.

    This keeps unsupported opcodes and implemented opcodes clearly separated:

        unsupported opcode may have 0 cycles
        implemented opcode must have > 0 cycles
    """
    implemented_opcodes_with_zero_cycles = [
        opcode
        for opcode in OPCODE_TABLE
        if OPCODE_CYCLES[opcode] == 0
    ]

    assert implemented_opcodes_with_zero_cycles == []


def test_unsupported_opcode_can_remain_zero_cycles_for_now():
    """
    Objective:
    This timing table does not force implementation of every 6502 opcode.

    Example:
        $02 is an unofficial/illegal opcode and is not part of the current
        OPCODE_TABLE. It may remain 0 in OPCODE_CYCLES.
    """
    assert 0x02 not in OPCODE_TABLE
    assert OPCODE_CYCLES[0x02] == 0
