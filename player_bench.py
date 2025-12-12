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
    #logging.basicConfig(level=logging.ERROR)

    parser = argparse.ArgumentParser(
        prog=sys.argv[0], description="Benchmark launcher for Amstrad CPC players"
    )

    # accept both --benchmark and the shorter --bench for convenience/compatibility
    parser.add_argument(
        "--benchmark", "--bench", action="append", default=[], choices=["AT3", "CHP", "PACIDEMO"]
    )
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--no-report", action="store_true", help="Skip report/plot generation and only produce JSON results")
    parser.add_argument("--no-profile", action="store_true", help="Skip profiling step (Z80Profiler) during build")
    parser.add_argument("--outdir", type=str, default=None, help="Output directory for reports and artifacts")
    parser.add_argument("--jobs", type=int, default=-1, help="Number of parallel jobs for building (-1 = all cores)")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity (use -v or -vv for more log output)")


    args = parser.parse_args()

    benchs = []
    if not args.benchmark or "AT3" in args.benchmark:
        benchs.append(benchmark.ArkosTracker3Benchmark())

    if "CHP" in args.benchmark:
        benchs.append(benchmark.ChpBenchmark())

    if "PACIDEMO" in args.benchmark:
        benchs.append(benchmark.PaCiDemoBenchmark())

    for bench in benchs:
        # Apply runtime flags to the Benchmark instance
        bench.no_report = bool(args.no_report)
        bench.no_profile = bool(args.no_profile)
        bench.jobs = int(args.jobs) if args.jobs is not None else -1
        if args.outdir:
            bench.outdir = args.outdir

        # Adjust logging level based on verbosity
        if args.verbose >= 1:
            logging.getLogger().setLevel(logging.DEBUG)
        else:
            logging.getLogger().setLevel(logging.INFO)

        if args.clean:
            bench.clean()
        else:
            bench.execute()
