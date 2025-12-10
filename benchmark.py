#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# Filename: player_bench.py
# License: MIT License
# Author: Krusty/Benediction
# Date: 2025-11-11
# Version: 0.1
# Description: This file store all necessary to encode benchmarks and execute them


import os
import logging
import json
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from itertools import combinations
from joblib import delayed, Parallel
from scipy.stats import wilcoxon
from math import pi
from matplotlib.patches import Ellipse

from datasets import *
from players import *
from profile import *
from utils import compute_pareto_front, draw_pareto_front

class Benchmark:
    def __init__(self, name: str, dataset: Dataset, players: list | None = None) -> None:
        if players is None:
            players = [PlayerFormat.FAP, PlayerFormat.AYT]

        self.dataset = dataset
        self.players = players
        self.name = name

    def clean(self) -> None:
        self.dataset.clean()

    def root(self) -> str:
        return self.dataset.root()

    def execute(self) -> None:
        self.build_files()
        self.analyse_files()

    def analyse_files(self) -> None:
        with open(f"reports/report_{self.name}.md", "w") as report:
            sizes = []
            zx0sizes = []
            formats = []
            sources = []
            max_execution_time = []
            min_execution_time = []
            mean_execution_time = []
            init_time = []
            for f in self.iter_json():
                with open(f) as json_file:
                    res = json.load(json_file)
                formats.append(
                    os.path.splitext(res["compressed_fname"])[1].replace("CHPZ80", "chp")
                )
                sizes.append(res["program_size"])
                zx0sizes.append(res["program_zx0_size"])
                sources.append(
                    os.path.splitext(os.path.basename(res["compressed_fname"]))[0]
                )
                max_execution_time.append(res["nops_exec_max"])
                min_execution_time.append(res["nops_exec_min"])
                mean_execution_time.append(res["nops_exec_mean"])
                init_time.append(res["nops_init"])

            df = pd.DataFrame.from_dict(
                {"format": formats, 
                 "prog_size": sizes, 
                 "zx0_prog_size": zx0sizes, 
                 "max_execution_time": max_execution_time,
                 "min_execution_time": min_execution_time,
                 "mean_execution_time": mean_execution_time,
                 "init_time": init_time,
                 "sources": sources
                 }
            )

            title = {
                'prog_size': "Raw program size",
                'zx0_prog_size': "Crunch (zx0) program size (without decrunch routine and data reloction)",
                'max_execution_time': "Maximum execution time (in nops)"
            }

            # Compute format ordering once
            preferred_order = [".chp", ".akm", ".akg", ".fap", ".aky", ".ayt"]
            ordered_extensions = [c for c in preferred_order if c in df["format"].unique()]
            format_palette = sns.color_palette("tab10", n_colors=len(ordered_extensions))
            format_colors = dict(zip(ordered_extensions, format_palette))

            report.write(f"---\ntitle: {self.name}\n---\n\n")
            for comparison_key in ["prog_size", "zx0_prog_size", "max_execution_time"]:


                report.write(f"# {title[comparison_key]}\n\n")

                summary: pd.DataFrame = df.pivot(index="sources", columns=["format"])[comparison_key]
                summary = summary.reset_index()
                summary.to_markdown(report)
                report.write("\n\n")

                print(summary)
                report.write("Mean\n\n")
                summary.drop("sources",axis=1).mean().to_markdown(report)
                report.write("\n\n")

      
                print(summary.columns)

                for col1, col2 in combinations(ordered_extensions, 2):
                    res = wilcoxon(summary[col1], summary[col2])

                    if res.pvalue < 0.05:
                        best = col1 if summary[col1].mean() < summary[col2].mean() else col2
                        code = f"dissimilar (best={best})"
                    else:
                        code = "similar"

                    report.write(f" - {col1} vs {col2}: {code}\n")

                # Generate plots
                self._plot_parallel_coordinates(summary, ordered_extensions, comparison_key, title[comparison_key], report)
                self._plot_boxplot(df, ordered_extensions, comparison_key, title[comparison_key], report)
                self._plot_swarmplot(df, ordered_extensions, comparison_key, title[comparison_key], report)

            self._plot_spider(df, ordered_extensions, format_colors, report)
            self._plot_scatter_tracks(df, ordered_extensions, format_colors, report)
            self._plot_scatter_median(df, ordered_extensions, format_colors, report)

    def build_files(self) -> None:
        def handle_input(input: str) -> list:
            logging.info(f'Handle "{input}" data generation')
            return [handle_input_with_player(input, player) for player in self.players]

        def handle_input_with_player(input: str, out_player: PlayerFormat) -> dict:
            logging.info(f"Generate data for {out_player}")
            input_fmt: MusicFormat = MusicFormat.get_format(input)

            expected = out_player.requires_one_of()
            convertible = input_fmt.convertible_to()

            convert_to = set(expected).intersection(convertible).pop()
            converted_fname = input.replace(
                os.path.splitext(input)[1], f".{convert_to.value}"
            )

        

            produced_fname = out_player.set_extension(converted_fname)
            json_fname = produced_fname + ".json"

            if not os.path.exists(json_fname):
                logging.info(f"{json_fname} does not exist")

                convert_music_file(input, converted_fname)

                res_conv = crunch_music_file(converted_fname, produced_fname, out_player)
                res_play = build_replay_program(res_conv, out_player)
                res_prof = profile(res_play["program_name"], out_player.load_address())

                res = res_conv | res_play | res_prof
                with open(json_fname, "w") as f:
                    json.dump(res, f)
            else:
                logging.info(f"{json_fname} already exists")
                res = json.load(open(json_fname))

            #handle the zx0 file
            return res

        return Parallel(n_jobs=-1, verbose=3)(
            delayed(handle_input)(input) for input in self.dataset
        )

    def iter_json(self) -> list:
        return self.dataset.iter_json()

    # Plotting helpers
    def _plot_parallel_coordinates(self, summary: pd.DataFrame, ordered_extensions: list[str], comparison_key: str, title: str, report) -> None:
        plot_x = list(range(len(ordered_extensions)))
        fig, ax = plt.subplots(figsize=(10, 6))
        for _, row in summary.iterrows():
            ax.plot(plot_x, [row[k] for k in ordered_extensions], c="gray", alpha=0.4)
        ax.set_xticks(plot_x)
        ax.set_xticklabels(ordered_extensions)
        ax.set_xlabel("Format")
        ax.set_ylabel(title)
        parallel_png = f"reports/{comparison_key}_parallel_coordinates_{self.name}.png"
        try:
            fig.savefig(parallel_png, dpi=100, bbox_inches='tight')
            report.write(f"\n\n![Parallel coordinates]({os.path.basename(parallel_png)})\n")
        except Exception as e:
            logging.error(f"Failed to save {parallel_png}: {e}")
        plt.close(fig)

    def _plot_boxplot(self, df: pd.DataFrame, ordered_extensions: list[str], comparison_key: str, title: str, report) -> None:
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.boxplot(data=df, x="format", y=comparison_key, ax=ax, order=ordered_extensions)
        ax.set_ylabel(title)
        boxplot_png = f"reports/{comparison_key}_boxplot_{self.name}.png"
        try:
            fig.savefig(boxplot_png, dpi=100, bbox_inches='tight')
            report.write(f"\n\n![Boxplot]({os.path.basename(boxplot_png)})\n")
        except Exception as e:
            logging.error(f"Failed to save {boxplot_png}: {e}")
        plt.close(fig)

    def _plot_swarmplot(self, df: pd.DataFrame, ordered_extensions: list[str], comparison_key: str, title: str, report) -> None:
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.swarmplot(data=df, x="format", y=comparison_key, ax=ax, order=ordered_extensions)
        ax.set_ylabel(title)
        swarmplot_png = f"reports/{comparison_key}_swarmplot_{self.name}.png"
        try:
            fig.savefig(swarmplot_png, dpi=100, bbox_inches='tight')
            report.write(f"\n\n![Swarmplot]({os.path.basename(swarmplot_png)})\n")
        except Exception as e:
            logging.error(f"Failed to save {swarmplot_png}: {e}")
        plt.close(fig)

    def _plot_spider(self, df: pd.DataFrame, ordered_extensions: list[str], format_colors: dict[str, tuple], report) -> None:
        report.write("\n\n# Spider Charts by Player Format\n\n")
        metrics = [col for col in df.columns if col not in ["format", "sources"]]
        n_formats = len(ordered_extensions)
        n_cols = min(3, n_formats)
        n_rows = (n_formats + n_cols - 1) // n_cols

        fig, axes = plt.subplots(n_rows, n_cols, figsize=(6*n_cols, 6*n_rows), subplot_kw=dict(projection='polar'))
        if n_formats == 1:
            axes = np.array([axes])
        axes = axes.flatten()

        for idx, fmt in enumerate(ordered_extensions):
            ax = axes[idx]
            format_data = df[df["format"] == fmt]
            categories = metrics
            N = len(categories)

            angles = [n / float(N) * 2 * pi for n in range(N)]
            angles += angles[:1]

            values = []
            for metric in metrics:
                metric_values = format_data[metric].values
                if len(metric_values) > 0:
                    max_val = df[metric].max()
                    min_val = df[metric].min()
                    if max_val == min_val:
                        normalized = 0.5
                    else:
                        normalized = (metric_values.mean() - min_val) / (max_val - min_val)
                    values.append(normalized)
                else:
                    values.append(0)

            values += values[:1]
            color = format_colors.get(fmt, None)
            ax.plot(angles, values, 'o-', linewidth=2, label=fmt, color=color)
            ax.fill(angles, values, alpha=0.25, color=color)
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(categories, size=8)
            ax.set_ylim(0, 1)
            ax.set_title(f"{fmt}", size=12, weight='bold', pad=20)
            ax.grid(True)

        for idx in range(n_formats, len(axes)):
            axes[idx].set_visible(False)

        plt.tight_layout()
        spider_png = f"reports/spider_charts_{self.name}.png"
        try:
            fig.savefig(spider_png, dpi=100, bbox_inches='tight')
            report.write(f"\n\n![Spider Charts by Format]({os.path.basename(spider_png)})\n")
            report.write("\nNote: In spider charts, values closer to the center (0.0) indicate better performance (lower size/time).\n")
        except Exception as e:
            logging.error(f"Failed to save {spider_png}: {e}")
        plt.close(fig)

    def _plot_scatter_tracks(self, df: pd.DataFrame, ordered_extensions: list[str], format_colors: dict[str, tuple], report) -> None:
        report.write("\n\n# Program Size vs Maximum Execution Time\n\n")
        fig, ax = plt.subplots(figsize=(10, 6))
        for source in df["sources"].unique():
            source_data = df[df["sources"] == source].sort_values("prog_size")
            ax.plot(source_data["prog_size"], source_data["max_execution_time"], color="gray", alpha=0.2, linewidth=1, zorder=1)

        for fmt in ordered_extensions:
            format_data = df[df["format"] == fmt]
            ax.scatter(
                format_data["prog_size"],
                format_data["max_execution_time"],
                label=fmt,
                s=100,
                alpha=0.6,
                zorder=2,
                color=format_colors.get(fmt)
            )

        ax.set_xlabel("Program Size (bytes)")
        ax.set_ylabel("Maximum Execution Time (nops)")
        ax.set_title("Program Size vs Maximum Execution Time by Player Format")
        ax.grid(True, alpha=0.3)

        # Add reference lines
        ax.axvline(x=16384, color='red', linestyle=':', linewidth=1.5, alpha=0.6, label='bank limitation')
        ax.axvline(x=0x8000, color='red', linestyle=':', linewidth=1.5, alpha=0.6)
        ax.axvline(x=0xC000, color='red', linestyle=':', linewidth=1.5, alpha=0.6)
        ax.axhline(y=3328, color='blue', linestyle=':', linewidth=1.5, alpha=0.6, label='1 halt')
        
        ax.legend()

        scatter_png = f"reports/scatter_prog_size_vs_exec_time_{self.name}.png"
        try:
            fig.savefig(scatter_png, dpi=100, bbox_inches='tight')
            report.write(f"\n\n![Scatter Plot]({os.path.basename(scatter_png)})\n")
        except Exception as e:
            logging.error(f"Failed to save {scatter_png}: {e}")
        plt.close(fig)

    def _plot_scatter_median(self, df: pd.DataFrame, ordered_extensions: list[str], format_colors: dict[str, tuple], report) -> None:
        report.write("\n\n# Player Formats Comparison (Median Values)\n\n")
        fig, ax = plt.subplots(figsize=(10, 6))
        player_stats = []
        for fmt in ordered_extensions:
            format_data = df[df["format"] == fmt]
            median_prog_size = format_data["prog_size"].median()
            median_exec_time = format_data["max_execution_time"].median()
            std_prog_size = format_data["prog_size"].std()
            std_exec_time = format_data["max_execution_time"].std()
            player_stats.append({
                "format": fmt,
                "prog_size": median_prog_size,
                "max_execution_time": median_exec_time,
                "std_prog_size": std_prog_size if not np.isnan(std_prog_size) else 0,
                "std_exec_time": std_exec_time if not np.isnan(std_exec_time) else 0
            })

        player_df = pd.DataFrame(player_stats)

        handles = []
        labels = []
        for _, row in player_df.iterrows():
            color = format_colors.get(row["format"], "C0")
            sc = ax.scatter(row["prog_size"], row["max_execution_time"], s=200, alpha=0.7, color=color, label=row["format"])
            handles.append(sc)
            labels.append(row["format"])

            ellipse = Ellipse(
                (row["prog_size"], row["max_execution_time"]),
                width=2*row["std_prog_size"],
                height=2*row["std_exec_time"],
                alpha=0.2,
                color=color
            )
            ax.add_patch(ellipse)
            ax.annotate(row["format"], (row["prog_size"], row["max_execution_time"]),
                        xytext=(5, 5), textcoords="offset points", fontsize=10)

        pareto_indices = compute_pareto_front(player_df, "prog_size", "max_execution_time")
        draw_pareto_front(ax, player_df, pareto_indices, "prog_size", "max_execution_time",
                         scatter_size=240, include_label=True)

        ax.set_xlabel("Median Program Size (bytes)")
        ax.set_ylabel("Median Maximum Execution Time (nops)")
        ax.set_title("Player Formats Comparison (Median Values ± 1 Std Dev)")
        ax.grid(True, alpha=0.3)
        ax.legend()

        scatter_median_png = f"reports/scatter_median_prog_size_vs_exec_time_{self.name}.png"
        try:
            fig.savefig(scatter_median_png, dpi=100, bbox_inches='tight')
            report.write(f"\n\n![Scatter Plot - Median Values]({os.path.basename(scatter_median_png)})\n")
            report.write("\nNote: Ellipses show ±1 standard deviation around median values. The dashed line represents the Pareto front (non-dominated players).\n")
        except Exception as e:
            logging.error(f"Failed to save {scatter_median_png}: {e}")
        plt.close(fig)


class ArkosTracker3Benchmark(Benchmark):
    def __init__(self):
        replay_formats = [
            PlayerFormat.FAP,
            PlayerFormat.AYT,
            PlayerFormat.AKG,
            PlayerFormat.AKY,
            PlayerFormat.AKM,
        ]
        super().__init__("AT3", At3Dataset(), replay_formats)


class ChpBenchmark(Benchmark):
    def __init__(self):
        replay_formats = [PlayerFormat.CHP, PlayerFormat.AKM]
        super().__init__("CHP", ChpDataset(), replay_formats)


class PaCiDemoBenchmark(Benchmark):
    def __init__(self):
        replay_formats = [PlayerFormat.AYT, PlayerFormat.FAP]
        super().__init__("PACIDEMO", PaCiDemoDataset(), replay_formats)