"""Step 210: verify the completed CPU instruction slice.

In this step, integrate existing ``emulator/cpu/cpu.py::CPU.reset``/``CPU.step``,
``emulator/cpu/opcodes.py::OPCODE_TABLE``, instruction symbols ``lda``, ``ldx``,
``ldy``, ``sta``, ``stx``, ``sty``, ``adc``, ``sbc``, ``inc``, ``dec``,
``and_a``, ``or_a``, ``or_e``, ``bit``, ``cmp``, ``beq``, ``bne``, ``pha``,
``pla``, ``php``, ``plp``, ``asl_a``, ``lsr_a``, ``rol_a``, ``ror_a``, ``tax``,
``txa``, ``tay``, ``tya``, ``txs``, ``tsx``, ``inx``, ``dex``, ``iny``, ``dey``,
``jsr``, ``rts``, ``clc``, ``sec``, ``cld``, ``sed``, ``clv``, ``cli``, ``sei``,
and ``nop`` in ``emulator/cpu/instructions.py``, plus
``emulator/bus/cpu_bus.py::CpuBus.read``/``write`` and
``emulator/memory/fake_rom.py::FakeROM.read``/``write``.

The complete transition is test support, added to ``tests/helpers.py``::

    from emulator.memory.fake_rom import FakeROM

    def make_cpu_with_rom():
        rom = FakeROM()
        bus = CpuBus(program_rom=rom)
        return CPU(bus), bus, rom

    def write_reset_vector(rom, addr: int):
        rom.write(0x7FFC, addr & 0xFF)
        rom.write(0x7FFD, (addr >> 8) & 0xFF)

    def load_program(rom, start_addr: int, program: list[int]):
        for offset, byte in enumerate(program):
            rom.write((start_addr - 0x8000) + offset, byte)

Why this step exists:
Although this validation adds no production implementation, short byte programs
expose integration defects hidden by direct
operation tests.  Invariants include sequential PC ownership by CPU.step,
balanced stack round trips, branch targets relative to post-operand PC,
preservation of unrelated flags, and RAM writes at the addressed locations.
The misconception is that passing isolated instruction tests proves dispatch,
PC, stack, and flag interactions also compose correctly.

Out of scope: the trace formatter is step 211. The iNES reader, cartridge/NROM
mapping, PPU, VBlank, and NMI belong to later steps and must not be anticipated
here.
"""

from tests.helpers import (
    NEGATIVE_FLAG,
    ZERO_FLAG,
    load_program,
    make_cpu_with_rom,
    write_reset_vector,
)


CARRY_FLAG = 1 << 0
DECIMAL_FLAG = 1 << 3
OVERFLOW_FLAG = 1 << 6
STACK_BASE = 0x0100


def prepare_cpu(program, start_addr=0x8000):
    cpu, bus, rom = make_cpu_with_rom()
    write_reset_vector(rom, start_addr)
    load_program(rom, start_addr, program)
    cpu.reset()
    return cpu, bus, rom


def run_steps(cpu, count: int):
    for _ in range(count):
        cpu.step()


def test_CPU_VERIFICATION_stack_roundtrip_program():
    """
    Final boss objective:
    Execute a real stack roundtrip program.

    Program:
        LDA #$42
        PHA
        LDA #$00
        PLA
        NOP

    Expected:
        A returns to $42 after PLA.
        Stack pointer returns to reset value $FD.
        Zero and Negative reflect $42.
    """
    cpu, bus, rom = prepare_cpu([
        0xA9, 0x42,  # LDA #$42
        0x48,        # PHA
        0xA9, 0x00,  # LDA #$00
        0x68,        # PLA
        0xEA,        # NOP
    ])

    run_steps(cpu, 5)

    assert cpu.a == 0x42
    assert cpu.s == 0xFD
    assert cpu.flags.get_zero_flag() is False
    assert cpu.flags.get_negative_flag() is False
    assert cpu.pc == 0x8007


def test_CPU_VERIFICATION_subroutine_program():
    """
    Final boss objective:
    Execute JSR/RTS as a real program flow.

    Program:
        $8000: JSR $8007
        $8003: LDA #$02
        $8005: NOP
        $8006: NOP
        $8007: LDA #$01
        $8009: RTS

    Expected:
        Subroutine first sets A to $01.
        RTS returns to $8003.
        Main code then sets A to $02.
    """
    cpu, bus, rom = prepare_cpu([
        0x20, 0x07, 0x80,  # JSR $8007
        0xA9, 0x02,        # LDA #$02
        0xEA,              # NOP
        0xEA,              # NOP padding before subroutine
        0xA9, 0x01,        # LDA #$01
        0x60,              # RTS
    ])

    run_steps(cpu, 4)

    assert cpu.a == 0x02
    assert cpu.s == 0xFD
    assert cpu.pc == 0x8005


def test_CPU_VERIFICATION_branch_program_skips_instruction():
    """
    Final boss objective:
    Execute a real conditional branch.

    Program:
        LDA #$00      ; sets Zero
        BEQ +2        ; skip LDA #$01
        LDA #$01      ; must be skipped
        LDA #$03      ; branch target

    Expected:
        A = $03, proving the branch target was used.
    """
    cpu, bus, rom = prepare_cpu([
        0xA9, 0x00,  # LDA #$00
        0xF0, 0x02,  # BEQ +2
        0xA9, 0x01,  # LDA #$01
        0xA9, 0x03,  # LDA #$03
    ])

    run_steps(cpu, 3)

    assert cpu.a == 0x03
    assert cpu.flags.get_zero_flag() is False
    assert cpu.pc == 0x8008


def test_CPU_VERIFICATION_loop_program_with_dex_and_bne():
    """
    Final boss objective:
    Execute a tiny loop using DEX and BNE.

    Program:
        LDX #$03
        DEX
        BNE -3
        STX $10

    Expected:
        X counts down to $00.
        BNE stops branching when Zero is set by DEX.
        STX stores $00 into RAM address $0010.
    """
    cpu, bus, rom = prepare_cpu([
        0xA2, 0x03,  # LDX #$03
        0xCA,        # DEX
        0xD0, 0xFD,  # BNE -3, back to DEX at $8002
        0x86, 0x10,  # STX $10
    ])

    run_steps(cpu, 8)

    assert cpu.x == 0x00
    assert cpu.flags.get_zero_flag() is True
    assert bus.read(0x0010) == 0x00
    assert cpu.pc == 0x8007


def test_CPU_VERIFICATION_flag_control_program():
    """
    Final boss objective:
    Execute several flag-control opcodes together.

    Program:
        SEC
        SED
        CLV
        CLC
        CLD
        SEI
        CLI

    Expected final flags:
        Carry clear
        Decimal clear
        Overflow clear
        Interrupt Disable clear
    """
    cpu, bus, rom = prepare_cpu([
        0x38,  # SEC
        0xF8,  # SED
        0xB8,  # CLV
        0x18,  # CLC
        0xD8,  # CLD
        0x78,  # SEI
        0x58,  # CLI
    ])
    cpu.p = OVERFLOW_FLAG

    run_steps(cpu, 7)

    assert (cpu.p & CARRY_FLAG) == 0
    assert (cpu.p & DECIMAL_FLAG) == 0
    assert (cpu.p & OVERFLOW_FLAG) == 0
    assert cpu.flags.get_interrupt_disable_flag() is False
    assert cpu.pc == 0x8007


def test_CPU_VERIFICATION_transfers_and_stack_pointer_program():
    """
    Final boss objective:
    Execute register transfers involving X and S.

    Program:
        LDX #$80
        TXS
        LDX #$00
        TSX

    Expected:
        TXS copies $80 into S.
        TSX copies S back into X.
        TSX sets Negative because X becomes $80.
    """
    cpu, bus, rom = prepare_cpu([
        0xA2, 0x80,  # LDX #$80
        0x9A,        # TXS
        0xA2, 0x00,  # LDX #$00
        0xBA,        # TSX
    ])

    run_steps(cpu, 4)

    assert cpu.s == 0x80
    assert cpu.x == 0x80
    assert (cpu.p & NEGATIVE_FLAG) != 0
    assert (cpu.p & ZERO_FLAG) == 0


def test_CPU_VERIFICATION_OPCODE_GAUNTLET_program():
    """
    Final boss objective:
    Execute a larger real program that combines many official opcode families.

    This is not a replacement for the focused per-instruction tests. Instead, it
    is an integration confidence test: many instructions must cooperate through
    real CPU.step() sequencing, real PC movement, real stack behavior, real
    status flags, and real RAM writes.

    Program overview:
        - load/store: LDA, LDX, LDY, STA, STX, STY
        - arithmetic: ADC, SBC
        - memory math: INC, DEC
        - logic: AND, ORA, EOR, BIT
        - compare/branch: CMP, BEQ
        - stack: PHA, PLA, PHP, PLP
        - shifts/rotates: ASL, LSR, ROL, ROR accumulator forms
        - transfers: TAX, TXA, TAY, TYA, TXS, TSX
        - increments/decrements: INX, DEX, INY, DEY
        - flag controls: CLC, SEC, CLD, SED, CLV, CLI, SEI
        - NOP

    Why this test matters:
    A CPU can pass isolated instruction tests but still fail when instructions
    interact. This test catches integration bugs such as:
        - PC off-by-one errors
        - stale flags influencing ADC/SBC or branches
        - stack pointer push/pull mistakes
        - transfer instructions updating or not updating flags incorrectly
        - RAM writes going to the wrong address
    """
    cpu, bus, rom = prepare_cpu([
        0xA9, 0x10,  # LDA #$10
        0x85, 0x10,  # STA $10
        0xA2, 0x03,  # LDX #$03
        0xA0, 0x05,  # LDY #$05
        0xE6, 0x10,  # INC $10 -> $11
        0xC6, 0x10,  # DEC $10 -> $10
        0xA5, 0x10,  # LDA $10 -> $10
        0x69, 0x05,  # ADC #$05 -> $15
        0x38,        # SEC, so SBC subtracts without borrow
        0xE9, 0x05,  # SBC #$05 -> $10
        0x29, 0x0F,  # AND #$0F -> $00
        0x09, 0x80,  # ORA #$80 -> $80
        0x49, 0xFF,  # EOR #$FF -> $7F
        0xC9, 0x7F,  # CMP #$7F, sets Zero and Carry
        0xF0, 0x02,  # BEQ +2, skip next LDA
        0xA9, 0x00,  # LDA #$00, skipped
        0x24, 0x10,  # BIT $10, tests A against RAM value $10
        0x48,        # PHA, push $7F
        0xA9, 0x00,  # LDA #$00
        0x68,        # PLA, restore $7F
        0x0A,        # ASL A: $7F -> $FE
        0x4A,        # LSR A: $FE -> $7F
        0x2A,        # ROL A with Carry clear: $7F -> $FE
        0x6A,        # ROR A with Carry clear: $FE -> $7F
        0xAA,        # TAX, X = $7F
        0xE8,        # INX, X = $80
        0xCA,        # DEX, X = $7F
        0x8A,        # TXA, A = $7F
        0xA8,        # TAY, Y = $7F
        0xC8,        # INY, Y = $80
        0x88,        # DEY, Y = $7F
        0x98,        # TYA, A = $7F
        0x9A,        # TXS, S = X = $7F
        0xBA,        # TSX, X = S = $7F
        0x08,        # PHP, push status
        0x28,        # PLP, restore status
        0x18,        # CLC
        0x38,        # SEC
        0xD8,        # CLD
        0xF8,        # SED
        0xB8,        # CLV
        0x58,        # CLI
        0x78,        # SEI
        0xEA,        # NOP
        0x86, 0x11,  # STX $11
        0x84, 0x12,  # STY $12
        0x85, 0x13,  # STA $13
    ])

    run_steps(cpu, 46)

    assert cpu.a == 0x7F
    assert cpu.x == 0x7F
    assert cpu.y == 0x7F
    assert cpu.s == 0x7F

    assert bus.read(0x0010) == 0x10
    assert bus.read(0x0011) == 0x7F
    assert bus.read(0x0012) == 0x7F
    assert bus.read(0x0013) == 0x7F

    assert cpu.flags.get_carry_flag() is True
    assert cpu.flags.get_decimal_flag() is True
    assert cpu.flags.get_interrupt_disable_flag() is True
    assert cpu.flags.get_overflow_flag() is False
    assert cpu.flags.get_zero_flag() is False
    assert cpu.flags.get_negative_flag() is False

    assert cpu.pc == 0x8043
