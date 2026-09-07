"""
Test 001 — Create the initial emulator source files.

Files to create:
    emulator/cpu/cpu.py
    emulator/cpu/addressing_modes.py
    emulator/cpu/instructions.py
    emulator/bus/cpu_bus.py
    emulator/memory/ram.py

Why this step exists:
Establish the first source-code boundaries before implementing behavior. CPU state,
address calculations, instruction behavior, bus routing, and memory storage should
not begin in one monolithic file.

Steps to reproduce:
    1. Create emulator/cpu, emulator/bus, and emulator/memory if they do not exist.
    2. Create the five empty Python files listed above.
    3. Add __init__.py files to package directories when required by the environment.
    4. Run this test and confirm that every expected path exists.

No implementation is required yet. Empty files are the intended result of this step.

Common misconception:
Creating separate files does not require designing every future class now. This step
defines only physical locations; later tests introduce responsibilities incrementally.

Out of scope:
    - RAM behavior
    - CPU registers
    - bus address mapping
    - instruction execution
"""

from pathlib import Path


# CPU Folder files
def test_cpu_file_exists():
    assert Path("emulator/cpu/cpu.py").exists()


def test_cpu_addressing_mode_file_exists():
    assert Path("emulator/cpu/addressing_modes.py").exists()


def test_cpu_instructions_file_exists():
    assert Path("emulator/cpu/instructions.py").exists()


# BUS Folder files
def test_cpu_bus_file_exists():
    assert Path("emulator/bus/cpu_bus.py").exists()


# Memory Files
def test_memory_ram_file_exists():
    assert Path("emulator/memory/ram.py").exists()
