"""
Add explicit PyPy launchers for manual execution.

Files to create at repository root:
    launcher.sh
    launcher.cmd

Why this step exists:
PyPy can improve emulator-core throughput because much of the emulator is Python
code running in tight loops. Instead of changing pyproject.toml or forcing all
students to use PyPy by default, this step adds explicit manual launchers.

After creating these launchers, students should use them for manual performance
experiments instead of launching main.py directly with CPython.

Linux/macOS usage:

    sh launcher.sh

or, if executable permission was added:

    chmod +x launcher.sh
    ./launcher.sh

Windows Command Prompt usage:

    launcher.cmd

Expected manual signal:
The FPS counter added earlier should improve when the emulator core benefits from
PyPy. After the faster pygame framebuffer upload path, PyPy may make the emulator
run faster than real NES speed. During tutorial development, the combined faster
pygame drawing path plus PyPy reached roughly 90-120 FPS on the manual ROM path.

The exact number depends on machine and ROM state, but the terminal FPS output is
now the evidence to compare:

    fps=30.0    # example after faster pygame drawing on CPython
    fps=100.0   # example after faster pygame drawing + PyPy launcher

If FPS is now above NES speed, that is good evidence that the next step should add
frame pacing / expected-speed control so the manual game does not run too fast.

Expected command delegated by both launchers:

    uv run --python pypy python main.py

Linux/macOS example:

    #!/usr/bin/env sh

    # Run NES with PyPy through uv.
    # Usage:
    #     sh launcher.sh
    # or:
    #     chmod +x launcher.sh
    #     ./launcher.sh

    uv run --python pypy python main.py

Windows CMD example:

    @echo off

    REM Run NES with PyPy through uv.
    REM Usage:
    REM     launcher.cmd

    uv run --python pypy python main.py

Important testing rule:
These tests must not execute the launchers. Running them would start the manual
pygame frontend and require a local ROM file. We only inspect the files as text.

Out of scope:
    - changing pyproject.toml default Python
    - launching PyPy from pytest
    - opening pygame windows
    - measuring FPS
    - optimizing rendering
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LAUNCHER_SH = ROOT / "launcher.sh"
LAUNCHER_CMD = ROOT / "launcher.cmd"
EXPECTED_COMMAND = "uv run --python pypy python main.py"


def test_linux_mac_pypy_launcher_exists_at_repo_root():
    """
    Objective:
    Linux/macOS users should have a simple shell launcher at the repository root.
    """
    assert LAUNCHER_SH.exists()


def test_windows_pypy_launcher_exists_at_repo_root():
    """
    Objective:
    Windows users should have a simple CMD launcher at the repository root.
    """
    assert LAUNCHER_CMD.exists()


def test_linux_mac_launcher_uses_sh_shebang():
    """
    Objective:
    launcher.sh should be runnable with POSIX sh on Linux/macOS.
    """
    source = LAUNCHER_SH.read_text()

    assert source.startswith("#!/usr/bin/env sh")


def test_linux_mac_launcher_delegates_to_uv_pypy_main():
    """
    Objective:
    The shell launcher should explicitly run main.py using PyPy through uv.
    """
    source = LAUNCHER_SH.read_text()

    assert EXPECTED_COMMAND in source


def test_windows_launcher_disables_echo_and_delegates_to_uv_pypy_main():
    """
    Objective:
    The CMD launcher should explicitly run main.py using PyPy through uv.
    """
    source = LAUNCHER_CMD.read_text()

    assert source.lower().startswith("@echo off")
    assert EXPECTED_COMMAND in source


def test_launchers_do_not_import_or_execute_emulator_modules_directly():
    """
    Objective:
    Launchers should only delegate to uv. They should not import pygame, main.py, or
    emulator core modules themselves.
    """
    combined = LAUNCHER_SH.read_text() + "\n" + LAUNCHER_CMD.read_text()

    forbidden_fragments = [
        "import pygame",
        "import main",
        "from emulator",
        "python -m pytest",
    ]

    for fragment in forbidden_fragments:
        assert fragment not in combined


def test_launchers_do_not_change_project_default_python_runtime():
    """
    Objective:
    PyPy should remain explicit and opt-in. This step should not force the whole
    project to use PyPy through pyproject.toml.
    """
    pyproject = ROOT / "pyproject.toml"
    if not pyproject.exists():
        return

    source = pyproject.read_text()

    assert "python-preference" not in source
    assert "pypy" not in source.lower()
