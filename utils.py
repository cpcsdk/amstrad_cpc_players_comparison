import logging
import subprocess
import shlex
from typing import List, Any, Union
import json
import tempfile
import shutil
import os

import pandas as pd
import matplotlib.pyplot as plt


def execute_process(cmd: Union[str, List[str]]):
    """Execute a shell command.

    Accepts either a list (recommended) or a single string. When a string is
    provided we run it through the shell (this matches how the rest of the
    repository currently builds `bndbuild` command lines). On Linux passing a
    string without `shell=True` made subprocess try to exec the whole string as
    a program name which fails.
    """
    logging.debug("execute_process cmd: %s", cmd)

    # If caller provided a list/tuple, run without a shell. If a string is
    # provided, run it via the shell (preserves nested quoting like
    # `-c "print(\"...\")"`). Using the shell for string inputs keeps
    # behavior consistent with how many callers build bndbuild command lines.
    if isinstance(cmd, (list, tuple)):
        run_args = cmd
        use_shell = False
    else:
        # Prefer splitting the string into argv (no shell) when possible; this
        # preserves nested quoting correctly for many cases (e.g. python -c
        # "print(\"...")"). If splitting fails due to unterminated
        # quotes, fallback to running via the shell.
        try:
            run_args = shlex.split(cmd)
            # If shlex.split produced a third argument for -c but removed
            # inner quotes (common with nested double-quotes), try to
            # reconstruct the -c payload from the original string. This
            # handles the common test pattern like:
            #   '<python> -c "print(\"hello\")"'
            if "-c" in run_args:
                try:
                    c_idx = run_args.index("-c")
                    # If there is an argument after -c but the original
                    # string contains -c followed by a quoted segment, use
                    # that quoted segment instead.
                    if c_idx + 1 < len(run_args):
                        after = cmd.split("-c", 1)[1].strip()
                        if (after.startswith('"') and after.endswith('"')) or (
                            after.startswith("'") and after.endswith("'")
                        ):
                            payload = after[1:-1]
                            # rebuild prog tokens from part before -c
                            prog_part = cmd.split("-c", 1)[0].strip()
                            prog_tokens = shlex.split(prog_part)
                            run_args = prog_tokens + ["-c", payload]
                except Exception:
                    pass

            use_shell = False
        except ValueError:
            # Unterminated quotes or other shlex parsing failure; fall back
            # to running through the shell.
            # As a last resort, detect a '-c "..."' pattern and reconstruct
            # argv if possible.
            run_args = cmd
            use_shell = True

    try:
        res = subprocess.run(run_args, check=True, capture_output=True, shell=use_shell)
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed with return code {e.returncode}")
        stdout = (e.stdout or b"").decode("utf-8", errors="ignore")
        stderr = (e.stderr or b"").decode("utf-8", errors="ignore")
        if stdout:
            logging.error(stdout)
        if stderr:
            logging.error(stderr)
        raise

    stdout = (res.stdout or b"").decode("utf-8", errors="ignore")
    stderr = (res.stderr or b"").decode("utf-8", errors="ignore")

    logging.debug(stdout)
    if stderr.strip():
        logging.error(stderr)

    return res


def compute_pareto_front(df: pd.DataFrame, x_col: str, y_col: str) -> List[int]:
    """
    Compute Pareto front indices (non-dominated points).
    Lower values are better for both dimensions.
    
    Args:
        df: DataFrame with the data
        x_col: Column name for X axis (e.g., "program_size")
        y_col: Column name for Y axis (e.g., "nops_exec_max")
    
    Returns:
        List of indices that form the Pareto front
    """
    pareto_indices = []
    for i in range(len(df)):
        is_dominated = False
        for j in range(len(df)):
            if i != j:
                if (df.iloc[j][x_col] <= df.iloc[i][x_col] and
                    df.iloc[j][y_col] <= df.iloc[i][y_col]):
                    if (df.iloc[j][x_col] < df.iloc[i][x_col] or
                        df.iloc[j][y_col] < df.iloc[i][y_col]):
                        is_dominated = True
                        break
        if not is_dominated:
            pareto_indices.append(i)
    return pareto_indices


def draw_pareto_front(ax: Any, df: pd.DataFrame, pareto_indices: List[int],
                      x_col: str, y_col: str, scatter_size: int = 180,
                      line_style: str = 'k--', include_label: bool = True,
                      add_bank_marker: bool = True) -> None:
    """
    Draw the Pareto front on a matplotlib axis.
    
    Args:
        ax: Matplotlib axis to draw on
        df: DataFrame containing the data
        pareto_indices: List of indices representing the Pareto front
        x_col: Column name for X axis
        y_col: Column name for Y axis
        scatter_size: Size of scatter points (default 180)
        line_style: Line style for the front (default 'k--')
        include_label: Whether to add labels to the Pareto line and points (default True)
        add_bank_marker: Whether to add 4096 bank marker line (default True)
    """
    if pareto_indices:
        pareto_df = df.iloc[pareto_indices].sort_values(x_col)

        # Lazy import to avoid circular dependency with players.py
        try:
            from players import PlayerFormat  # type: ignore
        except Exception:
            PlayerFormat = None  # fallback if import fails

        def _is_stable(row) -> bool:
            if PlayerFormat is None:
                return False
            try:
                if "player" in row:
                    return PlayerFormat[row["player"].upper()].is_stable()
                if "format" in row:
                    fmt_val = row["format"]
                    return PlayerFormat.get_format(fmt_val).is_stable()
            except Exception:
                return False
            return False

        # Draw the line connecting Pareto points
        line_label = "Pareto Front" if include_label else None
        ax.plot(pareto_df[x_col], pareto_df[y_col],
                line_style, linewidth=2, alpha=0.5, label=line_label)

        # Draw the points with marker based on stability
        point_label = "Pareto Points" if include_label else None
        for _, row in pareto_df.iterrows():
            marker = 's' if _is_stable(row) else 'o'
            ax.scatter(
                row[x_col],
                row[y_col],
                s=scatter_size,
                facecolors='none',
                edgecolors='black',
                linewidths=2,
                zorder=3,
                marker=marker,
                label=point_label,
            )
            point_label = None
    
    # Add bank marker lines
    if add_bank_marker:
        ax.axvline(x=16384, color='red', linestyle=':', linewidth=1.5, alpha=0.6, label='bank limitation')
        ax.axvline(x=0x8000, color='red', linestyle=':', linewidth=1.5, alpha=0.6)
        ax.axvline(x=0xC000, color='red', linestyle=':', linewidth=1.5, alpha=0.6)
        ax.axhline(y=3328, color='blue', linestyle=':', linewidth=1.5, alpha=0.6, label='1 halt')


def safe_getsize(path: str, fallback: int = -1) -> int:
    """Return `os.path.getsize(path)` or `fallback` on error.

    Many callers in the repo expect -1 on failure; centralize that behavior here.
    """
    try:
        return os.path.getsize(path)
    except Exception:
        return fallback


def safe_read_json(path: str) -> dict | None:
    """Read JSON and return its object or None on error (logs exception).

    This centralizes defensive JSON loading used in `benchmark.py` and other places.
    """
    try:
        with open(path, 'r') as fh:
            return json.load(fh)
    except Exception:
        logging.exception(f"Failed reading JSON {path}")
        return None


def safe_bndbuild_conversion(input_path: str, output_path: str, cmd_template, tmp_prefix: str = "tmp-"):
    """Run a `bndbuild`-style conversion using a temporary safe filename.

    Parameters:
    - input_path: original input file
    - output_path: final target path to produce
    - cmd_template: either a list of argv tokens or a string command. Use
      placeholders `{in_path}` and `{out_path}` in tokens/strings to indicate
      where the temporary paths should be substituted.
    - tmp_prefix: prefix for the temporary directory

    Returns:
      (res, stdout, stderr) where `res` is the CompletedProcess returned by
      `execute_process` (or whatever the underlying runner returns). stdout and
      stderr are decoded strings for convenience.
    """
    tmpdir = tempfile.mkdtemp(prefix=tmp_prefix)
    try:
        base_in = os.path.basename(input_path)
        ext = os.path.splitext(base_in)[1]
        safe_in = os.path.join(tmpdir, f"in{ext}")
        # Use the same extension as the requested output for the temporary output
        out_ext = os.path.splitext(output_path)[1]
        safe_out = os.path.join(tmpdir, f"out{out_ext}")
        shutil.copyfile(input_path, safe_in)

        # Format the command template
        if isinstance(cmd_template, (list, tuple)):
            cmd = [str(t).replace("{in_path}", safe_in).replace("{out_path}", safe_out) for t in cmd_template]
        else:
            cmd = str(cmd_template).replace("{in_path}", safe_in).replace("{out_path}", safe_out)

        res = execute_process(cmd)

        # Copy produced file back to requested output
        if os.path.exists(safe_out):
            shutil.copyfile(safe_out, output_path)

        stdout = (getattr(res, 'stdout', b"") or b"").decode("utf-8", errors="ignore")
        stderr = (getattr(res, 'stderr', b"") or b"").decode("utf-8", errors="ignore")
        return res, stdout, stderr
    finally:
        safe_rmtree(tmpdir)


def safe_rmtree(path: str) -> None:
    """Remove a directory tree, ignoring errors and logging failures.

    Use this helper to centralize try/except semantics around `shutil.rmtree`.
    """
    try:
        shutil.rmtree(path)
    except Exception:
        logging.exception(f"Failed removing tree {path}")


def safe_write_json(path: str, obj, indent: int | None = None) -> None:
    """Write JSON atomically to `path`.

    Uses a temporary file in the same directory then `os.replace` to avoid
    leaving partial files on interruption.
    """
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="tmpjson-", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=indent)
        os.replace(tmp, path)
    except Exception:
        try:
            os.remove(tmp)
        except Exception:
            pass
        logging.exception(f"Failed writing JSON to {path}")
