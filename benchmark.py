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
from utils import compute_pareto_front, draw_pareto_front, safe_read_json, safe_write_json, safe_rmtree
import plots
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
        # runtime options (can be set by caller)
        self.no_report = False
        self.no_profile = False
        self.outdir = None
        self.jobs = -1
        self.generate_html = False

    def iter_json(self) -> list:
        return self.dataset.iter_json()


    def build_files(self):
        def handle_input_with_player(original_input: str, out_player: PlayerFormat):
            # Wrap entire processing so any unexpected error becomes an
            # explictly-returned result with an `error` field instead of
            # crashing the entire Parallel pool.
            try:
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
                    res = safe_read_json(json_target)
                    if res is not None:
                        return res
                    else:
                        logging.info("Failed reading dataset JSON; will rebuild")

                if os.path.exists(json_working):
                    res = safe_read_json(json_working)
                    if res is not None:
                        return res
                    else:
                        logging.info("Failed reading working JSON; will rebuild")

                # Convert, crunch, build, profile
                convert_music_file(working_input, converted_working)
                res_conv = crunch_music_file(converted_working, produced_working, out_player)

                try:
                    res_play = build_replay_program(res_conv, out_player)
                except Exception:
                    logging.exception("build_replay_program failed")
                    res_play = {}

                res_prof = {}
                try:
                    program_name = res_play.get("program_name")
                    if program_name and not getattr(self, 'no_profile', False):
                        res_prof = profile(program_name, out_player.load_address())
                except Exception:
                    logging.exception("profile failed")

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

                    # Normalize and annotate player format in JSON so downstream
                    # report generation can rely on a canonical field.
                    try:
                        comp = result.get("compressed_fname", "")
                        if comp:
                            try:
                                result["player_format"] = PlayerFormat.get_format(comp).name
                            except Exception:
                                # keep original if we cannot canonicalize
                                result["player_format"] = None
                    except Exception:
                        pass

                    safe_write_json(json_target, result)
                    return result
                finally:
                    safe_rmtree(tmpdir)
            except Exception as e:
                logging.exception(f"Unexpected error processing {original_input} for {out_player}")
                return {
                    "original_input": original_input,
                    "player": str(out_player),
                    "error": str(e),
                }

        tasks = []
        for inp in self.dataset:
            for p in self.players:
                tasks.append((inp, p))

        def _run(task):
            inp, p = task
            return handle_input_with_player(inp, p)

        # Allow caller to tune job count via `self.jobs` (default -1 = all cores)
        n_jobs = getattr(self, 'jobs', -1)
        return Parallel(n_jobs=n_jobs)(delayed(_run)(t) for t in tasks)

    def execute(self):
        """Run the benchmark: build files and return results."""
        logging.info(f"Starting benchmark {self.name}")
        results = self.build_files()
        logging.info(f"Finished benchmark {self.name}: processed {len(results)} tasks")
        # If caller requested to skip plot generation, avoid running the
        # heavier `analyse_files()` pipeline which produces plots and images.
        if getattr(self, 'no_report', False):
            logging.info("no_report: skipping rich analysis; returning JSON-only results")
            # JSONs are produced by `build_files()`; when `no_report` is set we
            # intentionally avoid generating any reports or plots. Return the
            # collected results so callers can inspect or persist them.
            return results

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

        # If requested to skip reports, bail out early to avoid creating figures
        # and consuming plotting resources. The caller (execute) should
        # generate a minimal report instead.
        if getattr(self, 'no_report', False):
            logging.info("no_report is True; analyse_files() will skip report generation")
            return

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
                res = safe_read_json(f)
                if res is None:
                    # safe_read_json already logged the issue
                    continue

                # Determine canonical format: prefer explicit `player_format` written
                # alongside JSONs by `build_files()`. Fall back to deriving from
                # the `compressed_fname` extension.
                try:
                    if res.get("player_format"):
                        fmt = res.get("player_format")
                    else:
                        raw_fmt = os.path.splitext(res.get("compressed_fname", ""))[1]
                        raw_fmt = raw_fmt.replace("CHPZ80", "CHPB")
                        try:
                            pf = PlayerFormat.get_format(raw_fmt)
                            fmt = pf.name
                        except Exception:
                            fmt = str(raw_fmt).upper().lstrip('.')
                except Exception:
                    fmt = ""

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
            if False:
                df = df[ df["format"] != "AKM"]

            title = {
                'prog_size': "Raw program size",
                'zx0_prog_size': "Crunch (zx0) program size (without decrunch routine and data reloction)",
                'max_execution_time': "Maximum execution time (in nops)"
            }

            # Prepare canonical ordering and color mapping for plots
            ordered_extensions, format_colors = plots.prepare_format_colors(self, df)

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
                    plots.plot_parallel_coordinates(self, summary, ordered_extensions, comparison_key, title[comparison_key], report)
                except Exception:
                    logging.exception("_plot_parallel_coordinates failed")

                try:
                    present_formats = [f for f in ordered_extensions if f in df['format'].unique()]
                    if present_formats:
                        plots.plot_boxplot(self, df, present_formats, comparison_key, title[comparison_key], format_colors, report)
                    else:
                        logging.info("No formats present for boxplot; skipping")
                except Exception:
                    logging.exception("_plot_boxplot failed")

                try:
                    present_formats = [f for f in ordered_extensions if f in df['format'].unique()]
                    if present_formats:
                        plots.plot_violin(self, df, present_formats, comparison_key, title[comparison_key], format_colors, report)
                    else:
                        logging.info("No formats present for swarmplot; skipping")
                except Exception:
                    logging.exception("_plot_swarmplot failed")

            # global comparison plots
            try:
                plots.plot_spider(self, df, ordered_extensions, format_colors, report)
            except Exception:
                logging.exception("plot_spider failed")

            try:
                plots.plot_scatter_tracks(self, df, ordered_extensions, format_colors, report)
            except Exception:
                logging.exception("plot_scatter_tracks failed")

            try:
                plots.plot_scatter_median(self, df, ordered_extensions, format_colors, report)
            except Exception:
                logging.exception("plot_scatter_median failed")

            logging.info(f"Wrote report to {fname}")


    def _plot_spider(self, df: pd.DataFrame, ordered_extensions: list, format_colors: dict, report) -> None:
        # removed: use plots.plot_spider(...) directly from `analyse_files()`
        raise RuntimeError("_plot_spider is removed; call plots.plot_spider directly")

    def _plot_scatter_tracks(self, df: pd.DataFrame, ordered_extensions: list, format_colors: dict, report) -> None:
        raise RuntimeError("_plot_scatter_tracks is removed; call plots.plot_scatter_tracks directly")

    def _plot_scatter_median(self, df: pd.DataFrame, ordered_extensions: list, format_colors: dict, report) -> None:
        raise RuntimeError("_plot_scatter_median is removed; call plots.plot_scatter_median directly")

    def _plot_parallel_coordinates(self, summary: pd.DataFrame, ordered_extensions: list, comparison_key: str, title: str, report) -> None:
        raise RuntimeError("_plot_parallel_coordinates is removed; call plots.plot_parallel_coordinates directly")

    def _plot_boxplot(self, df: pd.DataFrame, ordered_extensions: list, comparison_key: str, title: str, format_colors: dict = None, report=None) -> None:
        raise RuntimeError("_plot_boxplot is removed; call plots.plot_boxplot directly")

    def _plot_swarmplot(self, df: pd.DataFrame, ordered_extensions: list, comparison_key: str, title: str, format_colors: dict = None, report=None) -> None:
        raise RuntimeError("_plot_swarmplot is removed; call plots.plot_violin directly")

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
        replay_formats = [PlayerFormat.CHPB, PlayerFormat.AKM, PlayerFormat.AYT, PlayerFormat.FAP, PlayerFormat.MINYQ]
        super().__init__("CHP", ChpDataset(), replay_formats)


class PaCiDemoBenchmark(Benchmark):
    def __init__(self):
        replay_formats = [PlayerFormat.AYT, PlayerFormat.FAP]
        super().__init__("PACIDEMO", PaCiDemoDataset(), replay_formats)
