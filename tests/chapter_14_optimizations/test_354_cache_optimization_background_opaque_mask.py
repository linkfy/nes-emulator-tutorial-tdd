"""
Test 354 — Begin Chapter 14 by caching repeated background opacity-mask construction.

File to update:
    emulator/rendering/nametable_renderer.py

Why this small optimization exists:
The viewport renderer and sprite-zero-hit preparation can request an opacity mask for
the same pattern-table and nametable bytes. Building that mask repeatedly decodes 256
CHR tiles and visits every pixel in a 256x240 background.

An LRU cache stores a recently computed result and evicts the least recently used
entry when its size limit is reached. Here, the exact immutable input bytes are the
cache key:

    same pattern bytes + same nametable bytes -> cache hit
    changed pattern bytes or nametable bytes  -> cache miss

The easy implementation is a small boundary change rather than a rendering rewrite:

    from functools import lru_cache

    # This is our old build_background_opaque_mask implementation under a private
    # name. It now returns a tuple so callers cannot mutate the cached value. A
    # public wrapper below will preserve the historical mutable list API.
    @lru_cache(maxsize=8)
    def _cached_background_opaque_mask(
        pattern_table: bytes,
        nametable: bytes,
    ) -> tuple[bool, ...]:
        if len(nametable) != NAMETABLE_SIZE:
            raise ValueError("Nametable must be 960 bytes")

        decoded_tiles = decode_pattern_table(pattern_table)
        opaque_mask: BackgroundOpaqueMask = [False] * (
            BACKGROUND_WIDTH * BACKGROUND_HEIGHT
        )

        for tile_y in range(NAMETABLE_ROWS):
            for tile_x in range(NAMETABLE_TILES_PER_ROW):
                nametable_index = (
                    tile_y * NAMETABLE_TILES_PER_ROW + tile_x
                )
                tile_index = nametable[nametable_index]
                tile = decoded_tiles[tile_index]

                for pixel_y in range(CHR_TILE_HEIGHT):
                    for pixel_x in range(CHR_TILE_WIDTH):
                        color_index = tile[pixel_y][pixel_x]

                        screen_x = tile_x * CHR_TILE_WIDTH + pixel_x
                        screen_y = tile_y * CHR_TILE_HEIGHT + pixel_y
                        mask_index = (
                            screen_y * BACKGROUND_WIDTH + screen_x
                        )

                        opaque_mask[mask_index] = color_index != 0

        return tuple(opaque_mask)


    def build_background_opaque_mask(
        pattern_table: bytes,
        nametable: bytes,
    ) -> BackgroundOpaqueMask:
        return list(_cached_background_opaque_mask(pattern_table, nametable))

Why cache a tuple but return a list?
functools.lru_cache returns the exact stored object; it does not make a copy. Caching
the public mutable list directly would let one caller modify the result observed by
future callers. The private tuple makes cached state immutable, while the public list
copy preserves the historical BackgroundOpaqueMask API and independent ownership.

This test checks one complete contract:
    - identical content performs the expensive decode only once
    - public results are equal but are different list objects
    - mutating one result cannot poison a later cache hit
    - changed nametable content causes a cache miss
    - the cache is bounded to eight entries

Common misconception:
The optimization is not based on object identity or frame number. Two different bytes
objects with equal content compare as the same cache key, while changed graphics data
naturally forms a different key without an explicit invalidation signal from the PPU.
"""

from emulator.ppu.chr_decoder import PATTERN_TABLE_SIZE
from emulator.rendering import nametable_renderer
from emulator.rendering.nametable_renderer import NAMETABLE_SIZE


def test_cache_optimization_reuses_work_without_sharing_mutable_results(monkeypatch):
    """Verify the speed mechanism and the public ownership boundary together."""
    cached_builder = nametable_renderer._cached_background_opaque_mask
    original_decode = nametable_renderer.decode_pattern_table
    decode_calls = 0

    def counting_decode(pattern_table: bytes):
        nonlocal decode_calls
        decode_calls += 1
        return original_decode(pattern_table)

    pattern_table = bytes(PATTERN_TABLE_SIZE)
    nametable = bytes(NAMETABLE_SIZE)
    equal_pattern_table = bytes(bytearray(pattern_table))
    equal_nametable = bytes(bytearray(nametable))
    changed_nametable = bytes([1]) + nametable[1:]

    assert equal_pattern_table == pattern_table
    assert equal_pattern_table is not pattern_table
    assert equal_nametable == nametable
    assert equal_nametable is not nametable

    cached_builder.cache_clear()
    monkeypatch.setattr(
        nametable_renderer,
        "decode_pattern_table",
        counting_decode,
    )

    try:
        first = nametable_renderer.build_background_opaque_mask(
            pattern_table,
            nametable,
        )
        second = nametable_renderer.build_background_opaque_mask(
            equal_pattern_table,
            equal_nametable,
        )

        assert decode_calls == 1
        assert first == second
        assert first is not second

        first[0] = True
        third = nametable_renderer.build_background_opaque_mask(
            pattern_table,
            nametable,
        )

        assert third[0] is False
        assert decode_calls == 1

        nametable_renderer.build_background_opaque_mask(
            pattern_table,
            changed_nametable,
        )

        assert decode_calls == 2
        assert cached_builder.cache_info().maxsize == 8
    finally:
        cached_builder.cache_clear()
