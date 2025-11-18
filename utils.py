import logging
import subprocess

def execute_process(cmd):
    logging.debug(cmd)
    res = subprocess.run(cmd, check=True, capture_output=True)
    logging.debug(res.stdout)
    logging.error(res.stderr)

    return res