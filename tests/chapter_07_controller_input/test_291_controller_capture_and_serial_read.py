"""
Capture controller buttons and read them serially.

Files created in this step:
    emulator/input/controller.py

Why this step exists:
The NES CPU does not receive the controller state as a whole byte from $4016. It
receives one button bit at a time. Before wiring that protocol into CpuBus, the
pure Controller object should know how to:

References:
    https://www.nesdev.org/wiki/Standard_controller
    https://www.nesdev.org/wiki/Controller_reading_code

    1. capture the current button booleans into a stable snapshot
    2. expose the captured bits in NES serial order
    3. handle strobe high vs strobe low behavior

Key term: strobe
A strobe is a control signal written by the CPU. For the NES controller, strobe
controls whether the controller keeps capturing live button state or advances
through the captured serial bits.

Minimal example:

    controller.a = True
    controller.write_strobe(1)
    controller.write_strobe(0)
    controller.read_bit()  # returns A bit

Common misconception:

    "The controller should return all buttons as one byte."

The emulator may store captured buttons as one byte internally, but the CPU-facing
protocol reads one bit at a time.

Suggested implementation example:

    def capture_buttons(self) -> None:
        value = 0

        if self.a:
            value |= BUTTON_A
        if self.b:
            value |= BUTTON_B
        if self.select:
            value |= BUTTON_SELECT
        if self.start:
            value |= BUTTON_START
        if self.up:
            value |= BUTTON_UP
        if self.down:
            value |= BUTTON_DOWN
        if self.left:
            value |= BUTTON_LEFT
        if self.right:
            value |= BUTTON_RIGHT

        self.captured_buttons = value
        self.read_index = 0


    def write_strobe(self, value: int) -> None:
        self.strobe = (value & 1) == 1

        if self.strobe:
            self.capture_buttons()


    def read_bit(self) -> int:
        if self.strobe:
            self.capture_buttons()

        if self.read_index >= 8:
            return 1

        bit = (self.captured_buttons >> self.read_index) & 1
        self.read_index += 1
        return bit

Out of scope:
    - CpuBus $4016 routing
    - pygame keyboard mapping
    - controller port 2
    - Famicom expansion controllers
    - DMC/controller read glitch behavior
"""

from emulator.input.controller import (
    BUTTON_A,
    BUTTON_DOWN,
    BUTTON_RIGHT,
    BUTTON_SELECT,
    BUTTON_START,
    Controller,
)


def test_capture_buttons_packs_current_buttons_into_captured_snapshot():
    """
    Objective:
    capture_buttons() converts current boolean button fields into one captured byte
    using NES hardware serial order.
    """
    controller = Controller(a=True, start=True, right=True)

    controller.capture_buttons()

    assert controller.captured_buttons == BUTTON_A | BUTTON_START | BUTTON_RIGHT
    assert controller.read_index == 0


def test_capture_buttons_is_a_snapshot_not_live_alias():
    """
    Objective:
    Captured state should remain stable until the next capture.

    This teaches why captured_buttons is a better name than pressed_buttons.
    """
    controller = Controller(a=True)
    controller.capture_buttons()

    controller.a = False

    assert controller.captured_buttons == BUTTON_A


def test_read_bit_returns_buttons_in_nes_serial_order():
    """
    Objective:
    read_bit() exposes one button at a time in hardware order:

        A, B, Select, Start, Up, Down, Left, Right
    """
    controller = Controller(a=True, select=True, down=True, right=True)
    controller.capture_buttons()

    bits = [controller.read_bit() for _ in range(8)]

    assert bits == [1, 0, 1, 0, 0, 1, 0, 1]
    assert controller.read_index == 8


def test_read_bit_returns_one_after_all_8_buttons_are_read():
    """
    Objective:
    After the eight standard controller bits, this tutorial model returns 1 for
    further reads.
    """
    controller = Controller()
    controller.capture_buttons()

    for _ in range(8):
        controller.read_bit()

    assert controller.read_bit() == 1
    assert controller.read_bit() == 1


def test_write_strobe_high_captures_current_buttons_and_sets_strobe():
    """
    Objective:
    Writing a value with bit 0 set turns strobe on and captures current buttons.
    """
    controller = Controller(start=True, down=True)

    controller.write_strobe(0x01)

    assert controller.strobe is True
    assert controller.captured_buttons == BUTTON_START | BUTTON_DOWN
    assert controller.read_index == 0


def test_write_strobe_uses_only_bit_0():
    """
    Objective:
    The controller strobe signal is controlled by bit 0 of the written value.
    Higher bits should not matter.
    """
    controller = Controller(select=True)

    controller.write_strobe(0xFE)

    assert controller.strobe is False

    controller.write_strobe(0xFF)

    assert controller.strobe is True
    assert controller.captured_buttons == BUTTON_SELECT


def test_strobe_high_keeps_capturing_and_returns_a_button_repeatedly():
    """
    Objective:
    While strobe is high, read_bit() keeps recapturing live state and returns the A
    button bit instead of advancing through the serial sequence.
    """
    controller = Controller(a=True, right=True)
    controller.write_strobe(1)

    assert [controller.read_bit() for _ in range(4)] == [1, 1, 1, 1]
    assert controller.read_index == 1

    controller.a = False

    assert controller.read_bit() == 0


def test_strobe_low_allows_serial_reads_to_advance():
    """
    Objective:
    The normal CPU polling pattern is strobe high, then strobe low, then eight
    serial reads.
    """
    controller = Controller(a=True, b=False, start=True, right=True)

    controller.write_strobe(1)
    controller.write_strobe(0)

    bits = [controller.read_bit() for _ in range(8)]

    assert bits == [1, 0, 0, 1, 0, 0, 0, 1]
