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
from joblib import delayed, Parallel
from scipy.stats import wilcoxon

from datasets import *
from players import *
from profile import *

class Benchmark:
    def __init__(self, name, dataset: Dataset, players: None):
        if players is None:
            players = [PlayerFormat.FAP, PlayerFormat.AYT]

        self.dataset = dataset
        self.players = players
        self.name = name

    def clean(self):
        self.dataset.clean()

    def root(self):
        return self.dataset.root()

    def execute(self):
        self.build_files()  # deactivated temporarily
        self.analyse_files()

    def analyse_files(self):
        with open(f"reports/report_{self.name}.md", "w") as report:
            sizes = []
            zx0sizes = []
            formats = []
            sources = []
            max_execution_time = []
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

            df = pd.DataFrame.from_dict(
                {"format": formats, 
                 "prog_size": sizes, 
                 "zx0_prog_size": zx0sizes, 
                 "max_execution_time": max_execution_time,
                 "sources": sources
                 }
            )

            title = {
                'prog_size': "Raw program size",
                'zx0_prog_size': "Crunch (zx0) program size (without decrunch routine and data reloction)",
                'max_execution_time': "Maximum execution time (in nops)"
            }

            report.write(f"---\ntitle: {self.name}\n---\n\n")
            for comparison_key in ["prog_size", "zx0_prog_size", "max_execution_time"]:


                report.write(f"# {title[comparison_key]}\n\n")

                summary = df.pivot(index="sources", columns=["format"])[comparison_key]
                summary = summary.reset_index()
                summary.to_markdown(report)
                report.write("\n\n")

                print(summary)
                report.write("Mean\n\n")
                summary.drop("sources",axis=1).mean().to_markdown(report)
                report.write("\n\n")

      

                ordered_extensions = [".chp", ".akm", ".fap", ".aky", ".ayt"]
                print(summary.columns)
                ordered_extensions = [_ for _ in ordered_extensions if _ in summary.columns]

                for i in range(len(ordered_extensions)):
                    col1 = ordered_extensions[i]
                    for j in range (i+1, len(ordered_extensions)):
                        col2 = ordered_extensions[j]
                        res = wilcoxon(summary[col1], summary[col2])

                        if res.pvalue < 0.05:
                            if summary[col1].mean() < summary[col2].mean():
                                best = col1
                            else:
                                best = col2
                            code = f"dissimilar (best={best})"
                        else:
                            code = "similar"

                        report.write(f" - {col1} vs {col2}: {code}\n")


                plot_x = list(range(len(ordered_extensions)))

                def generate_axis():
                    plt.xticks(plot_x, ordered_extensions)
                    plt.xlabel("Format")
                    plt.ylabel("Program size")

                plt.clf()
                for row in summary.iterrows():
                    row = row[1]
                    plt.plot(plot_x, [row[k] for k in ordered_extensions], c="gray", alpha=0.4)
                generate_axis()
                parallal_png = f"reports/{comparison_key}_parallal_coordinates_{self.name}.png"
                plt.savefig(parallal_png)
                report.write(f"\n\n![Parallal coordinates]({os.path.basename(parallal_png)})\n")

                plt.clf()
                sns.boxplot(df, x="format", y=comparison_key)
                boxplot_png = f"reports/{comparison_key}_boxplot_{self.name}.png"
                # generate_axis()
                plt.savefig(boxplot_png)
                report.write(f"\n\n![Boxplot]({os.path.basename(boxplot_png)})\n")

                plt.clf()
                sns.swarmplot(df, x="format", y=comparison_key)
                #  generate_axis()
                swarmplot_png = f"reports/{comparison_key}_swarmlot_{self.name}.png"
                plt.savefig(swarmplot_png)
                report.write(f"\n\n![Swarmplot]({os.path.basename(swarmplot_png)})\n")

    def build_files(self):
        def handle_input(input):
            logging.info(f'Handle "{input}" data generation')
            return [handle_input_with_player(input, player) for player in self.players]

        def handle_input_with_player(input, out_player: PlayerFormat):
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


        return Parallel(n_jobs=1, verbose=3)(
            delayed(handle_input)(input) for input in self.dataset
        )

    def iter_json(self):
        return self.dataset.iter_json()


class ArkosTracker3Benchmark(Benchmark):
    def __init__(self):
        replay_formats = [
            PlayerFormat.FAP,
            PlayerFormat.AYT,
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