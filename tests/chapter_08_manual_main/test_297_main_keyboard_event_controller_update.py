"""
Use pygame key events to update controller_1 in main_only_background.py.

File to update:
    main_only_background.py

Why this step exists:
The emulator core already exposes controller port 1 through CpuBus $4016.
main_only_background.py should translate pygame keyboard events into updates on the
pure Controller object:

    pygame KEYDOWN Z -> cpu_bus.controller_1.a = True
    pygame KEYUP Z   -> cpu_bus.controller_1.a = False

Suggested implementation example:

    from emulator.input.controller import Controller
    ...

    def handle_key_event(controller: Controller, key: int, pressed: bool) -> None:
        if key == KEYS["a"]:
            controller.a = pressed
        elif key == KEYS["b"]:
            controller.b = pressed
        elif key == KEYS["select"]:
            controller.select = pressed
        elif key == KEYS["start"]:
            controller.start = pressed
        elif key == KEYS["up"]:
            controller.up = pressed
        elif key == KEYS["down"]:
            controller.down = pressed
        elif key == KEYS["left"]:
            controller.left = pressed
        elif key == KEYS["right"]:
            controller.right = pressed

    ...
    # Inside pygame event loop:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            handle_key_event(cpu_bus.controller_1, event.key, True)
        elif event.type == pygame.KEYUP:
            handle_key_event(cpu_bus.controller_1, event.key, False)

Important boundary:
main_only_background.py can import pygame and handle keyboard events because it is a
manual visual runner. emulator/input/controller.py should remain pygame-free.

Out of scope:
    - pygame joystick/gamepad support
    - configurable key bindings
    - controller port 2
    - calling main() from pytest
"""

import inspect
from pathlib import Path

import pygame

import main_only_background as background_main
from emulator.input.controller import Controller


def test_main_declares_handle_key_event_helper():
    """
    Objective:
    main_only_background.py exposes a small helper that translates one pygame key
    event into one Controller state update.
    """
    assert hasattr(background_main, "handle_key_event")
    assert callable(background_main.handle_key_event)


def test_handle_key_event_sets_each_button_when_pressed():
    """
    Objective:
    KEYDOWN-style input should set the matching controller button boolean to True.
    """
    controller = Controller()

    button_names = ["a", "b", "select", "start", "up", "down", "left", "right"]

    for button_name in button_names:
        background_main.handle_key_event(controller, background_main.KEYS[button_name], True)
        assert getattr(controller, button_name) is True


def test_handle_key_event_clears_each_button_when_released():
    """
    Objective:
    KEYUP-style input should set the matching controller button boolean to False.
    """
    controller = Controller(
        a=True,
        b=True,
        select=True,
        start=True,
        up=True,
        down=True,
        left=True,
        right=True,
    )

    button_names = ["a", "b", "select", "start", "up", "down", "left", "right"]

    for button_name in button_names:
        background_main.handle_key_event(controller, background_main.KEYS[button_name], False)
        assert getattr(controller, button_name) is False


def test_handle_key_event_ignores_unknown_keys():
    """
    Objective:
    Pressing unrelated keyboard keys should not mutate controller state.
    """
    controller = Controller(a=True)

    background_main.handle_key_event(controller, pygame.K_F1, True)

    assert controller.a is True
    assert controller.b is False
    assert controller.start is False


def test_main_event_loop_handles_keydown_and_keyup_with_controller_1():
    """
    Objective:
    The pygame event loop should route KEYDOWN and KEYUP events to cpu_bus.controller_1.

    This is a source-shape test because pytest must not call main() or open a real
    pygame window.
    """
    source = inspect.getsource(background_main.main)

    assert "pygame.KEYDOWN" in source
    assert "pygame.KEYUP" in source
    assert "handle_key_event(cpu_bus.controller_1, event.key, True)" in source
    assert "handle_key_event(cpu_bus.controller_1, event.key, False)" in source


def test_keyboard_mapping_keeps_pygame_outside_emulator_core():
    """
    Objective:
    Keyboard events belong to main_only_background.py, not to emulator core
    input/bus modules.
    """
    core_files = [
        Path("emulator/input/controller.py"),
        Path("emulator/bus/cpu_bus.py"),
        Path("emulator/console.py"),
    ]

    for file_path in core_files:
        assert "import pygame" not in file_path.read_text()
