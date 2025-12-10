import logging
import subprocess
from typing import List, Any

import pandas as pd
import matplotlib.pyplot as plt


def execute_process(cmd):
    logging.debug(cmd)
    res = subprocess.run(cmd, check=True, capture_output=True)

    logging.debug(res.stdout)
    if res.stderr.decode("utf-8").strip():
        logging.error(res.stderr)

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
                      line_style: str = 'k--', include_label: bool = True) -> None:
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
    """
    if pareto_indices:
        pareto_df = df.iloc[pareto_indices].sort_values(x_col)
        
        # Draw the line connecting Pareto points
        line_label = "Pareto Front" if include_label else None
        ax.plot(pareto_df[x_col], pareto_df[y_col],
                line_style, linewidth=2, alpha=0.5, label=line_label)
        
        # Draw the points
        point_label = "Pareto Points" if include_label else None
        ax.scatter(pareto_df[x_col], pareto_df[y_col],
                  s=scatter_size, facecolors='none', edgecolors='black',
                  linewidths=2, zorder=3, label=point_label)
