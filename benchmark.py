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
        
    def execute(self):
        self.build_files() #deactivated temporarily
        self.analyse_files()


    def analyse_files(self):
        sizes = []
        formats = []
        sources = []
        for f in glob.glob(os.path.join(self.dataset.path, "*/*.json")):
            res = json.load(open(f))
            formats.append(os.path.splitext(res["compressed_fname"])[1])
            sizes.append(res["program_size"])
            sources.append(os.path.splitext(os.path.basename(res["compressed_fname"]))[0])

        
        df = pd.DataFrame.from_dict({
            "format": formats,
            "prog_size": sizes,
            "sources": sources
        })


        sns.boxplot(df, x="format", y="prog_size")
        plt.figure()
        sns.swarmplot(df, x="format", y="prog_size")
        plt.figure()

        summary = df.pivot(index="sources", columns=["format"])["prog_size"].reset_index()
        print(summary)
        for row in summary.iterrows():
            row = row[1]
            plt.plot(
                [0,1,2,3],
                [row[".akm"], row[".fap"], row[".aky"], row[".ayt"]],
                c="gray",
                alpha=0.4
            )
        plt.xticks(
            [0, 1, 2, 3],
            ["AKM", "FAP", "AKY", "AYT"]
        )
        plt.xlabel("Format")
        plt.ylabel("Program size")

        plt.show()

            

    def build_files(self):
        def handle_input(input):
            logging.info(f"Handle \"{input}\" data generation")
            return [handle_input_player(input, player) for player in self.players]

        def handle_input_player(input, out_player: PlayerFormat):
            logging.info(f"Generate data for {out_player}")
            input_fmt: MusicFormat = MusicFormat.get_format(input)
            
            expected = out_player.requires_one_of()
            convertible = input_fmt.convertible_to()

            print("expected", expected)
            print("convertibe", convertible)

            convert_to = set(expected).intersection(convertible).pop()
            converted_fname = input.replace(f".{input_fmt.value}", f".{convert_to.value}")
            convert_music_file(input, converted_fname)
            
            resc = crunch_music_file(converted_fname, out_player)
            json_fname = "_".join(os.path.splitext(resc["compressed_fname"])) + ".json"

            if os.path.exists(json_fname):
                resp = build_replay_program(resc, out_player)

                res = resc | resp
                with open(json_fname, "w") as f:
                    json.dump(res, f)

        return [handle_input(input) for input in self.dataset]

class ArkosTracker3Benchmark(Benchmark):
    def __init__(self):
        replay_formats = [PlayerFormat.FAP, PlayerFormat.AYT, PlayerFormat.AKY, PlayerFormat.AKM]
        super().__init__(
            At3Dataset(), 
            replay_formats
        )
