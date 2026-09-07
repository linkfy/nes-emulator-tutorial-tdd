# NES Emulator Tutorial By Test Driven Development

Build a small, understandable Nintendo Entertainment System emulator from scratch by
following the ordered test-driven development lessons numbered through Test 356.

## Final Implementation Example

The completed reference implementation is available at
[linkfy/N1_TDD](https://github.com/linkfy/N1_TDD).

This is a **tests-only starter project**. It intentionally does not contain the
completed emulator. The `tests/` directory is the curriculum: each numbered test
explains why the next behavior matters, which production file to create or update,
and the smallest implementation expected at that point.

## Objective

The goal is to learn emulator architecture and TDD by incrementally building:

- A useful subset of the MOS 6502 CPU used by the NES.
- CPU RAM, buses, iNES parsing, and NROM cartridge mapping.
- PPU registers, memory, timing, VBlank, and NMI coordination.
- Background, palette, nametable, attribute-table, and sprite rendering.
- Controller input, OAM DMA, sprite priority, and sprite-zero-hit behavior.
- Horizontal nametable mirroring and scrolling.
- A pygame manual frontend with keyboard input and frame pacing.
- Measured rendering caches that make the final PyPy runtime approach 60 FPS.

The emphasis is clarity and incremental understanding, not complete hardware
emulation.

## Project Scope

The final tutorial supports the following focused path:

- Mapper 000 / NROM cartridges only.
- CHR ROM and the Mapper 000 behavior introduced by the lessons.
- Horizontal and vertical cartridge nametable mirroring.
- Horizontal scrolling with timed per-scanline PPU scroll state.
- 8x8 sprites, sprite/background priority, and a simplified sprite-zero-hit path.
- One standard NES controller through `$4016`.
- A pygame-ce manual display and keyboard frontend.
- CPython for normal tests and optional PyPy for the final manual performance path.

## Non-Goals

The tutorial deliberately does not attempt to provide a complete NES implementation.
The following remain outside its final scope:

- Audio synthesis or a complete APU. Required audio-register writes are explicit
  no-ops so supported ROMs can continue running.
- Complete visible vertical scrolling across vertically adjacent nametables.
- Mappers other than Mapper 000 / NROM.
- Save states, battery-backed saves, rewind, netplay, or debugger UI.
- Cycle-perfect CPU, PPU, DMA, NMI, or sprite evaluation behavior.
- 8x16 sprites and authentic sprite-overflow quirks.
- Every sprite-zero-hit edge case, including complete left-edge masking and the
  hardware `x=255` exception.
- PAL timing, region selection, shaders, audio synchronization, and production-grade
  input configuration.
- Passing arbitrary commercial ROM compatibility suites.

## Prerequisites

- Linux, macOS, or Windows.
- [uv](https://docs.astral.sh/uv/) for Python and dependency management.
- Git for saving your progress.
- A text editor or IDE with Python support.
- Optional: Pyright or another type checker.
- Legal local copies of the following Mapper 000 / NROM games for the manual
  checkpoints. Automated tests do not use these files.

| Game | Required local filename | SHA-256 of the verified tutorial dump |
|---|---|---|
| Mario Bros. | `MarioBros.nes` | `a2a0aa437a735cd36ed29a8e7c5b3dfa10590c6203e893f1668c7995bad2b309` |
| Super Mario Bros. | `Super Mario Bros.nes` | `f61548fdf1670cffefcc4f0b7bdcdd9eaba0c226e3b74f8666071496988248de` |

These hashes identify the ROM revisions used during tutorial development. Other
legitimate dumps or revisions may differ. You must provide your own legally obtained
copies; ROM files are not included and are ignored by Git.

The repository pins its normal development interpreter in `.python-version` and locks
dependencies in `uv.lock`.

## Install uv

Follow the official installation instructions:

<https://docs.astral.sh/uv/getting-started/installation/>

Confirm the installation:

```bash
uv --version
```

## Initialize the Environment

The project is already initialized. Do **not** run `uv init` inside this repository;
that command is only needed when creating a new uv project from an empty directory.

From the project root, create the virtual environment and install locked dependencies:

```bash
uv sync
```

If this directory is not already inside a Git repository, initialize one before your
first lesson:

```bash
git init
git add README.md pyproject.toml uv.lock .python-version .gitignore tests
git commit -m "Initialize NES emulator TDD tutorial"
```

Confirm the selected Python interpreter:

```bash
uv run python --version
```

If you were reproducing this project metadata from an empty directory, the equivalent
starting workflow would be:

```bash
uv init --name nes-emulator-tutorial-by-test-driven-development --python 3.14
uv add pygame-ce
uv add --dev pytest
uv sync
```

In this repository, use the provided `pyproject.toml` and `uv.lock` instead.

## Start the Tutorial

Open the first lesson:

```text
tests/chapter_01_cpu/test_001_initial_files.py
```

Read its module-level documentation from beginning to end before writing production
code. Then run only that lesson:

```bash
uv run pytest tests/chapter_01_cpu/test_001_initial_files.py -v
```

The first failure is expected. It defines the first production behavior you must add.

## The TDD Loop

For each numbered test, follow this cycle:

1. **Read:** Understand `Why this step exists`, the vocabulary, invariants, and example.
2. **Red:** Run only the current numbered test and observe the expected failure.
3. **Green:** Create or modify only the production code required by that lesson.
4. **Verify:** Rerun the current test until it passes.
5. **Regressions:** Rerun all tests completed so far or the completed chapter.
6. **Refactor:** Improve names or structure only while all completed tests remain green.
7. **Commit:** Save one small, understandable milestone in Git.
8. **Continue:** Open the next numerical test.

Example:

```bash
uv run pytest tests/chapter_01_cpu/test_001_initial_files.py -v
# Implement only Step 001.
uv run pytest tests/chapter_01_cpu/test_001_initial_files.py -v
```

After completing a chapter:

```bash
uv run pytest tests/chapter_01_cpu -v
```

## Do Not Run the Full Future Suite Initially

The repository includes the complete curriculum, including tests for modules that do
not exist at the beginning. Running `uv run pytest` immediately will therefore produce
many expected import and collection errors.

That is not the starting test signal. Run the current numbered lesson and previously
completed lessons only.

Use the complete suite after implementing the final lesson:

```bash
uv run pytest
```

Do not solve future collection errors by creating broad fake modules or catch-all
stubs. Follow the numerical sequence so every dependency is introduced intentionally.

## Curriculum Map

| Chapter | Tests | Topic |
|---|---:|---|
| 01 | 001–211 | CPU, RAM, bus, addressing modes, instructions, flags, and validation |
| 02 | 212–223 | iNES parsing, cartridges, Mapper 000, and ROM execution |
| 03 | 224–258 | PPU registers, PPU bus, VRAM, CHR data, and graphics decoding |
| 04 | 259–269 | PPU timing, VBlank, NMI, and CPU/PPU coordination |
| 05 | 270–287 | Pure rendering pipeline, framebuffer data, and pygame helpers |
| 06 | 288–289 | ROM startup preparation, APU no-ops, and OAM DMA |
| 07 | 290–293 | NES controller protocol and `$4016` integration |
| 08 | 294–298 | Manual ROM loop, pygame frontend, keyboard input, and errors |
| 09 | 299–314 | Sprite decoding, rendering, priority, and composition |
| 10 | 315–318 | FPS reporting, fast framebuffer upload, PyPy, and initial pacing |
| 11 | 319–323 | Sprite-zero-hit detection and timing integration |
| 12 | 324–327 | Cartridge nametable mirroring |
| 13 | 328–353 | Horizontal viewport composition and timed scrolling |
| 14 | 354–356 | Immutable rendering caches and absolute-deadline frame pacing |

## Test Files Are Lessons

The tests are intentionally more explanatory than conventional application tests.
Their module docstrings contain the tutorial narrative and may show:

- `NEW LINE` or `NEW BLOCK` markers for code to add.
- `UPDATED LINE` or `UPDATED BLOCK` markers for code to change.
- `DELETED LINE` or `DELETED BLOCK` markers showing obsolete production code.
- `...` where existing code should remain unchanged.

Deleted lines shown inside a lesson are documentation. Remove those lines from
production code; do not preserve them as commented-out compatibility code.

Do not edit tests merely to make a failure disappear. If a failure is unclear, compare
your implementation with the lesson's stated behavior and public ownership contract.

## Recommended Project Structure

The tests will guide you toward a structure similar to:

```text
emulator/
├── bus/
├── cartridge/
├── cpu/
├── input/
├── memory/
├── ppu/
└── rendering/
tools/
main.py
core_validator.py
```

Do not create this entire tree in advance. Add packages and modules only when the
current test asks for them.

## Manual ROM Checkpoints

Automated tests use synthetic data and do not require commercial ROMs. Some later
lessons include optional manual checkpoints using real Mapper 000 / NROM games.

You must legally obtain your own ROM dumps. This project does not provide, download,
or authorize distribution of ROM files.

Use these local filenames when the corresponding lesson requests them:

```text
MarioBros.nes
Super Mario Bros.nes
```

Place them in the project root unless the current lesson explicitly documents another
local path. Every `.nes` file is ignored by `.gitignore`, including ROMs in subfolders.

Before committing, verify that no ROM is tracked:

```bash
git status --short
git ls-files "*.nes"
```

`git ls-files "*.nes"` should print nothing.

### Mario Bros.

Use a valid Mapper 000 / NROM Mario Bros. ROM for the first manual ROM runner and
controller checkpoints. The expected local filename is:

```text
MarioBros.nes
```

### Super Mario Bros.

Use a valid Mapper 000 / NROM Super Mario Bros. ROM for later sprite-zero-hit,
horizontal-scrolling, and performance checkpoints. The expected local filename is:

```text
Super Mario Bros.nes
```

ROM revisions may differ. Never weaken automated behavior to match one undocumented
ROM dump; the automated suite remains synthetic and deterministic.

## Running the Manual Frontend

When the relevant lessons have created `main.py`, install or select PyPy for the final
performance checks:

```bash
uv python install pypy
uv run --python pypy python main.py
```

PyPy uses a tracing JIT and may initially run below the final target. With the Chapter
14 caches and pacing implemented, allow roughly 30 seconds of warm-up before evaluating
Super Mario Bros. performance. On a machine with sufficient processing headroom,
gameplay should become smooth and remain close to the long-term 60 FPS target.

Frame pacing cannot make an over-budget frame faster. It prevents a sufficiently fast
emulator from advancing game time too quickly and limits long-term timing drift.

## Troubleshooting

### Many import errors at the beginning

You probably ran the complete future suite. Return to the current numbered test.

### Circular import errors

Read the import chain in the traceback. Shared data types should live in a lower-level
module that does not import its consumers. Remove accidental unused imports before
moving types or adding compatibility layers.

### A cache returns stale or shared state

Cache immutable tuples internally and return a fresh public list or `Framebuffer`.
Include every visual input in the cache key.

### FPS is high without pacing but low after `time.sleep()`

Short sleeps specify a minimum duration and may wake late. Follow the absolute-deadline
pacing lesson rather than adjusting the target FPS to hide scheduler latency.

### PyPy starts slowly

This is expected JIT warm-up behavior. Compare performance after reaching the same game
section and allowing hot paths to compile.

## Final Validation

After Test 356 passes:

```bash
uv run pytest
uv run --python pypy python main.py
```

Confirm that:

- The complete automated suite passes.
- Mario Bros. boots and controller input works.
- Super Mario Bros. progresses past sprite-zero-hit waits.
- Horizontal scrolling and the fixed status-bar split behave as taught.
- The renderer does not expose shared mutable cache state.
- The warmed manual frontend remains near its long-term 60 FPS target.
- No `.nes` file is tracked by Git.

## Academic Use

The tests provide substantial guidance and complete examples where appropriate. You
will learn more by implementing one lesson at a time, explaining each invariant in your
own words, and resisting the temptation to copy a completed emulator into the project.
