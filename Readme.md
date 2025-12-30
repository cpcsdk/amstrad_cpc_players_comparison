# Player benchmark for Amstrad CPC

## Aim

The aim of this repository is to benchmark state-of-the-art music players on the Amstrad CPC.

For a given dataset, songs are converted to various replay formats and an executable is built for each format. The length of the executable is then retrieved and compared across players.

Why use the executable length rather than the player and music file size?

- All extra boilerplate is common to all players, so it does not count in the comparison (we can subtract it if needed).
- Some players require a buffer; that buffer must be included in the size.
- Some players save the stack pointer; that mechanism is considered part of the player routine and should be included.
- Some players generate code at build-time; even if the generated code can be removed after usage, it should be accounted for.

Execution duration will be collected in future versions; currently only FAP exposes duration automatically and easily.

## Requirements

- **Python 3.10+** (uses modern type hints)
- **bndbuild** — CPC development tool suite (automatically resolved, see below)

## Installation

```bash
# Clone the repository
git clone https://github.com/cpcsdk/amstrad_cpc_players_comparison.git
cd amstrad_cpc_players_comparison

# Create a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

## Current bugs

- There is a bug in the execution program for AKM: the program can crash.
- There is a bug with the minimiser: the program systematically crashes.
- Pacidemo dataset is not usable at the moment.
- There is a bug with FAP for some music files: the player execution is incorrect and consumes too many NOPs.

## Current limitations & known issues

- This started as a solo project — contributions are very welcome.
- Cache handling is limited in some flows; many conversions avoid rebuilding if dataset JSON artifacts exist, but some operations still re-run external tools.
- Some datasets (e.g. Pacidemo) are flagged as problematic.
- AYC cruncher is missing (may require a PC tool or an emulator-based approach).
- A few players (AKM, minimiser, FAP corner cases) have runtime issues; see `reports/` and the issue tracker for details.

## Usage

To launch the current benchmark (example):

```bash
python player_bench.py --bench AT3
```

To benchmark all compatible players for a single music file:

```bash
python music_bench.py --music path/to/song.aks
```

Additional CLI options are available; run `python player_bench.py --help`.

## Dependencies

See `requirements.txt` for Python dependencies. External tools required:

- `bndbuild` — used for conversions/crunchers. The repo will attempt to resolve it automatically (see bndbuild handling below).

## bndbuild handling

The project locates `bndbuild` in this order:

1. `BNDBUILD_PATH` environment variable (explicit path)
2. `./tools/bndbuild` (or `bndbuild.exe` on Windows)
3. system `bndbuild` on PATH
4. if not found, the repo will download a release asset (default URLs used by CI), or you can set `BNDBUILD_DOWNLOAD_URL` to a custom URL.

To force a specific binary:

```bash
export BNDBUILD_PATH=/path/to/bndbuild
```

To force download of the repo-provided release asset:

```bash
export BNDBUILD_DOWNLOAD_URL=https://github.com/cpcsdk/rust.cpclib/releases/download/latest/bndbuild
```

## Output & reports

- Per-song JSON artifacts are written under `datasets/` and `reports/`.
- Human-readable report markdown files are generated under `reports/report_*.md`.
- Plots are produced with a headless backend (matplotlib Agg) so CI can run without a display.

## Testing

Unit tests live in `tests/`. Run them locally with:

```bash
pytest -q
```

## CI

A GitHub Actions workflow is included at `.github/workflows/ci.yml`. It creates a venv, installs dependencies, resolves `bndbuild` (download URL configurable with `BNDBUILD_DOWNLOAD_URL`) and runs tests.

## Configuration & environment

- `BNDBUILD_PATH`: path to a `bndbuild` binary (overrides download)
- `BNDBUILD_DOWNLOAD_URL`: URL to download a `bndbuild` binary if none is found

## Troubleshooting

- If `bndbuild` resolution fails, set `BNDBUILD_PATH` to a local binary or provide `BNDBUILD_DOWNLOAD_URL`.
- If plots fail in CI, ensure matplotlib is installed in the venv and the Agg backend is available (the repo configures Agg for headless runs).

## Datasets evaluation

- See [reports/report_AT3.md](reports/report_AT3.md) for an example report.

