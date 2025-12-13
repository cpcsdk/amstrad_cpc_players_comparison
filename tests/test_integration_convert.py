import shutil
from pathlib import Path
import logging
import pytest
import sys

# Ensure repo root is on sys.path so tests can import project modules
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

from datasets import At3Dataset, MusicFormat, convert_music_file


@pytest.mark.skipif(shutil.which("bndbuild") is None, reason="bndbuild not found in PATH")
def test_convert_one_at3_song_to_ym(tmp_path):
    """Integration test: copy one AT3 dataset song to tmp and convert to .ym.

    This reproduces the real-world case that failed on Linux (filenames
    containing `&`, spaces). Test is skipped when `bndbuild` is not present.
    """
    logging.basicConfig(level=logging.DEBUG)

    d = At3Dataset()
    # pick the first file that requires Arkos->YM conversion
    src = None
    for f in d:
        fmt = MusicFormat.get_format(f)
        # Arkos types that convert to YM6
        if fmt in (MusicFormat.ST, MusicFormat.SKS, MusicFormat.AKS, MusicFormat.VT2, MusicFormat.WYZ):
            src = Path(f)
            break

    assert src is not None, "No AT3 source file found for integration test"

    dest_input = tmp_path / src.name
    shutil.copyfile(src, dest_input)

    out_path = dest_input.with_suffix(".ym")

    # Should not raise
    convert_music_file(str(dest_input), str(out_path))

    assert out_path.exists()
    assert out_path.stat().st_size > 0
