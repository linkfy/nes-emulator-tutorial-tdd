from emulator.bus.cpu_bus import CpuBus
from emulator.cpu.cpu import CPU
from emulator.memory.fake_rom import FakeROM


ZERO_FLAG = 1 << 1
NEGATIVE_FLAG = 1 << 7


def make_cpu():
    return CPU(CpuBus())


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
