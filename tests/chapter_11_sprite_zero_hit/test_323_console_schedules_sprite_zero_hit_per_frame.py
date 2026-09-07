"""
Schedule sprite 0 hit automatically when Console advances a frame.

File to update:
    emulator/console.py

Why this step exists:
The previous steps provide all required mechanisms:

    ppu_sprite_zero_hit_position(ppu)
        -> extracts current PPU state and finds the overlap position

    ppu.set_sprite_zero_hit_position(position)
        -> stores the future timing event

    ppu.step(...)
        -> sets PPUSTATUS bit 6 when timing reaches that position

This step connects them to the frame loop.

Architecture decision:
We intentionally put sprite-zero-hit preparation inside
Console.step_until_next_frame(). A caller such as main.py should ask Console to
advance one complete emulated frame without knowing which internal PPU timing events
must be prepared first.

This keeps main.py focused on frontend responsibilities:

    input
    display
    FPS reporting
    frame pacing

Console owns frame-level emulator coordination.

Suggested implementation change:

    # --- NEW LINE ---
    from emulator.rendering.sprite_zero_hit import ppu_sprite_zero_hit_position
    # --- END NEW LINE ---


    def step_until_next_frame(
        self,
        max_cpu_instructions: int | None = None,
    ) -> int:
        # --- NEW BLOCK ---
        position = ppu_sprite_zero_hit_position(self.ppu)
        self.ppu.set_sprite_zero_hit_position(position)
        # --- END NEW BLOCK ---

        start_frame = self.ppu.frame
        executed = 0

        while self.ppu.frame == start_frame:
            ...

Why before the stepping loop?
The CPU may poll PPUSTATUS while the frame is being emulated. The future hit must be
scheduled before CPU/PPU execution reaches the overlapping pixel.

Manual compatibility checkpoint:
After this step, students may temporarily change the local manual ROM path in
main.py to their own legal copy:

Suggested implementation change in main.py:
    ROM_PATH = Path("Super Mario Bros.nes")

Then run with PyPy:

Linux/macOS:

    sh launcher.sh

Windows Command Prompt:

    launcher.cmd

Expected manual improvement:
Super Mario Bros. uses sprite 0 hit as a PPU timing signal. With the hit now detected,
scheduled, and exposed through PPUSTATUS, the title/menu should progress further,
Mario should appear, and controller input should become usable.

Known remaining limitation:
When Mario advances horizontally, the scene may still look incorrect because the
current background renderer does not yet apply the PPU scrolling state to select and
offset the visible nametable region. Sprite 0 hit enables the game's timing path; it
does not implement horizontal background scrolling.

Legal/testing rule:
Super Mario Bros.nes is a manual, user-provided compatibility experiment only. Do
not commit the ROM and do not require it from automated tests. These tests use fake
CPU/PPU objects and inspect coordination behavior only.

Out of scope:
    - horizontal/vertical scrolling
    - fine X scrolling
    - adjacent nametable composition
    - exact OAM Y+1 behavior
    - PPUMASK left-edge rules
    - x=255 sprite 0 hit exception
    - commercial ROM fixtures
"""

import inspect
from pathlib import Path

import emulator.console as console_module
from emulator.console import Console


class FakeCPU:
    def __init__(self, events: list[str]):
        self.events = events

    def step(self) -> int:
        self.events.append("cpu_step")
        return 2

    def interrupt_nmi(self) -> None:
        self.events.append("nmi")


class FakePPU:
    def __init__(self, events: list[str]):
        self.events = events
        self.frame = 0
        self.nmi_requested = False
        self.received_position = "not-set"

    def set_sprite_zero_hit_position(self, position) -> None:
        self.events.append("set_position")
        self.received_position = position

    def step(self, cycles: int) -> None:
        self.events.append("ppu_step")
        self.frame += 1


def make_fake_console() -> tuple[Console, FakePPU, list[str]]:
    events: list[str] = []
    cpu = FakeCPU(events)
    ppu = FakePPU(events)
    console = Console(cpu=cpu, ppu=ppu)
    return console, ppu, events


def test_console_computes_sprite_zero_hit_position_before_advancing_frame(monkeypatch):
    """
    Objective:
    Frame-level overlap extraction must happen before the first CPU instruction of
    the frame.
    """
    console, _ppu, events = make_fake_console()

    def fake_ppu_sprite_zero_hit_position(ppu):
        events.append("find_position")
        return (40, 30)

    monkeypatch.setattr(
        console_module,
        "ppu_sprite_zero_hit_position",
        fake_ppu_sprite_zero_hit_position,
    )

    console.step_until_next_frame()

    assert events == [
        "find_position",
        "set_position",
        "cpu_step",
        "ppu_step",
    ]


def test_console_forwards_exact_overlap_position_to_ppu(monkeypatch):
    """
    Objective:
    Console coordinates the helpers but must not alter the detected screen
    coordinate.
    """
    console, ppu, _events = make_fake_console()
    expected_position = (123, 45)

    monkeypatch.setattr(
        console_module,
        "ppu_sprite_zero_hit_position",
        lambda received_ppu: expected_position,
    )

    console.step_until_next_frame()

    assert ppu.received_position is expected_position


def test_console_forwards_none_when_frame_has_no_overlap(monkeypatch):
    """
    Objective:
    A frame without sprite 0/background overlap should explicitly clear any future
    scheduled position by forwarding None.
    """
    console, ppu, _events = make_fake_console()

    monkeypatch.setattr(
        console_module,
        "ppu_sprite_zero_hit_position",
        lambda received_ppu: None,
    )

    console.step_until_next_frame()

    assert ppu.received_position is None


def test_sprite_zero_hit_preparation_preserves_instruction_count_result(monkeypatch):
    """
    Objective:
    Adding frame preparation must not change the existing return contract of
    step_until_next_frame().
    """
    console, _ppu, _events = make_fake_console()

    monkeypatch.setattr(
        console_module,
        "ppu_sprite_zero_hit_position",
        lambda received_ppu: None,
    )

    executed = console.step_until_next_frame()

    assert executed == 1


def test_main_does_not_need_to_know_sprite_zero_hit_internals():
    """
    Objective:
    The frontend should continue calling only Console.step_until_next_frame() rather
    than manually finding or scheduling sprite 0 hit.
    """
    source = Path("main.py").read_text()

    assert "console.step_until_next_frame()" in source
    assert "ppu_sprite_zero_hit_position" not in source
    assert "set_sprite_zero_hit_position" not in source


def test_console_schedules_position_before_existing_frame_loop():
    """
    Objective:
    Preserve the source-level timing invariant even if implementation details around
    the loop evolve later.
    """
    source = inspect.getsource(Console.step_until_next_frame)

    find_index = source.index("ppu_sprite_zero_hit_position(self.ppu)")
    set_index = source.index("self.ppu.set_sprite_zero_hit_position(position)")
    loop_index = source.index("while self.ppu.frame == start_frame")

    assert find_index < set_index < loop_index


def test_sprite_zero_hit_frame_coordination_keeps_pygame_outside_core():
    """
    Objective:
    Sprite-zero-hit scheduling is emulator behavior and must not introduce pygame
    into Console, PPU, or rendering helpers.
    """
    core_files = [
        Path("emulator/console.py"),
        Path("emulator/ppu/ppu.py"),
        Path("emulator/rendering/sprite_zero_hit.py"),
    ]

    for file_path in core_files:
        assert "import pygame" not in file_path.read_text()
