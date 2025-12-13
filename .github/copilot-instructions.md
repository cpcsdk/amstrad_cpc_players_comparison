# Amstrad CPC Player Benchmark — AI Coding Instructions (concise)

This file gives targeted guidance for AI coding agents working on this repository.

1) Big picture
- Purpose: measure final executable sizes and Z80 profiling for many player/music combinations.
- Core flow: `datasets.py` (convert music) → `players.py` (crunch/compile) → `benchmark.py` / `player_bench.py` (orchestrate) → `profile.py` (Z80 profiling) → JSON reports in `datasets/` and `reports/`.

2) Critical files to inspect first
- `player_bench.py` — CLI entry and benchmark selection.
- `benchmark.py` — base `Benchmark` and lifecycle: `build_files()` → `analyse_files()`.
- `datasets.py` — format enums (`MusicFormat`) and dataset iteration/conversion.
- `players.py` — player dispatch table, per-player crunch/compile functions, and `bndbuild` usage.
- `profile.py` — CSV parsing from `Z80Profiler.exe` and metric extraction.

3) External tools & environment
- `bndbuild` is required for most conversions (SongToYm, chipnsfx, SongToAkm/aky/akg, ayt, fap, zx0, basm). Calls are fragile and use platform-specific escaping.
- `Z80Profiler.exe` (Windows) produces CSVs consumed by `profile.py`.
- On Linux: many flows were tested on Windows only — expect tool availability gaps. Do not assume `bndbuild` or `Z80Profiler.exe` exist.

4) Project-specific patterns and gotchas
- Dispatch table pattern in `players.py`: lookup by `PlayerFormat` returns (builder, params). Avoid if-chains.
- JSON caching: produced artifacts are cached as `<output>.json`. Skip regeneration if JSON exists — do not delete these files lightly.
- Parallelism: `joblib.Parallel(..., n_jobs=1)` is intentionally disabled. External tools are not thread-safe; change cautiously.
- Windows path escaping: code contains logic to triple-escape backslashes for `bndbuild`. Keep this when modifying subprocess commands.

5) How to run (common commands)
```bash
python player_bench.py                # run all benchmarks
python player_bench.py --benchmark AT3
python player_bench.py --benchmark AT3 --clean
```

6) When editing code that calls external tools
- Keep argument quoting and path escaping exactly as in `players.py`.
- Preserve `if os.path.exists(json_fname):` short-circuit behavior to avoid long rebuilds.
- If adding new conversions, verify compatibility in `PlayerFormat.requires_one_of()` and update dispatch table.

7) Reporting and outputs
- Per-song metrics: `datasets/.../*.json` (cached)
- Human reports: `reports/report_*.md`

8) Quick debugging tips
- Re-run a single conversion manually for fast iteration (use small dataset subset).
- Check `players/` subfolders for intermediate binaries for each player format.

If anything above is unclear or you want more detail for a section (example commands, tool install tips, or merged legacy content), tell me which part to expand.
