"""
Define the pure NES Controller state object.

Files to create in this step:
    emulator/input/__init__.py
    emulator/input/controller.py

Why this step exists:
Before connecting controller input to CpuBus address $4016, we need a pure data
model for the standard NES controller. This keeps the controller mechanism easy to
test without involving pygame, CpuBus, ROM execution, or frame timing.

What is a standard NES controller?
The standard controller has eight buttons:

References:
    https://www.nesdev.org/wiki/Standard_controller
    https://www.nesdev.org/wiki/Controller_reading_code

    A, B, Select, Start, Up, Down, Left, Right

The hardware serial read order is:

    first read  -> A
    second read -> B
    third read  -> Select
    fourth read -> Start
    fifth read  -> Up
    sixth read  -> Down
    seventh read -> Left
    eighth read -> Right

Important distinction:
Some NES assembly routines shift these reads into RAM so A ends up in bit 7 of a
game-owned byte. That does not mean the hardware sends Right first. The emulator
should model the hardware serial order.

Suggested implementation example:

    from dataclasses import dataclass


    BUTTON_A = 1 << 0
    BUTTON_B = 1 << 1
    BUTTON_SELECT = 1 << 2
    BUTTON_START = 1 << 3
    BUTTON_UP = 1 << 4
    BUTTON_DOWN = 1 << 5
    BUTTON_LEFT = 1 << 6
    BUTTON_RIGHT = 1 << 7


    @dataclass
    class Controller:
        a: bool = False
        b: bool = False
        select: bool = False
        start: bool = False
        up: bool = False
        down: bool = False
        left: bool = False
        right: bool = False

        strobe: bool = False
        captured_buttons: int = 0
        read_index: int = 0

Out of scope:
    - CpuBus $4016 routing
    - pygame keyboard mapping
    - controller port 2
    - Famicom expansion controllers
    - DMC/controller read glitch behavior
"""

from dataclasses import is_dataclass
from pathlib import Path

from emulator.input.controller import (
    BUTTON_A,
    BUTTON_B,
    BUTTON_DOWN,
    BUTTON_LEFT,
    BUTTON_RIGHT,
    BUTTON_SELECT,
    BUTTON_START,
    BUTTON_UP,
    Controller,
)


def test_controller_input_files_exist():
    """
    Objective:
    Controller input starts as a pure emulator-core input module, not as pygame or
    CpuBus behavior.
    """
    assert Path("emulator/input/__init__.py").exists()
    assert Path("emulator/input/controller.py").exists()


def test_controller_is_a_dataclass():
    """
    Objective:
    The controller state is plain data with small behavior methods layered on top.
    """
    assert is_dataclass(Controller)


def test_controller_button_constants_match_hardware_serial_order():
    """
    Objective:
    Constants encode the order in which $4016 serial reads expose buttons.

    This is not the same thing as every game's final RAM byte layout.
    """
    assert BUTTON_A == 1 << 0
    assert BUTTON_B == 1 << 1
    assert BUTTON_SELECT == 1 << 2
    assert BUTTON_START == 1 << 3
    assert BUTTON_UP == 1 << 4
    assert BUTTON_DOWN == 1 << 5
    assert BUTTON_LEFT == 1 << 6
    assert BUTTON_RIGHT == 1 << 7


def test_controller_defaults_to_all_buttons_released_and_not_strobing():
    """
    Objective:
    A new controller starts with no pressed buttons and no captured serial state.
    """
    controller = Controller()

    assert controller.a is False
    assert controller.b is False
    assert controller.select is False
    assert controller.start is False
    assert controller.up is False
    assert controller.down is False
    assert controller.left is False
    assert controller.right is False

    assert controller.strobe is False
    assert controller.captured_buttons == 0
    assert controller.read_index == 0


def test_controller_module_does_not_import_pygame_or_cpubus():
    """
    Objective:
    This first controller step must remain pure. Pygame and CpuBus wiring come
    later.
    """
    source = Path("emulator/input/controller.py").read_text()

    assert "import pygame" not in source
    assert "CpuBus" not in source
    assert "4016" not in source
