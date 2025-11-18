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
import glob
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt 

from datasets import *
from players import *

class Benchmark:
    def __init__(self, dataset: Dataset, players: None):
        if players is None:
            players = [PlayerFormat.FAP, PlayerFormat.AYT]

        self.dataset = dataset
        self.players = players


    def clean(self):
        self.dataset.clean()

    def root(self):
        return self.dataset.root()
        
    def execute(self):
        self.build_files() #deactivated temporarily
        self.analyse_files()


    def analyse_files(self):
        sizes = []
        formats = []
        sources = []
        for f in self.iter_json():
            res = json.load(open(f))
            formats.append(os.path.splitext(res["compressed_fname"])[1].replace("CHPZ80", "chp"))
            sizes.append(res["program_size"])
            sources.append(os.path.splitext(os.path.basename(res["compressed_fname"]))[0])
            print(f)
        
        df = pd.DataFrame.from_dict({
            "format": formats,
            "prog_size": sizes,
            "sources": sources
        })



        print(df)
        print(df.pivot(index="sources", columns=["format"]))
        summary = df.pivot(index="sources", columns=["format"])["prog_size"].reset_index()

        ordered_extensions = [".chp", ".akm", ".fap", ".aky", ".ayt"]
        print(summary.columns)
        ordered_extensions = [_ for _ in ordered_extensions if _ in summary.columns]
        
        plot_x = list(range(len(ordered_extensions)))

        for row in summary.iterrows():

            row = row[1]
            print(row)
            plt.plot(
                plot_x,
                [row[k] for k in ordered_extensions],
                c="gray",
                alpha=0.4
            )



        sns.boxplot(df, x="format", y="prog_size")
        plt.figure()
        sns.swarmplot(df, x="format", y="prog_size")
        plt.figure()


        plt.xticks(
            [0, 1, 2, 3],
            ["AKM", "FAP", "AKY", "AYT"]
        )
        plt.xlabel("Format")
        plt.ylabel("Program size")

        plt.show()

        print(summary.to_markdown())


            

    def build_files(self):
        def handle_input(input):
            logging.info(f"Handle \"{input}\" data generation")
            return [handle_input_with_player(input, player) for player in self.players]

        def handle_input_with_player(input, out_player: PlayerFormat):
            logging.info(f"Generate data for {out_player}")
            input_fmt: MusicFormat = MusicFormat.get_format(input)
            
            expected = out_player.requires_one_of()
            convertible = input_fmt.convertible_to()

            convert_to = set(expected).intersection(convertible).pop()
            converted_fname = input.replace(os.path.splitext(input)[1], f".{convert_to.value}")



            produced_fname = out_player.set_extension(converted_fname)
            json_fname = produced_fname + ".json"
            
            if not os.path.exists(json_fname):
                logging.info(f"{json_fname} does not exist")

                convert_music_file(input, converted_fname)

                resc = crunch_music_file(converted_fname, produced_fname, out_player)
                resp = build_replay_program(resc, out_player)

                res = resc | resp
                with open(json_fname, "w") as f:
                    json.dump(res, f)
            else:
                logging.info(f"{json_fname} already exists")

        return [handle_input(input) for input in self.dataset]


    def iter_json(self):
        return self.dataset.iter_json()

class ArkosTracker3Benchmark(Benchmark):
    def __init__(self):
        replay_formats = [PlayerFormat.FAP, PlayerFormat.AYT, PlayerFormat.AKY, PlayerFormat.AKM]
        super().__init__(
            At3Dataset(), 
            replay_formats
        )


class ChpBenchmark(Benchmark):
    def __init__(self):
        replay_formats = [PlayerFormat.CHP,  PlayerFormat.AKM]
        super().__init__(
            ChpDataset(),
            replay_formats
        )