from utils import *
from utils import build_bndbuild_tokens
import os
import pandas as pd
import platform

def profile(amsdos_fname, load_address):
    """
    Profile a replay routine by executing it 10000 times
    """
    assert os.path.exists(amsdos_fname), f"File {amsdos_fname} does not exist"

    csv_fname = os.path.splitext(amsdos_fname)[0] + ".CSV"
    
    # Build argv tokens and let `execute_process` run them (no shell).
    tokens = build_bndbuild_tokens(
        "bndbuild",
        "--direct",
        "--",
        "Z80Profiler",
        "-l",
        hex(load_address),
        amsdos_fname,
        csv_fname,
    )

    execute_process(tokens)

    timings = pd.read_csv(
        csv_fname, 
        sep=",", 
        header=0,
        dtype={
            "nop count": int,
            "Execution index":  int
       }
    )
    nops = timings["nop count"][timings["Execution index"]>0]
    res = {
        "nops_init": int(timings["nop count"].values[0]),
        "nops_exec_min": int(nops.min()),
        "nops_exec_max": int(nops.max()),
        "nops_exec_mean": int(nops.mean()),
        "nops_exec_std": int(nops.std()),
        "nops_exec_median": int(nops.median()),
    }
    print(res)
    return res


# python .\profile.py .\datasets\chipnsfx\ABADIA1_CHPZ80.BIN 0x500
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <amsdos_file> <load_address>")
        sys.exit(1)

    import logging
    logging.basicConfig(level=logging.DEBUG)

    amsdos_file = sys.argv[1]
    profile_address = int(sys.argv[2], 16)
    print(f"Profiling {amsdos_file} at address {hex(profile_address)}")
    profile(amsdos_file, profile_address)