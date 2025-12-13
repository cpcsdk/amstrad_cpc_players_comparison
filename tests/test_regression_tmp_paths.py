import os
import json
import shutil
import tempfile

import pytest

# Ensure project root is on sys.path so imports like `benchmark` work when pytest
# runs from the repository root or other CWDs.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmark import Benchmark
from players import PlayerFormat
from datasets import Dataset, MusicFormat


class SingleFileDataset(Dataset):
    def __init__(self, path):
        super().__init__(path)

    def __iter__(self):
        for f in [self.path]:
            yield f


def test_tmp_path_copyback_and_json_remapping(monkeypatch, tmp_path):
    # Create a music file with special characters in its name
    src_dir = tmp_path / "datasets" / "special"
    src_dir.mkdir(parents=True)
    fname = "weird name's & test.aks"
    music_path = src_dir / fname
    music_path.write_bytes(b"dummy music data")

    # Create a Dataset pointing to that file
    ds = SingleFileDataset(str(music_path))

    # Monkeypatch conversion/compile/build/profile to avoid external tools
    def fake_convert(input_file, output_file):
        # avoid copying if source and dest are the same (can happen when
        # the sanitized working input already equals the converted path)
        if os.path.abspath(input_file) == os.path.abspath(output_file):
            return
        shutil.copyfile(input_file, output_file)

    def fake_crunch(input_file, output_file, format):
        # create the output file in whatever dir was requested
        with open(output_file, "wb") as f:
            f.write(b"crunched")
        return {
            "original_fname": input_file,
            "compressed_fname": output_file,
            "stdout": "",
            "stderr": "",
            "buffer_size": 0,
            "data_size": os.path.getsize(output_file),
            "play_time": 0,
        }

    def fake_build(res_conv, player):
        # create program files next to compressed_fname (simulate tmpdir creations)
        comp = res_conv["compressed_fname"]
        base = os.path.splitext(comp)[0]
        binf = base + ".BIN"
        zx0 = binf + ".zx0"
        with open(binf, "wb") as f:
            f.write(b"BIN")
        with open(zx0, "wb") as f:
            f.write(b"ZX0")
        return {"program_name": binf, "program_size": os.path.getsize(binf), "program_zx0_size": os.path.getsize(zx0)}

    def fake_profile(program_name, load_addr):
        return {"nops_init": 1, "nops_exec_min": 1, "nops_exec_max": 1, "nops_exec_mean": 1, "nops_exec_std": 0, "nops_exec_median": 1}

    monkeypatch.setattr("datasets.convert_music_file", fake_convert)
    monkeypatch.setattr("players.crunch_music_file", fake_crunch)
    monkeypatch.setattr("players.build_replay_program", fake_build)
    monkeypatch.setattr("profile.profile", fake_profile)
    # benchmark module imports many names with `from ... import *`,
    # ensure the benchmark module uses our fakes as well.
    monkeypatch.setattr("benchmark.convert_music_file", fake_convert)
    monkeypatch.setattr("benchmark.crunch_music_file", fake_crunch)
    monkeypatch.setattr("benchmark.build_replay_program", fake_build)
    monkeypatch.setattr("benchmark.profile", fake_profile)

    # joblib.Parallel used in Benchmark.build_files spawns processes by
    # default; to keep the test deterministic and keep monkeypatches local
    # to this process, replace `Parallel` with a simple sequential runner.
    class FakeParallel:
        def __init__(self, n_jobs=None, verbose=0):
            pass

        def __call__(self, tasks):
            results = []
            for task in tasks:
                # Delayed objects from joblib may be Delayed objects with
                # attributes or simple tuples (func, args, kwargs).
                if isinstance(task, tuple) and len(task) >= 1:
                    func = task[0]
                    args = task[1] if len(task) > 1 else ()
                    kwargs = task[2] if len(task) > 2 else {}
                    results.append(func(*args, **(kwargs or {})))
                    continue

                func = getattr(task, "func", None)
                args = getattr(task, "args", ())
                kwargs = getattr(task, "kwargs", {})
                if func is not None:
                    results.append(func(*args, **(kwargs or {})))
                else:
                    # fallback: try calling the task directly
                    results.append(task())
            return results

    monkeypatch.setattr("benchmark.Parallel", FakeParallel)

    # Run the benchmark on our single-file dataset
    bench = Benchmark("TEST", ds, players=[PlayerFormat.AKG])

    results = bench.build_files()

    # find generated json files under the dataset folder (not /tmp)
    jsons = list(src_dir.glob("*.json"))
    assert jsons, "No JSON result produced next to dataset file"

    for j in jsons:
        content = j.read_text(encoding="utf-8")
        # Ensure we didn't leak the temporary *processing* directory used for
        # sanitization (playerbench-...), but the dataset itself may live
        # under /tmp for pytest's tmp_path fixture so we only reject the
        # playerbench temp dir pattern.
        assert "/tmp/playerbench-" not in content, f"JSON contains temporary processing paths: {j}"

    # verify produced program files exist next to the dataset file
    bin_files = list(src_dir.glob("*.BIN"))
    assert bin_files, "No BIN files copied back to dataset folder"
