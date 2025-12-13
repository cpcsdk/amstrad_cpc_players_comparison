import sys
import subprocess
import pytest
from pathlib import Path

# Ensure repository root is on sys.path so tests can import project modules
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

from utils import execute_process


def test_execute_process_list_success():
    # Use the current Python interpreter to print a known value
    cmd = [sys.executable, "-c", "print('hello-from-list')"]
    res = execute_process(cmd)
    out = res.stdout.decode("utf-8").strip()
    assert "hello-from-list" in out


def test_execute_process_str_success():
    # Shell string form with Python (cross-platform)
    cmd = f'{sys.executable} -c "print(\"hello-from-str\")"'
    res = execute_process(cmd)
    out = res.stdout.decode("utf-8").strip()
    assert "hello-from-str" in out


def test_execute_process_list_failure_raises():
    # Command exits with non-zero -> CalledProcessError
    cmd = [sys.executable, "-c", "import sys; sys.exit(3)"]
    with pytest.raises(subprocess.CalledProcessError):
        execute_process(cmd)


def test_execute_process_str_failure_raises():
    # Build a string that will use the current python binary and exit non-zero
    cmd = f'{sys.executable} -c "import sys; sys.exit(4)"'
    with pytest.raises(subprocess.CalledProcessError):
        execute_process(cmd)
