"""
Add useful emulation error reporting to main_only_background.py.

File to update:
    main_only_background.py

Why this step exists:
main_only_background.py runs a real manual ROM loop with pygame. When real ROM
execution hits a missing emulator behavior, the user needs context before the
Python traceback.

Without context, an error may only say:

    ValueError: Unsupported CPU bus read: 4020

With context, main_only_background.py should also print useful emulator state:

    Emulation Error:
        type=ValueError
        message=Unsupported CPU bus read: 4020
        pc=$812A
        ppu_frame=123
        ppu_scanline=241
        ppu_cycle=10

This does not replace the traceback. The original exception should still be
re-raised so developers can debug normally.

Suggested implementation example:

    def print_emulation_error(error: Exception, console: Console) -> None:
        print("\nEmulation Error:")
        print(f"    type={type(error).__name__}")
        print(f"    message={error}")
        print(f"    pc=${console.cpu.pc:04X}")
        print(f"    ppu_frame={console.ppu.frame}")
        print(f"    ppu_scanline={console.ppu.scanline}")
        print(f"    ppu_cycle={console.ppu.cycle}")


    def main() -> None:
        ...

        pygame.init()
        try:
            window = pygame.display.set_mode(...)

            running = True
            while running:
                ...

                executed = console.step_until_next_frame()
                framebuffer = console.render_background_framebuffer()
                draw_framebuffer(window, framebuffer, SCALE)
                pygame.display.flip()

        except KeyboardInterrupt:
            print("\nStopped by user.")
        except Exception as error:
            print_emulation_error(error, console)
            raise
        finally:
            pygame.quit()

Why catch KeyboardInterrupt separately?
Ctrl+C is an intentional user stop, not an emulator failure. It should print a
friendly stop message and should not print an emulation error report.

Why re-raise unexpected exceptions?
The error report gives emulator context, but the traceback still matters. Re-raise
keeps the original failure visible for debugging.

Out of scope:
    - changing CPU opcode diagnostics
    - catching and hiding all errors
    - writing logs to files
    - calling main() from pytest
"""

import inspect
from contextlib import redirect_stdout
from io import StringIO

import main_only_background as background_main


class FakeCPU:
    def __init__(self, pc: int):
        self.pc = pc


class FakePPU:
    def __init__(self, frame: int, scanline: int, cycle: int):
        self.frame = frame
        self.scanline = scanline
        self.cycle = cycle


class FakeConsole:
    def __init__(self):
        self.cpu = FakeCPU(pc=0x812A)
        self.ppu = FakePPU(frame=123, scanline=241, cycle=10)


def test_main_declares_print_emulation_error_helper():
    """
    Objective:
    main_only_background.py exposes a small helper for printing emulator context
    when unexpected execution errors occur.
    """
    assert hasattr(background_main, "print_emulation_error")
    assert callable(background_main.print_emulation_error)


def test_print_emulation_error_prints_exception_type_and_message():
    """
    Objective:
    The report should include the original exception type and message.
    """
    output = StringIO()

    with redirect_stdout(output):
        background_main.print_emulation_error(ValueError("Unsupported CPU bus read: 4020"), FakeConsole())

    text = output.getvalue()

    assert "Emulation Error" in text
    assert "type=ValueError" in text
    assert "message=Unsupported CPU bus read: 4020" in text


def test_print_emulation_error_prints_cpu_and_ppu_context():
    """
    Objective:
    The report should include enough emulator state to locate when/where the error
    happened.
    """
    output = StringIO()

    with redirect_stdout(output):
        background_main.print_emulation_error(RuntimeError("boom"), FakeConsole())

    text = output.getvalue()

    assert "pc=$812A" in text
    assert "ppu_frame=123" in text
    assert "ppu_scanline=241" in text
    assert "ppu_cycle=10" in text


def test_main_handles_keyboard_interrupt_before_general_exception():
    """
    Objective:
    Ctrl+C should remain a clean user stop and should not be reported as an
    emulator failure.
    """
    source = inspect.getsource(background_main.main)

    keyboard_index = source.index("except KeyboardInterrupt")
    exception_index = source.index("except Exception as error")

    assert keyboard_index < exception_index
    assert "Stopped by user" in source


def test_main_reports_unexpected_exception_and_reraises():
    """
    Objective:
    Unexpected exceptions should print emulator context and then re-raise to keep
    the original traceback visible.

    This is a source-shape test because pytest must not call main().
    """
    source = inspect.getsource(background_main.main)

    assert "except Exception as error" in source
    assert "print_emulation_error(error, console)" in source
    assert "raise" in source


def test_main_still_quits_pygame_in_finally():
    """
    Objective:
    Even when an error happens, pygame should be cleaned up.
    """
    source = inspect.getsource(background_main.main)

    assert "finally:" in source
    assert "pygame.quit()" in source
