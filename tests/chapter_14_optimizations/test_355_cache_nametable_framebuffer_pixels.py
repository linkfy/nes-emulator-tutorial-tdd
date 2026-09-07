"""
Test 355 — Cache repeated nametable framebuffer pixels by exact graphics inputs.

File to update:
    emulator/rendering/nametable_renderer.py

Why this step exists:
The frontend asks the emulator for a complete background image every displayed frame.
Producing one logical nametable image requires decoding pattern data, selecting tile
palettes from the attribute table, and writing 256x240 RGB pixels. Scrolling can change
which portion of adjacent nametables is visible without changing the source graphics
inside either nametable, so consecutive frames often request the exact same expensive
source image.

At 60 FPS, one complete frame has only about 16.67 ms for CPU/PPU stepping, background
and sprite rendering, framebuffer upload, and presentation. Rebuilding 61,440 pixels
from unchanged bytes consumes that limited budget without producing new information.
A bounded content-addressed cache turns repeated source renders into an immutable-pixel
lookup plus a list copy, leaving more frame time for work that actually changed.

Names and responsibilities:
    - No existing function is renamed.
    - nametable_with_attributes_to_framebuffer() remains unchanged. It is still the
      lower-level operation that performs the expensive render on a cache miss.
    - nametable_with_palette_ram_to_framebuffer() keeps its public name and signature,
      but its body changes into an ownership-preserving wrapper around cached pixels.
    - _cached_nametable_with_palette_ram_pixels() is a new private helper containing
      the old public function's palette-building and rendering work.

Complete implementation:

    # functools.lru_cache is already imported for Test 354. Add this import if the
    # previous step is being reproduced independently:
    from functools import lru_cache


    @lru_cache(maxsize=8)
    def _cached_nametable_with_palette_ram_pixels(
        nametable_bytes: bytes,
        attribute_table: bytes,
        pattern_table_bytes: bytes,
        palette_ram: bytes,
    ) -> tuple[RGBColor, ...]:
        background_palettes = build_background_palettes_from_palette_ram(
            palette_ram
        )

        framebuffer = nametable_with_attributes_to_framebuffer(
            nametable_bytes,
            attribute_table,
            pattern_table_bytes,
            background_palettes,
        )

        # The cache must own immutable data so callers cannot poison later hits.
        return tuple(framebuffer.pixels)


    def nametable_with_palette_ram_to_framebuffer(
        nametable_bytes: bytes,
        attribute_table: bytes,
        pattern_table_bytes: bytes,
        palette_ram: bytes,
    ) -> Framebuffer:
        cached_pixels = _cached_nametable_with_palette_ram_pixels(
            nametable_bytes,
            attribute_table,
            pattern_table_bytes,
            palette_ram,
        )

        # Preserve the historical mutable ownership contract.
        return Framebuffer(
            width=BACKGROUND_WIDTH,
            height=BACKGROUND_HEIGHT,
            pixels=list(cached_pixels),
        )

Where to edit:
Replace the existing body of nametable_with_palette_ram_to_framebuffer() with the
wrapper shown above, and add the new private cached helper beside it. Do not keep the
old palette-building/rendering statements in the public wrapper, because that would
perform the expensive work before consulting the cache.

Type-checking boundary:
nametable_with_attributes_to_framebuffer() returns a Framebuffer, so returning that
call directly from _cached_nametable_with_palette_ram_pixels() violates its declared
tuple[RGBColor, ...] return type. First bind the Framebuffer to the local variable
shown above, then return tuple(framebuffer.pixels). Do not change the cached helper's
annotation to Framebuffer, because that would cache mutable public state.

Important invariants:
    - all four exact immutable byte inputs participate in the cache key
    - equal byte content reuses work even when objects have different identities
    - changing any graphics input causes a cache miss
    - cached pixels are immutable
    - public Framebuffer objects and pixel lists have independent ownership
    - the cache is bounded to eight entries

Performance consequence:
Cache hits avoid pattern decoding, palette reconstruction, tile traversal, and RGB
pixel generation. Cache misses preserve the original rendering path, so changing any
visual input still produces fresh and correct pixels. The size limit bounds memory use
while retaining recently reused nametable images.

Common misconception:
Do not cache and return one mutable Framebuffer instance. The speed mechanism is
reusing immutable pixel content, not sharing mutable frame ownership.
"""

from emulator.ppu.chr_decoder import PATTERN_TABLE_SIZE
from emulator.rendering import nametable_renderer
from emulator.rendering.nametable_renderer import NAMETABLE_SIZE
from emulator.rendering.palette_ram import PALETTE_RAM_SIZE


def test_cache_nametable_pixels_reuses_work_without_sharing_framebuffers(monkeypatch):
    """Verify cache reuse, invalidation, boundedness, and ownership together."""
    cached_builder = (
        nametable_renderer._cached_nametable_with_palette_ram_pixels
    )
    original_render = nametable_renderer.nametable_with_attributes_to_framebuffer
    render_calls = 0

    def counting_render(*args, **kwargs):
        nonlocal render_calls
        render_calls += 1
        return original_render(*args, **kwargs)

    nametable = bytes(NAMETABLE_SIZE)
    attributes = bytes(64)
    pattern_table = bytes(PATTERN_TABLE_SIZE)
    palette_ram = bytes(PALETTE_RAM_SIZE)

    equal_nametable = bytes(bytearray(nametable))
    equal_attributes = bytes(bytearray(attributes))
    equal_pattern_table = bytes(bytearray(pattern_table))
    equal_palette_ram = bytes(bytearray(palette_ram))
    changed_nametable = bytes([1]) + nametable[1:]
    changed_attributes = bytes([1]) + attributes[1:]
    changed_pattern_table = bytes([1]) + pattern_table[1:]
    changed_palette_ram = bytes([1]) + palette_ram[1:]

    assert equal_nametable == nametable
    assert equal_nametable is not nametable
    assert equal_attributes == attributes
    assert equal_attributes is not attributes
    assert equal_pattern_table == pattern_table
    assert equal_pattern_table is not pattern_table
    assert equal_palette_ram == palette_ram
    assert equal_palette_ram is not palette_ram

    cached_builder.cache_clear()
    monkeypatch.setattr(
        nametable_renderer,
        "nametable_with_attributes_to_framebuffer",
        counting_render,
    )

    try:
        cached_pixels = cached_builder(
            nametable,
            attributes,
            pattern_table,
            palette_ram,
        )

        assert isinstance(cached_pixels, tuple)

        first = nametable_renderer.nametable_with_palette_ram_to_framebuffer(
            nametable,
            attributes,
            pattern_table,
            palette_ram,
        )
        second = nametable_renderer.nametable_with_palette_ram_to_framebuffer(
            equal_nametable,
            equal_attributes,
            equal_pattern_table,
            equal_palette_ram,
        )

        assert render_calls == 1
        assert first is not second
        assert first.pixels == second.pixels
        assert first.pixels is not second.pixels

        expected_first_pixel = second.pixels[0]
        first.pixels[0] = (1, 2, 3)

        third = nametable_renderer.nametable_with_palette_ram_to_framebuffer(
            nametable,
            attributes,
            pattern_table,
            palette_ram,
        )

        assert third.pixels[0] == expected_first_pixel
        assert render_calls == 1

        nametable_renderer.nametable_with_palette_ram_to_framebuffer(
            changed_nametable,
            attributes,
            pattern_table,
            palette_ram,
        )
        nametable_renderer.nametable_with_palette_ram_to_framebuffer(
            nametable,
            changed_attributes,
            pattern_table,
            palette_ram,
        )
        nametable_renderer.nametable_with_palette_ram_to_framebuffer(
            nametable,
            attributes,
            changed_pattern_table,
            palette_ram,
        )
        nametable_renderer.nametable_with_palette_ram_to_framebuffer(
            nametable,
            attributes,
            pattern_table,
            changed_palette_ram,
        )

        assert render_calls == 5
        assert cached_builder.cache_info().maxsize == 8
    finally:
        cached_builder.cache_clear()
