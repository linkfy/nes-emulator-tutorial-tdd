"""
Define a minimal NES RGB palette approximation.

Reference palette file:
    https://www.nesdev.org/wiki/File:2C02G_U_wiki.pal

File to create:
    emulator/rendering/nes_palette.py

Why this step exists:
The rendering pipeline can now convert color-index grids into Framebuffer data,
but callers still need to provide an RGB palette manually.

This step defines a practical 64-color NES RGB palette approximation:

    NES color index $00-$3F -> RGB tuple

Important hardware model:
The NES does not store RGB colors directly. The PPU has palette RAM containing
NES color indexes, and the PPU's analog video circuitry turns those indexes into
a video signal. In an emulator, we approximate that output with RGB tuples.

Real-ish flow:

    pixel palette entry
        -> PPU palette RAM value $00-$3F
        -> PPU hardware color generator / analog video signal
        -> TV color

Emulator flow:

    pixel palette entry
        -> PPU palette RAM value $00-$3F
        -> NES_PALETTE_RGB[index]
        -> Framebuffer RGB pixel

What is 2C02G_U_wiki.pal?
2C02G is an NTSC NES PPU revision. The referenced .pal file is an RGB palette
approximation for that PPU/output behavior. It is not a literal RGB table stored
inside NES hardware.

Why does the source file have more than 64 colors?
Some .pal files include PPUMASK emphasis variants. The base NES color index range
is 64 colors, but emphasis can create 8 display variants:

    64 base colors * 8 emphasis states = 512 RGB entries

For this tutorial step, use only the first 64 RGB entries: the normal no-emphasis
palette. Emphasis support can be added later when rendering uses PPUMASK bits 5-7.

How to reproduce this table from the downloaded .pal file:

    file = "2C02G_U_wiki.pal"
    data = open(file, "rb").read()

    for i in range(0, 64 * 3, 3):
        rgb = data[i:i + 3]
        if len(rgb) == 3:
            r, g, b = rgb[0], rgb[1], rgb[2]
            print(f"({r},{g},{b}),")

Suggested implementation example:

    from emulator.rendering.framebuffer import RGBColor

    NES_PALETTE_SIZE = 64

    NES_PALETTE_RGB: list[RGBColor] = [
        (87,87,87),     (0,12,142),     (8,0,166),      (52,0,150),      (85,0,97),      (99,0,21),      (90,0,0),       (60,14,0),
        (17,40,0),      (0,59,0),       (0,66,0),       (0,58,5),        (0,38,82),      (0,0,0),        (0,0,0),        (0,0,0),

        (165,165,165),  (0,65,217),     (47,30,255),    (103,4,242),     (148,0,180),    (170,0,87),     (163,24,0),     (128,57,0),
        (75,91,0),      (19,118,0),     (0,129,0),      (0,121,35),      (0,98,136),     (0,0,0),        (0,0,0),        (0,0,0),

        (255,255,255),  (74,159,255),   (121,126,255),  (175,99,255),    (221,85,255),   (247,87,194),   (247,106,99),   (220,136,16),
        (174,169,0),    (120,196,0),    (74,210,17),    (47,207,100),    (47,189,196),   (65,65,65),     (0,0,0),        (0,0,0),

        (255,255,255),  (185,221,255),  (202,209,255),  (222,198,255),   (240,192,255),  (252,192,238),  (253,198,202),  (245,208,170),
        (228,221,149),  (208,232,146),  (189,238,162),  (178,238,192),   (176,232,227),  (179,179,179),  (0,0,0),        (0,0,0),
    ]

    def get_nes_rgb_color(index: int) -> RGBColor:
        return NES_PALETTE_RGB[index & 0x3F]

Why mask with $3F?
NES color indexes are 6-bit values:

    $00-$3F

Masking keeps lookup in range:

    index & 0x3F

Examples:

    get_nes_rgb_color(0x40) == get_nes_rgb_color(0x00)
    get_nes_rgb_color(0x41) == get_nes_rgb_color(0x01)

Out of scope:
    - PPUMASK emphasis colors
    - PAL/Dendy palettes
    - CRT/NTSC signal simulation
    - PPU palette RAM lookup at $3F00-$3F1F
    - pygame display
"""

from pathlib import Path

from emulator.rendering.nes_palette import (
    NES_PALETTE_RGB,
    NES_PALETTE_SIZE,
    get_nes_rgb_color,
)


EXPECTED_NES_PALETTE_RGB = [
    (87,87,87),     (0,12,142),     (8,0,166),      (52,0,150),      (85,0,97),      (99,0,21),      (90,0,0),       (60,14,0),
    (17,40,0),      (0,59,0),       (0,66,0),       (0,58,5),        (0,38,82),      (0,0,0),        (0,0,0),        (0,0,0),

    (165,165,165),  (0,65,217),     (47,30,255),    (103,4,242),     (148,0,180),    (170,0,87),     (163,24,0),     (128,57,0),
    (75,91,0),      (19,118,0),     (0,129,0),      (0,121,35),      (0,98,136),     (0,0,0),        (0,0,0),        (0,0,0),

    (255,255,255),  (74,159,255),   (121,126,255),  (175,99,255),    (221,85,255),   (247,87,194),   (247,106,99),   (220,136,16),
    (174,169,0),    (120,196,0),    (74,210,17),    (47,207,100),    (47,189,196),   (65,65,65),     (0,0,0),        (0,0,0),

    (255,255,255),  (185,221,255),  (202,209,255),  (222,198,255),   (240,192,255),  (252,192,238),  (253,198,202),  (245,208,170),
    (228,221,149),  (208,232,146),  (189,238,162),  (178,238,192),   (176,232,227),  (179,179,179),  (0,0,0),        (0,0,0),
]


def test_nes_palette_file_exists():
    """
    Objective:
    Keep NES color-index-to-RGB policy separate from framebuffer storage.
    """
    assert Path("emulator/rendering/nes_palette.py").exists()


def test_nes_palette_declares_64_base_colors():
    """
    Objective:
    The current renderer uses the normal no-emphasis 64-color NES palette.
    """
    assert NES_PALETTE_SIZE == 64
    assert len(NES_PALETTE_RGB) == NES_PALETTE_SIZE


def test_nes_palette_matches_documented_2c02g_first_64_entries():
    """
    Objective:
    Lock the selected tutorial palette so rendering tests are deterministic.

    These are the first 64 RGB triples extracted from 2C02G_U_wiki.pal.
    """
    assert NES_PALETTE_RGB == EXPECTED_NES_PALETTE_RGB


def test_nes_palette_entries_are_rgb_byte_tuples():
    """
    Objective:
    Every palette entry is a displayable RGB tuple with byte-sized components.
    """
    for color in NES_PALETTE_RGB:
        assert isinstance(color, tuple)
        assert len(color) == 3

        for component in color:
            assert isinstance(component, int)
            assert 0 <= component <= 255


def test_get_nes_rgb_color_returns_palette_entry_for_base_indexes():
    """
    Objective:
    get_nes_rgb_color(index) performs a normal lookup for indexes $00-$3F.
    """
    assert get_nes_rgb_color(0x00) == NES_PALETTE_RGB[0x00]
    assert get_nes_rgb_color(0x01) == NES_PALETTE_RGB[0x01]
    assert get_nes_rgb_color(0x21) == NES_PALETTE_RGB[0x21]
    assert get_nes_rgb_color(0x3F) == NES_PALETTE_RGB[0x3F]


def test_get_nes_rgb_color_masks_indexes_to_6_bits():
    """
    Objective:
    NES color indexes are 6-bit. Higher bits should not escape the 64-color table.

    Examples:
        $40 masks to $00
        $41 masks to $01
        $7F masks to $3F
    """
    assert get_nes_rgb_color(0x40) == NES_PALETTE_RGB[0x00]
    assert get_nes_rgb_color(0x41) == NES_PALETTE_RGB[0x01]
    assert get_nes_rgb_color(0x7F) == NES_PALETTE_RGB[0x3F]


def test_nes_palette_does_not_model_emphasis_variants_yet():
    """
    Objective:
    Document the intentional scope: this table contains only the 64 base colors.
    PPUMASK emphasis variants can be added later as a separate rendering step.
    """
    assert len(NES_PALETTE_RGB) != 512
