"""
Add a manual core_validator.py ROM boot loop.

File to create on root folder:
    core_validator.py

Why this step exists:
The emulator now has enough startup-survival behavior to make a manual developer
entry point useful:

    iNES parsing
    Mapper000/NROM
    CPU reset vector
    Console frame stepping
    APU/audio no-op for out-of-scope audio
    OAMDMA $4014
    controller port 1 through $4016

This step makes core_validator.py a manual place to try a local ROM and keep the
emulator running frame by frame without pygame.

Why core_validator.py instead of main.py?
main.py is reserved for the visual pygame runner. core_validator.py remains a
small non-visual runner that is useful when debugging the emulator core without a
window or frontend event loop.

Important legal/testing rule:
The tutorial repository must not include commercial ROM files. Automated tests must
not require MarioBros.nes. A developer who wants to manually run Mario Bros. must
provide their own legal local copy:

    MarioBros.nes

Reference hash used during tutorial development [Mario Bros. (World).nes]:

    MD5 5d7bcc400a2fb5fa27346da345d3bb62  MarioBros.nes
    SHA1 314b6e46e814f955b52ac954f67dab849582fe77

This hash is only a manual reference. Tests must not require this file or this
exact hash because users may have different legal dumps/revisions.

Suggested implementation example:

    from pathlib import Path

    from emulator.bus.cpu_bus import CpuBus
    from emulator.cartridge.cartridge import Cartridge
    from emulator.console import Console
    from emulator.cpu.cpu import CPU


    ROM_PATH = Path("MarioBros.nes")
    debug_mode = True


    def main() -> None:
        if not ROM_PATH.exists():
            raise FileNotFoundError(
                "MarioBros.nes not found. Provide your own legal local copy. "
                "This file is intentionally not included in the tutorial repository."
            )

        cartridge = Cartridge.from_ines_bytes(ROM_PATH.read_bytes())

        cpu_bus = CpuBus(cartridge=cartridge)
        cpu = CPU(cpu_bus)
        console = Console(cpu=cpu, ppu=cpu_bus.ppu)

        cpu.reset()

        print(f"Loaded {ROM_PATH}")
        print(f"CPU reset PC = ${cpu.pc:04X}")
        print("Starting frame loop. Press Ctrl+C to stop.")

        try:
            while True:
                executed = console.step_until_next_frame()

                if debug_mode:
                    print(
                        f"frame={console.ppu.frame} "
                        f"pc=${cpu.pc:04X} "
                        f"instructions={executed}"
                    )
        except KeyboardInterrupt:
            print("\nStopped by user.")


    if __name__ == "__main__":
        main()

Manual command:

    uv run python core_validator.py

Expected manual behavior:
This command does not exit by itself. It keeps stepping frames until the developer
presses Ctrl+C. That is expected because core_validator.py is a manual long-running
ROM execution tool, not an automated test.

Why this test does not call main():
core_validator.py is a manual infinite loop. Automated tests must stay finite and
must not require a local commercial ROM file. These tests inspect structure only.

Why debug_mode is only checked for existence:
debug_mode is a manual control knob. Future tutorial steps may set it to True or
False depending on what is being taught. Tests should not freeze that value.

Out of scope:
    - pygame display
    - keyboard mapping
    - committed ROM fixtures
    - asserting core_validator.py produces correct gameplay
    - calling main() from pytest
"""

import inspect
from pathlib import Path

import core_validator


def test_core_validator_exists_and_exposes_manual_entry_point_variables():
    """
    Objective:
    core_validator.py exposes the basic manual-run configuration without requiring
    tests to execute the infinite loop.
    """
    assert Path("core_validator.py").exists()
    assert hasattr(core_validator, "ROM_PATH")
    assert hasattr(core_validator, "debug_mode")
    assert hasattr(core_validator, "main")
    assert callable(core_validator.main)


def test_core_validator_rom_path_points_to_local_mariobros_file_name_without_requiring_it():
    """
    Objective:
    core_validator.py documents the expected local ROM filename, but pytest must
    not require that file to exist.
    """
    assert isinstance(core_validator.ROM_PATH, Path)
    assert core_validator.ROM_PATH.name == "MarioBros.nes"


def test_core_validator_debug_mode_exists_but_test_does_not_freeze_value():
    """
    Objective:
    debug_mode is a manual/developer knob. The test verifies the knob exists but
    does not assert True or False, so future tutorial steps may change it.
    """
    assert hasattr(core_validator, "debug_mode")


def test_core_validator_uses_real_rom_boot_construction_path():
    """
    Objective:
    core_validator.py should use the same ownership path as the emulator architecture:

        Cartridge -> CpuBus -> CPU + PPU -> Console
    """
    source = inspect.getsource(core_validator.main)

    assert "Cartridge.from_ines_bytes" in source
    assert "CpuBus(cartridge=cartridge)" in source
    assert "CPU(cpu_bus)" in source
    assert "Console(cpu=cpu, ppu=cpu_bus.ppu)" in source


def test_core_validator_uses_cpu_reset_vector_before_running_frames():
    """
    Objective:
    core_validator.py must boot through the ROM reset vector instead of forcing PC
    manually.
    """
    source = inspect.getsource(core_validator.main)

    assert "cpu.reset()" in source
    assert "cpu.pc = 0x8000" not in source


def test_core_validator_steps_by_frame_not_single_instruction_loop():
    """
    Objective:
    The manual loop should use the frame-level Console helper introduced earlier.
    """
    source = inspect.getsource(core_validator.main)

    assert "console.step_until_next_frame()" in source


def test_core_validator_has_keyboard_interrupt_escape_for_infinite_manual_loop():
    """
    Objective:
    An unlimited manual loop is acceptable only if the user can stop it cleanly
    with Ctrl+C.
    """
    source = inspect.getsource(core_validator.main)

    assert "while True" in source
    assert "KeyboardInterrupt" in source
    assert "Stopped by user" in source


def test_core_validator_has_main_guard_so_importing_does_not_start_loop():
    """
    Objective:
    Importing core_validator.py from pytest must not start the manual ROM loop.
    """
    source = Path("core_validator.py").read_text()

    assert 'if __name__ == "__main__"' in source
    assert "main()" in source


def test_core_validator_does_not_import_pygame():
    """
    Objective:
    core_validator.py is intentionally non-visual. Pygame belongs in main.py or
    other manual/frontend entry points.
    """
    source = Path("core_validator.py").read_text()

    assert "import pygame" not in source
