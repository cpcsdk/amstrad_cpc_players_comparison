#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# Filename: player_bench.py
# License: MIT License
# Author: Krusty/Benediction
# Date: 2025-11-11
# Version: 0.1
# Description: This file launch the current benchmark


import logging
import benchmark
import argparse
import sys


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        prog=sys.argv[0], description="Benchmark launcher for Amstrad CPC players"
    )

    parser.add_argument(
        "--benchmark", action="append", default=[], choices=["AT3", "CHP", "PACIDEMO"]
    )
    parser.add_argument("--clean", action="store_true")


    args = parser.parse_args()

    benchs = []
    if not args.benchmark or "AT3" in args.benchmark:
        benchs.append(benchmark.ArkosTracker3Benchmark())

    if "CHP" in args.benchmark:
        benchs.append(benchmark.ChpBenchmark())

    if "PACIDEMO" in args.benchmark:
        benchs.append(benchmark.PaCiDemoBenchmark())

    for bench in benchs:
        if args.clean:
            bench.clean()
        else:
            bench.execute()
