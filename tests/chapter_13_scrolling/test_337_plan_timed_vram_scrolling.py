"""
Understand the timed v/t/x scrolling plan before changing PPU stepping.

File to acknowledge after reading:
    emulator/ppu/ppu.py

References:
    https://www.nesdev.org/wiki/PPU_scrolling
    https://www.nesdev.org/wiki/PPU_scrolling#During_rendering
    https://www.nesdev.org/wiki/PPU_rendering#Line-by-line_timing

Why this reading step exists:
PPU.step() is a timing-critical subsystem. A small mistake can produce a picture that
looks almost correct while using the wrong scanline, nametable, or scroll position.
Before changing it, we need a stable mental model and a clear migration plan.

The current problem:
The existing frame-level viewport decodes temp_vram_addr (t) plus fine X after the
frame. That works for simple synthetic scrolling but fails for games that change
scroll during a frame.

Super Mario Bros. uses approximately this shape:

    visible rows 0-30:
        fixed status-bar scroll

    sprite-zero split:
        CPU prepares another horizontal position

    visible rows 31-239:
        moving gameplay scroll

One value sampled after the frame cannot describe both regions.

There is a second problem: t is not exclusively a scroll value. $2006 (PPUADDR) also
writes t while games load nametables and palettes. For example:

    CPU writes PPUADDR $3F00
        -> t becomes $3F00

Decoding that final value as scroll can briefly select the wrong viewport. This is why
startup or level transitions can appear to scroll rapidly while the screen is black.

The four internal scrolling values:

    v = current VRAM address used by rendering
    t = temporary VRAM address prepared by CPU register writes
    x = fine horizontal pixel offset
    w = first/second-write toggle for $2005 and $2006

Intuitive model:

    t is the next address configuration being prepared.
    v is the address currently moving through rendering.
    x is the 0-7 pixel offset inside the first tile.
    w remembers which half of a two-write register comes next.

Common misconception:

    t is the current scroll position for the entire frame.

Correct model:

    CPU writes assemble t and x.
    PPU timing copies selected fields from t into v.
    Rendering advances v while tiles and scanlines are processed.

Important timed operations:

    background-fetch dots, every 8 dots:
        increment horizontal v

    dot 256:
        increment vertical v

    dot 257:
        copy horizontal fields from t into v

    pre-render dots 280-304:
        copy vertical fields from t into v

Horizontal fields:

    coarse X
    horizontal nametable bit

Vertical fields:

    coarse Y
    fine Y
    vertical nametable bit

Why the copies are selective:
At dot 257, only the next scanline's horizontal position should be refreshed. Copying
all of t would also replace vertical state at the wrong time.

Why we record per scanline:
The existing nametable renderer already produces correct RGB source framebuffers. We
do not need to replace it with a complete per-dot pixel-fetch pipeline yet. Instead,
PPU timing will record the effective v + x position once for every visible scanline:

    scanline 0  -> viewport X 0
    scanline 1  -> viewport X 0
    ...
    scanline 30 -> viewport X 0
    scanline 31 -> viewport X 40
    ...

After the frame, the high-level renderer uses those recorded positions while copying
each output row exactly once.

Prefetch detail:
At dot 1, v is already two tiles ahead because dots 321-336 fetched the first two
background tiles into hardware shifters. The scanline snapshot must compensate for
those two coarse-X increments when deriving the visible viewport. Otherwise the whole
background appears shifted by 16 pixels.

Compatibility plan:
    - keep existing v, t, x, w register behavior and public rendering helpers
    - add pure address operations before applying them inside PPU.step()
    - retain the old frame-level viewport path as fallback during migration
    - add timed scanline rendering only after a complete frame of states exists
    - keep framebuffer and opacity-mask row selection identical
    - run `uv run pytest` after every numbered step

Upcoming focused steps:

    - pure horizontal v increment and nametable wrapping
    - pure horizontal t-to-v field copy
    - horizontal fetch-dot increments and dot-257 copy
    - pure vertical increment with fine Y and rows 29-31
    - pure vertical t-to-v field copy
    - dot-256 vertical increment and pre-render vertical copy
    - effective v + fine-X state for each visible scanline
    - row-limited framebuffer composition
    - identical row-limited opacity-mask composition
    - scanline-aware mask for sprite-zero-hit scheduling
    - manual Super Mario Bros. status-bar, movement, transition, and FPS validation

Accuracy boundary:
This approach models scrolling-address timing and scanline viewport selection. It is
not yet a complete per-dot background fetch/shifter renderer. CPU register writes are
also timed at the current instruction-stepping granularity.

Required action after reading:
Add exactly this comment near the vram_addr, temp_vram_addr, fine_x, and
second_write_toggle fields in emulator/ppu/ppu.py:

    # pass_test_337

Do not implement scrolling changes in this step. The comment is the only production
file change required to pass Test 337.
"""

from pathlib import Path


PPU_FILE = Path("emulator/ppu/ppu.py")
ACKNOWLEDGMENT = "# pass_test_337"


def test_student_acknowledged_timed_vram_scrolling_plan():
    """
    Objective:
    Confirm that the timing plan was read before later tests modify PPU.step().
    """
    lines = PPU_FILE.read_text().splitlines()

    assert any(line.strip() == ACKNOWLEDGMENT for line in lines), (
        "After reading Test 337, add '# pass_test_337' near the v/t/x/w fields "
        "in emulator/ppu/ppu.py. Do not implement timing behavior yet."
    )
