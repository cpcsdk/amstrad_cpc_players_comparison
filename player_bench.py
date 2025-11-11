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




if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    bench = benchmark.ArkosTracker3Benchmark()
    bench.execute()