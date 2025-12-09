from utils import *
import os
import pandas as pd

def profile(amsdos_fname, load_address):
    """
    Profile a replay routine by executing it 10000 times
    """
    assert os.path.exists(amsdos_fname), f"File {amsdos_fname} does not exist"

    prof = os.path.join("tools", "Z80Profiler.exe")
    csv_fname = os.path.splitext(amsdos_fname)[0] + ".CSV"
    cmd = f'{prof} "{amsdos_fname}" "{csv_fname}" -l {hex(load_address)}'

    execute_process(cmd)

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