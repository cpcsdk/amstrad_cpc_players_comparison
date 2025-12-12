#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Clean replacement for benchmark.py (safe, minimal).

This file intentionally avoids heavy plotting and keeps the core orchestration
logic: sanitized temporary processing, copy-back, JSON remap, and skip-if-json-exists.

After you review and test this file, I can replace the broken `benchmark.py`
with this content or integrate parts back into the original file.
"""

import json
import os
import logging
import shutil
import tempfile
import re
from typing import List
import datetime

# plotting/data deps for richer report generation (optional at runtime)
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from math import pi
from matplotlib.ticker import FuncFormatter
from matplotlib.patches import Ellipse
from utils import compute_pareto_front, draw_pareto_front
from itertools import combinations
try:
    from scipy.stats import wilcoxon
    _have_wilcoxon = True
except Exception:
    _have_wilcoxon = False

from joblib import Parallel, delayed

from datasets import MusicFormat, convert_music_file, At3Dataset, ChpDataset, PaCiDemoDataset
from players import crunch_music_file, build_replay_program, PlayerFormat
from profile import profile


class Benchmark:
    def __init__(self, name: str, dataset, players: List[PlayerFormat]):
        self.name = name
        self.dataset = dataset
        self.players = players

    def iter_json(self) -> list:
        return self.dataset.iter_json()


    def build_files(self):
        def handle_input_with_player(original_input: str, out_player: PlayerFormat):
            logging.info(f"Processing {original_input} for {out_player}")

            input_fmt = MusicFormat.get_format(original_input)

            tmpdir = tempfile.mkdtemp(prefix="playerbench-")
            try:
                base = os.path.basename(original_input)
                safe_base = re.sub(r"[^A-Za-z0-9_.-]", "_", base)
                working_input = tmpdir + "/" + safe_base
                shutil.copyfile(original_input, working_input)
            except Exception:
                working_input = original_input

            expected = out_player.requires_one_of()
            convertible = input_fmt.convertible_to()
            convert_to = set(expected).intersection(convertible).pop()

            converted_working = working_input.rsplit('.', 1)[0] + f".{convert_to.value}"
            produced_working = out_player.set_extension(converted_working)
            json_working = produced_working + ".json"

            converted_target = original_input.rsplit('.', 1)[0] + f".{convert_to.value}"
            produced_target = out_player.set_extension(converted_target)
            json_target = produced_target + ".json"

            # Prefer dataset-local JSON if present
            if os.path.exists(json_target):
                try:
                    return json.load(open(json_target))
                except Exception:
                    logging.exception("Failed reading dataset JSON; will rebuild")

            if os.path.exists(json_working):
                try:
                    return json.load(open(json_working))
                except Exception:
                    logging.exception("Failed reading working JSON; will rebuild")

            # Convert, crunch, build, profile
            convert_music_file(working_input, converted_working)
            res_conv = crunch_music_file(converted_working, produced_working, out_player)

            try:
                res_play = build_replay_program(res_conv, out_player)
            except Exception:
                logging.exception("build_replay_program failed")
                res_play = {}

            try:
                program_name = res_play.get("program_name")
                if program_name:
                    res_prof = profile(program_name, out_player.load_address())
                else:
                    res_prof = {}
            except Exception:
                logging.exception("profile failed")
                res_prof = {}

            result = {**res_conv, **res_play, **res_prof}

            # Copy back produced artifacts and write dataset-local JSON
            try:
                if converted_working != converted_target and os.path.exists(converted_working):
                    shutil.copyfile(converted_working, converted_target)

                import glob
                tmp_base = converted_working.rsplit('.', 1)[0]
                target_base = converted_target.rsplit('.', 1)[0]
                for f in glob.glob(tmp_base + "*"):
                    if f == converted_working:
                        continue
                    try:
                        suffix = f[len(tmp_base):]
                        shutil.copyfile(f, target_base + suffix)
                    except Exception:
                        logging.exception(f"Failed copying produced file {f}")

                for k, v in list(result.items()):
                    if isinstance(v, str) and tmp_base in v:
                        result[k] = v.replace(tmp_base, target_base)

                with open(json_target, "w") as fh:
                    json.dump(result, fh)
                return result
            finally:
                try:
                    shutil.rmtree(tmpdir)
                except Exception:
                    pass

        tasks = []
        for inp in self.dataset:
            for p in self.players:
                tasks.append((inp, p))

        def _run(task):
            inp, p = task
            return handle_input_with_player(inp, p)

        return Parallel(n_jobs=-1)(delayed(_run)(t) for t in tasks)

    def execute(self):
        """Run the benchmark: build files and return results."""
        logging.info(f"Starting benchmark {self.name}")
        results = self.build_files()
        logging.info(f"Finished benchmark {self.name}: processed {len(results)} tasks")
        try:
            # Prefer the richer analysis/report pipeline from the working backup
            self.analyse_files()
        except Exception:
            logging.exception("Failed to generate rich report; falling back to simple generate_report")
            try:
                self.generate_report(results)
            except Exception:
                logging.exception("generate_report fallback also failed")
        return results

    def analyse_files(self) -> None:
        """Analyse existing JSON results and produce the full markdown report and plots.

        This method is adapted from the working backup `benchmark.py` and expects
        JSON files produced next to dataset inputs. It reads `self.iter_json()`
        to find json result files.
        """
        out_dir = os.path.join(os.getcwd(), "reports")
        os.makedirs(out_dir, exist_ok=True)
        fname = os.path.join(out_dir, f"report_{self.name}.md")

        with open(fname, "w") as report:
            sizes = []
            zx0sizes = []
            formats = []
            sources = []
            max_execution_time = []
            min_execution_time = []
            mean_execution_time = []
            init_time = []

            for f in self.iter_json():
                try:
                    with open(f) as json_file:
                        res = json.load(json_file)
                except Exception:
                    logging.exception(f"Failed reading JSON {f}; skipping")
                    continue

                # derive format from compressed filename extension (best-effort)
                try:
                    raw_fmt = os.path.splitext(res.get("compressed_fname", ""))[1]
                    raw_fmt = raw_fmt.replace("CHPZ80", "chp")
                except Exception:
                    raw_fmt = ""

                # Normalize format to canonical PlayerFormat.name (e.g. 'FAP', 'AKG')
                try:
                    pf = PlayerFormat.get_format(raw_fmt)
                    fmt = pf.name
                except Exception:
                    # Fallback: uppercase and strip leading dot
                    fmt = str(raw_fmt).upper().lstrip('.')

                formats.append(fmt)
                sizes.append(res.get("program_size", 0))
                zx0sizes.append(res.get("program_zx0_size", 0))
                sources.append(os.path.splitext(os.path.basename(res.get("compressed_fname", "")))[0])
                max_execution_time.append(res.get("nops_exec_max", 0))
                min_execution_time.append(res.get("nops_exec_min", 0))
                mean_execution_time.append(res.get("nops_exec_mean", 0))
                init_time.append(res.get("nops_init", 0))

            df = pd.DataFrame.from_dict({
                "format": formats,
                "prog_size": sizes,
                "zx0_prog_size": zx0sizes,
                "max_execution_time": max_execution_time,
                "min_execution_time": min_execution_time,
                "mean_execution_time": mean_execution_time,
                "init_time": init_time,
                "sources": sources,
            })

            # remove AKM
            df = df[ df["format"] != "AKM"]

            title = {
                'prog_size': "Raw program size",
                'zx0_prog_size': "Crunch (zx0) program size (without decrunch routine and data reloction)",
                'max_execution_time': "Maximum execution time (in nops)"
            }

            # Canonical ordering: prefer the order of players configured for this benchmark
            preferred_order = ["CHP", "AKM", "AKG", "FAP", "AYT", "AKYS", "AKYU"]
            # Keep only formats present in the dataframe (preserve player order)
            ordered_extensions = [c for c in preferred_order if c in df["format"].unique()]
            format_palette = sns.color_palette("tab10", n_colors=max(1, len(ordered_extensions)))
            format_colors = dict(zip(ordered_extensions, format_palette))

            report.write(f"---\ntitle: {self.name}\n---\n\n")

            for comparison_key in ["prog_size", "zx0_prog_size", "max_execution_time"]:
                report.write(f"# {title[comparison_key]}\n\n")

                # pivot per-source x format
                try:
                    summary: pd.DataFrame = df.pivot(index="sources", columns=["format"])[comparison_key]
                except Exception:
                    # fallback: try pivot_table with median
                    summary = df.pivot_table(index="sources", columns=["format"], values=comparison_key, aggfunc='median')

                summary = summary.reset_index()
                summary.to_markdown(report)
                report.write("\n\n")

                report.write("Mean\n\n")
                try:
                    summary.drop("sources", axis=1).mean().to_markdown(report)
                except Exception:
                    pass
                report.write("\n\n")

                # pairwise statistical tests (Wilcoxon) if available
                if _have_wilcoxon and len(ordered_extensions) >= 2:
                    for col1, col2 in combinations(ordered_extensions, 2):
                        try:
                            res = wilcoxon(summary[col1], summary[col2])
                            if res.pvalue < 0.05:
                                best = col1 if summary[col1].mean() < summary[col2].mean() else col2
                                code = f"dissimilar (best={best})"
                            else:
                                code = "similar"
                        except Exception:
                            code = "test_failed"
                        report.write(f" - {col1} vs {col2}: {code}\n")

                # Generate plots
                try:
                    # ensure summary columns include ordered_extensions (fill missing with 0)
                    for ext in ordered_extensions:
                        if ext not in summary.columns:
                            summary[ext] = 0
                    self._plot_parallel_coordinates(summary, ordered_extensions, comparison_key, title[comparison_key], report)
                except Exception:
                    logging.exception("_plot_parallel_coordinates failed")

                try:
                    present_formats = [f for f in ordered_extensions if f in df['format'].unique()]
                    if present_formats:
                        self._plot_boxplot(df, present_formats, comparison_key, title[comparison_key], format_colors, report)
                    else:
                        logging.info("No formats present for boxplot; skipping")
                except Exception:
                    logging.exception("_plot_boxplot failed")

                try:
                    present_formats = [f for f in ordered_extensions if f in df['format'].unique()]
                    if present_formats:
                        self._plot_swarmplot(df, present_formats, comparison_key, title[comparison_key], format_colors, report)
                    else:
                        logging.info("No formats present for swarmplot; skipping")
                except Exception:
                    logging.exception("_plot_swarmplot failed")

            # global comparison plots
            try:
                self._plot_spider(df, ordered_extensions, format_colors, report)
            except Exception:
                logging.exception("_plot_spider failed")

            try:
                self._plot_scatter_tracks(df, ordered_extensions, format_colors, report)
            except Exception:
                logging.exception("_plot_scatter_tracks failed")

            try:
                self._plot_scatter_median(df, ordered_extensions, format_colors, report)
            except Exception:
                logging.exception("_plot_scatter_median failed")

            logging.info(f"Wrote report to {fname}")


    def _plot_spider(self, df: pd.DataFrame, ordered_extensions: list, format_colors: dict, report) -> None:
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
        except Exception:
            logging.exception(f"Failed to save {spider_png}")
        plt.close(fig)

    def _plot_scatter_tracks(self, df: pd.DataFrame, ordered_extensions: list, format_colors: dict, report) -> None:
        report.write("\n\n# Program Size vs Maximum Execution Time\n\n")
        fig, ax = plt.subplots(figsize=(10, 6))
        for source in df["sources"].unique():
            source_data = df[df["sources"] == source].sort_values("prog_size")
            ax.plot(source_data["prog_size"], source_data["max_execution_time"], color="gray", alpha=0.2, linewidth=1, zorder=1)

        for fmt in ordered_extensions:
            format_data = df[df["format"] == fmt]
            # Use square marker for stable players, circle for others
            player_format = PlayerFormat.get_format(fmt)
            marker = 's' if player_format.is_stable() else 'o'
            
            ax.scatter(
                format_data["prog_size"],
                format_data["max_execution_time"],
                label=fmt,
                s=40,
                alpha=0.6,
                zorder=2,
                color=format_colors.get(fmt),
                marker=marker
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
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
        
        # Format x-axis as hexadecimal
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"0x{int(x):04X} ({int(x)})"))

        scatter_png = f"reports/scatter_prog_size_vs_exec_time_{self.name}.png"
        try:
            fig.savefig(scatter_png, dpi=100, bbox_inches='tight')
            report.write(f"\n\n![Scatter Plot]({os.path.basename(scatter_png)})\n")
        except Exception as e:
            logging.error(f"Failed to save {scatter_png}: {e}")
        plt.close(fig)

    def _plot_scatter_median(self, df: pd.DataFrame, ordered_extensions: list, format_colors: dict, report) -> None:
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
            # Use square marker for stable players, circle for others
            player_format = PlayerFormat.get_format(row["format"])
            marker = 's' if player_format.is_stable() else 'o'
            
            sc = ax.scatter(row["prog_size"], row["max_execution_time"], s=100, alpha=0.7, color=color, marker=marker, label=row["format"])
            handles.append(sc)
            labels.append(row["format"])

            width = 2 * row["std_prog_size"]
            height = 2 * row["std_exec_time"]
            patch = Ellipse(
                (row["prog_size"], row["max_execution_time"]),
                width=width,
                height=height,
                alpha=0.2,
                color=color
            )

            ax.add_patch(patch)
            ax.annotate(row["format"], (row["prog_size"], row["max_execution_time"]),
                        xytext=(5, 5), textcoords="offset points", fontsize=10)

        pareto_indices = compute_pareto_front(player_df, "prog_size", "max_execution_time")
        draw_pareto_front(ax, player_df, pareto_indices, "prog_size", "max_execution_time",
                 scatter_size=120, include_label=True)

        ax.set_xlabel("Median Program Size (bytes)")
        ax.set_ylabel("Median Maximum Execution Time (nops)")
        ax.set_title("Player Formats Comparison (Median Values ± 1 Std Dev)")
        ax.grid(True, alpha=0.3)
        ax.legend()
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
        
        # Format x-axis as hexadecimal
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"0x{int(x):04X} ({int(x)})"))

        scatter_median_png = f"reports/scatter_median_prog_size_vs_exec_time_{self.name}.png"
        try:
            fig.savefig(scatter_median_png, dpi=100, bbox_inches='tight')
            report.write(f"\n\n![Scatter Plot - Median Values]({os.path.basename(scatter_median_png)})\n")
            report.write("\nNote: Shaded regions show ±1 standard deviation (ellipse for circle markers, square for stable players). The dashed line represents the Pareto front (non-dominated players).\n")
        except Exception as e:
            logging.error(f"Failed to save {scatter_median_png}: {e}")
        plt.close(fig)

    def _plot_parallel_coordinates(self, summary: pd.DataFrame, ordered_extensions: list, comparison_key: str, title: str, report) -> None:
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

    def _plot_boxplot(self, df: pd.DataFrame, ordered_extensions: list, comparison_key: str, title: str, format_colors: dict = None, report=None) -> None:
        fig, ax = plt.subplots(figsize=(10, 6))
        # Build palette mapping for ordered_extensions
        palette = None
        if format_colors is not None:
            palette = {fmt: format_colors.get(fmt) for fmt in ordered_extensions}

        # Use hue='format' with dodge=False to apply explicit palette without deprecation warning
        sns.boxplot(data=df, x="format", y=comparison_key, hue="format", dodge=False,
                    ax=ax, order=ordered_extensions, palette=palette)
        # remove redundant legend created by hue
        lg = ax.get_legend()
        if lg:
            lg.remove()
        ax.set_ylabel(title)
        boxplot_png = f"reports/{comparison_key}_boxplot_{self.name}.png"
        try:
            fig.savefig(boxplot_png, dpi=100, bbox_inches='tight')
            if report is not None:
                report.write(f"\n\n![Boxplot]({os.path.basename(boxplot_png)})\n")
        except Exception as e:
            logging.error(f"Failed to save {boxplot_png}: {e}")
        plt.close(fig)

    def _plot_swarmplot(self, df: pd.DataFrame, ordered_extensions: list, comparison_key: str, title: str, format_colors: dict = None, report=None) -> None:
        fig, ax = plt.subplots(figsize=(10, 6))
        # Build palette mapping for ordered_extensions
        palette = None
        if format_colors is not None:
            palette = {fmt: format_colors.get(fmt) for fmt in ordered_extensions}

        # Use violinplot to show distribution and avoid point-overlap issues
        # Use density_norm='width' (future-proof replacement for scale='width')
        sns.violinplot(data=df, x="format", y=comparison_key, hue="format", dodge=False,
                       ax=ax, order=ordered_extensions, cut=0, inner="quartile",
                       density_norm='width', linewidth=0.6, palette=palette)
        # remove redundant legend created by hue
        lg = ax.get_legend()
        if lg:
            lg.remove()
        ax.set_ylabel(title)
        violin_png = f"reports/{comparison_key}_violin_{self.name}.png"
        try:
            fig.savefig(violin_png, dpi=100, bbox_inches='tight')
            if report is not None:
                report.write(f"\n\n![Violin Plot]({os.path.basename(violin_png)})\n")
        except Exception as e:
            logging.error(f"Failed to save {violin_png}: {e}")
        plt.close(fig)

    def clean(self):
        """Remove produced artifacts (but keep original input files)."""
        logging.info(f"Cleaning artifacts for benchmark {self.name}")
        import glob

        removed = 0
        for inp in self.dataset:
            base = inp.rsplit('.', 1)[0]
            for f in glob.glob(base + "*"):
                # never delete the original input file
                if f == inp:
                    continue
                try:
                    os.remove(f)
                    removed += 1
                except Exception:
                    logging.exception(f"Failed to remove {f}")

        logging.info(f"Removed {removed} produced files for {self.name}")


class ArkosTracker3Benchmark(Benchmark):
    def __init__(self):
        replay_formats = [
            PlayerFormat.FAP,
            PlayerFormat.AYT,
            PlayerFormat.AKG,
            PlayerFormat.AKYS,
            PlayerFormat.AKYU,
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
