#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Benchmark a single music file against all compatible player formats.

Usage examples:
  python music_bench.py --music path/to/song.aks              # all compatible players
  python music_bench.py --music path/to/song.aks --players AKM,AKG
"""

import argparse
import json
import logging
import os
from typing import Iterable, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from datasets import MusicFormat, convert_music_file
from players import PlayerFormat, crunch_music_file, build_replay_program
from profile import profile
from utils import compute_pareto_front, draw_pareto_front


def _parse_players(raw: str | None) -> List[PlayerFormat] | None:
    if raw is None:
        return None
    result: List[PlayerFormat] = []
    for token in raw.split(","):
        t = token.strip()
        if not t:
            continue
        # Accept enum name (AKM) or value (akm)
        try:
            result.append(PlayerFormat[t.upper()])
            continue
        except KeyError:
            pass
        for pf in PlayerFormat:
            if pf.value.lower() == t.lower():
                result.append(pf)
                break
        else:
            raise ValueError(f"Unknown player format: {t}")
    return result


def _compatible_players(music_path: str, players: List[PlayerFormat] | None) -> List[PlayerFormat]:
    input_fmt = MusicFormat.get_format(music_path)
    convertible = input_fmt.convertible_to()
    candidates: Iterable[PlayerFormat] = players if players is not None else list(PlayerFormat)
    compatible: List[PlayerFormat] = []
    for pf in candidates:
        if pf in (PlayerFormat.MINY, PlayerFormat.AYC):
            continue  # not yet supported
        expected = pf.requires_one_of()
        if convertible.intersection(expected):
            compatible.append(pf)
    return compatible


def _run_for_player(music_path: str, player: PlayerFormat) -> dict:
    input_fmt = MusicFormat.get_format(music_path)
    convertible = input_fmt.convertible_to()
    expected = player.requires_one_of()

    targets = sorted(convertible.intersection(expected), key=lambda f: f.value)
    if not targets:
        raise ValueError(f"Music {music_path} not compatible with {player.name}")
    convert_to = targets[0]

    converted_fname = music_path.replace(os.path.splitext(music_path)[1], f".{convert_to.value}")
    produced_fname = player.set_extension(converted_fname)

    convert_music_file(music_path, converted_fname)
    res_conv = crunch_music_file(converted_fname, produced_fname, player)
    res_play = build_replay_program(res_conv, player)
    res_prof = profile(res_play["program_name"], player.load_address())

    return res_conv | res_play | res_prof | {"player": player.value, "source": music_path}


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark a single music file across compatible players.")
    parser.add_argument("--music", required=True, help="Path to the music file (AKS/CHP/YM/etc.)")
    parser.add_argument("--players", help="Comma-separated player formats to force (e.g., AKM,AKG,FAP). If omitted, all compatible players are used.")
    parser.add_argument("--out-json", help="Optional path to save aggregated results as JSON")
    parser.add_argument("--save-plot", help="Optional path to save the Pareto front scatter plot (PNG)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    music_path = args.music
    assert os.path.exists(music_path), f"Music file not found: {music_path}"

    requested_players = _parse_players(args.players)
    players = _compatible_players(music_path, requested_players)
    if not players:
        raise SystemExit("No compatible players found for this music file and selection.")

    results = []
    for pf in players:
        logging.info(f"Benchmarking {music_path} with player {pf.name}")
        res = _run_for_player(music_path, pf)
        results.append(res)

    # Pretty print results via pandas
    df = pd.DataFrame(results)
    preferred_cols = [
        "player",
        "program_size",
        "program_zx0_size",
        "nops_exec_min",
        "nops_exec_max",
        "nops_exec_mean",
        "nops_exec_median",
        "nops_init",
        "data_size",
        "buffer_size",
        "source",
    ]
    cols = [c for c in preferred_cols if c in df.columns]
    print("\n" + df[cols].to_markdown(index=False))

    # Generate scatter plot with Pareto front
    if len(df) > 1 and "program_size" in df.columns and "nops_exec_max" in df.columns:
        _plot_pareto_scatter(df, music_path, args.save_plot)

    if args.out_json:
        with open(args.out_json, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        logging.info(f"Saved results to {args.out_json}")


def _plot_pareto_scatter(df: pd.DataFrame, music_path: str, save_plot: str | None = None) -> None:
    """Generate scatter plot of program size vs execution time with Pareto front."""
    fig, ax = plt.subplots(figsize=(10, 6))

    # Create color palette
    format_palette = sns.color_palette("tab10", n_colors=len(df))
    format_colors = dict(zip(df["player"], format_palette))

    # Plot points
    for _, row in df.iterrows():
        color = format_colors[row["player"]]
        ax.scatter(row["program_size"], row["nops_exec_max"], s=150, alpha=0.7, color=color, label=row["player"])
        ax.annotate(row["player"], (row["program_size"], row["nops_exec_max"]),
                   xytext=(5, 5), textcoords="offset points", fontsize=9)

    # Compute Pareto front
    pareto_indices = compute_pareto_front(df, "program_size", "nops_exec_max")
    draw_pareto_front(ax, df, pareto_indices, "program_size", "nops_exec_max", scatter_size=180, include_label=True)

    ax.set_xlabel("Program Size (bytes)")
    ax.set_ylabel("Maximum Execution Time (nops)")
    music_name = os.path.splitext(os.path.basename(music_path))[0]
    ax.set_title(f"{music_name} - Player Comparison")
    ax.legend(loc="best", fontsize=9)
    ax.grid(True, alpha=0.3)

    if save_plot:
        try:
            os.makedirs(os.path.dirname(save_plot) or ".", exist_ok=True)
            fig.savefig(save_plot, dpi=100, bbox_inches='tight')
            logging.info(f"Saved plot to {save_plot}")
        except Exception as e:
            logging.error(f"Failed to save plot: {e}")

    plt.show()


if __name__ == "__main__":
    main()
