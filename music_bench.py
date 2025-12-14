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

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd
import seaborn as sns

from datasets import MusicFormat, convert_music_file
from players import PlayerFormat, crunch_music_file, build_replay_program
from player_utils import (
    parse_players,
    sanitize_filename,
    find_compatible_players,
    find_conversion_target,
    generate_conversion_paths,
)
from profile import profile
from utils import compute_pareto_front, draw_pareto_front


def _run_for_player(music_path: str, player: PlayerFormat) -> dict:
    convert_to = find_conversion_target(music_path, player)
    converted_fname, produced_fname = generate_conversion_paths(
        music_path, convert_to, player
    )

    convert_music_file(music_path, converted_fname)
    res_conv = crunch_music_file(converted_fname, produced_fname, player)
    res_play = build_replay_program(res_conv, player)
    res_prof = profile(res_play["program_name"], player.load_address())

    return (
        res_conv | res_play | res_prof | {"player": player.value, "source": music_path}
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark a single music file across compatible players."
    )
    parser.add_argument(
        "--music", required=True, help="Path to the music file (AKS/CHP/YM/etc.)"
    )
    parser.add_argument(
        "--players",
        help="Comma-separated player formats to force (e.g., AKM,AKG,FAP). If omitted, all compatible players are used.",
    )
    parser.add_argument(
        "--out-json", help="Optional path to save aggregated results as JSON"
    )
    parser.add_argument(
        "--save-plot", help="Optional path to save the Pareto front scatter plot (PNG)"
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Display the plot interactively (requires GUI)",
    )
    args = parser.parse_args()

    # Set matplotlib backend based on --show flag
    if not args.show:
        matplotlib.use("Agg")  # Headless backend when not showing interactively

    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    music_path = args.music
    assert os.path.exists(music_path), f"Music file not found: {music_path}"

    # Handle filenames with special characters
    original_path = music_path
    music_path, needs_cleanup = sanitize_filename(music_path)

    requested_players = parse_players(args.players)
    players = find_compatible_players(music_path, requested_players)
    if not players:
        raise SystemExit(
            "No compatible players found for this music file and selection."
        )

    results = []
    for pf in players:
        logging.info(f"Benchmarking {original_path} with player {pf.name}")
        res = _run_for_player(music_path, pf)
        # Update source to reflect original path
        res["source"] = original_path
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
        _plot_pareto_scatter(df, original_path, args.save_plot, args.show)

    if args.out_json:
        # Use safe write helper to avoid partial files
        from utils import safe_write_json

        safe_write_json(args.out_json, results, indent=2)
        logging.info(f"Saved results to {args.out_json}")

    # Cleanup: remove sanitized symlink/copy if we created it
    if needs_cleanup and os.path.exists(music_path) and music_path != original_path:
        try:
            os.remove(music_path)
            logging.debug(f"Cleaned up temporary file: {music_path}")
        except Exception:
            pass


def _plot_pareto_scatter(
    df: pd.DataFrame,
    music_path: str,
    save_plot: str | None = None,
    show_plot: bool = False,
) -> None:
    """Generate scatter plot of program size vs execution time with Pareto front."""
    fig, ax = plt.subplots(figsize=(10, 6))

    # Create color palette
    format_palette = sns.color_palette("tab10", n_colors=len(df))
    format_colors = dict(zip(df["player"], format_palette))

    # Plot points
    for _, row in df.iterrows():
        color = format_colors[row["player"]]
        # Resolve player format robustly: accept enum name or value
        try:
            player_format = PlayerFormat[row["player"].upper()]
        except KeyError:
            # fallback: lookup by value
            player_format = next(
                (
                    pf
                    for pf in PlayerFormat
                    if pf.value.lower() == str(row["player"]).lower()
                ),
                None,
            )
            if player_format is None:
                raise KeyError(f"Unknown player format: {row['player']}")
        marker = "s" if player_format.is_stable() else "o"
        ax.scatter(
            row["program_size"],
            row["nops_exec_max"],
            s=150,
            alpha=0.7,
            color=color,
            marker=marker,
            label=row["player"],
        )
        ax.annotate(
            row["player"],
            (row["program_size"], row["nops_exec_max"]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=9,
        )

    # Compute Pareto front
    pareto_indices = compute_pareto_front(df, "program_size", "nops_exec_max")
    draw_pareto_front(
        ax,
        df,
        pareto_indices,
        "program_size",
        "nops_exec_max",
        scatter_size=180,
        include_label=True,
    )

    ax.set_xlabel("Program Size (bytes)")
    ax.set_ylabel("Maximum Execution Time (nops)")
    music_name = os.path.splitext(os.path.basename(music_path))[0]
    ax.set_title(f"{music_name} - Player Comparison")
    ax.legend(loc="best", fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)

    # Format x-axis as hexadecimal with decimal in parentheses
    ax.xaxis.set_major_formatter(
        FuncFormatter(lambda x, pos: f"0x{int(x):04X} ({int(x)})")
    )

    if save_plot:
        try:
            os.makedirs(os.path.dirname(save_plot) or ".", exist_ok=True)
            fig.savefig(save_plot, dpi=100, bbox_inches="tight")
            logging.info(f"Saved plot to {save_plot}")
        except Exception as e:
            logging.error(f"Failed to save plot: {e}")
    elif not show_plot:
        # When save_plot is not specified and not showing, save to a default location
        default_plot_path = "music_bench_plot.png"
        try:
            fig.savefig(default_plot_path, dpi=100, bbox_inches="tight")
            logging.info(f"Saved plot to {default_plot_path}")
        except Exception as e:
            logging.error(f"Failed to save plot: {e}")

    if show_plot:
        plt.show()  # Display plot interactively
    else:
        plt.close(fig)  # Close figure to free memory


if __name__ == "__main__":
    main()
