import sys
import os
import pytest
import pandas as pd

# Ensure repository root is on sys.path for imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import plots
from players import PlayerFormat


class DummyBenchmark:
    def __init__(self, players):
        # players should be a list of PlayerFormat
        self.players = players


def test_prepare_format_colors_preserves_order_and_keys():
    # players defined in preferred order
    players = [PlayerFormat.AYT, PlayerFormat.AKG, PlayerFormat.AKM]
    bench = DummyBenchmark(players)

    # DataFrame with only AYG and AKM present (AKG will be missing)
    data = {
        "format": [p.name for p in [PlayerFormat.AYT, PlayerFormat.AKM, PlayerFormat.AYT]],
        "prog_size": [100, 120, 110],
        "sources": ["a", "b", "c"]
    }
    df = pd.DataFrame(data)

    ordered_extensions, format_colors = plots.prepare_format_colors(bench, df)

    # Should preserve benchmark players order but only include those present in df
    assert ordered_extensions == [PlayerFormat.AYT.name, PlayerFormat.AKM.name]
    # format_colors should have keys equal to ordered_extensions
    assert set(format_colors.keys()) == set(ordered_extensions)
    # color values should be tuples/lists with 3 floats (RGB)
    for v in format_colors.values():
        assert hasattr(v, "__len__") and len(v) >= 3


def test__palette_for_ordered_none_when_no_input():
    res = plots._palette_for_ordered(None, ["A", "B"])  # None input should return None
    assert res is None


def test__palette_for_ordered_maps_chpb_to_chp_and_fills_missing():
    ordered = ["CHPB", "FOO"]
    # Provide explicit color only for CHPB
    explicit = {"CHPB": (1.0, 0.0, 0.0)}
    palette = plots._palette_for_ordered(explicit, ordered)

    # Must include CHPB and CHP mapping and FOO (auto-filled)
    assert "CHPB" in palette
    assert "CHP" in palette
    assert palette["CHPB"] == palette["CHP"]
    assert "FOO" in palette
