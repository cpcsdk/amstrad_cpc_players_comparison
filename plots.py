# Headless plotting helpers for player_benchmark
import os
import logging
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from math import pi
from matplotlib.ticker import FuncFormatter
from matplotlib.patches import Ellipse
from utils import compute_pareto_front, draw_pareto_front
from players import PlayerFormat


def plot_spider(
    benchmark, df: pd.DataFrame, ordered_extensions: list, format_colors: dict, report
) -> None:
    report.write("\n\n# Spider Charts by Player Format\n\n")
    metrics = [col for col in df.columns if col not in ["format", "sources"]]
    n_formats = len(ordered_extensions)
    if n_formats == 0:
        logging.info("No formats present for spider charts; skipping")
        report.write("\nNo formats available for spider charts.\n")
        return
    n_cols = min(3, n_formats)
    n_rows = (n_formats + n_cols - 1) // n_cols

    fig, axes = plt.subplots(
        n_rows,
        n_cols,
        figsize=(6 * n_cols, 6 * n_rows),
        subplot_kw=dict(projection="polar"),
    )
    if n_formats == 1:
        axes = np.array([axes])
    axes = axes.flatten()

    for idx, fmt in enumerate(ordered_extensions):
        ax = axes[idx]
        format_data = df[df["format"] == fmt]
        categories = metrics
        N = len(categories)

        angles = [n / float(N) * 2 * pi for n in range(N)]
        angles += angles[:1]

        values = []
        for metric in metrics:
            metric_values = format_data[metric].values
            if len(metric_values) > 0:
                max_val = df[metric].max()
                min_val = df[metric].min()
                if max_val == min_val:
                    normalized = 0.5
                else:
                    normalized = (metric_values.mean() - min_val) / (max_val - min_val)
                values.append(normalized)
            else:
                values.append(0)

        values += values[:1]
        color = format_colors.get(fmt, None) if format_colors else None
        ax.plot(angles, values, "o-", linewidth=2, label=fmt, color=color)
        ax.fill(angles, values, alpha=0.25, color=color)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, size=8)
        ax.set_ylim(0, 1)
        ax.set_title(f"{fmt}", size=12, weight="bold", pad=20)
        ax.grid(True)

    for idx in range(n_formats, len(axes)):
        axes[idx].set_visible(False)

    plt.tight_layout()
    spider_png = f"reports/spider_charts_{benchmark.name}.png"
    try:
        fig.savefig(spider_png, dpi=100, bbox_inches="tight")
        report.write(
            f"\n\n![Spider Charts by Format]({os.path.basename(spider_png)})\n"
        )
        report.write(
            "\nNote: In spider charts, values closer to the center (0.0) indicate better performance (lower size/time).\n"
        )
    except Exception:
        logging.exception(f"Failed to save {spider_png}")
    plt.close(fig)


def _palette_for_ordered(format_colors: dict, ordered_extensions: list):
    """Return a palette mapping (format -> color) for the given ordered formats.

    Centralized palette construction used by plotting helpers. If
    `format_colors` is None, returns None to let seaborn pick defaults.
    """
    if format_colors is None:
        return None

    palette = {}
    auto_palette = sns.color_palette("tab10", n_colors=max(1, len(ordered_extensions)))
    for i, fmt in enumerate(ordered_extensions):
        palette[fmt] = format_colors.get(fmt, auto_palette[i % len(auto_palette)])
    # Backwards compatibility: map CHPB -> CHP if present
    if "CHPB" in palette:
        palette["CHP"] = palette["CHPB"]
    return palette


def prepare_format_colors(benchmark, df: pd.DataFrame):
    """Derive the ordered formats and a color mapping for the present formats.

    Returns (ordered_extensions, format_colors)
    """
    # Canonical ordering: prefer the order of players configured for this benchmark
    preferred_order = [p.name for p in getattr(benchmark, "players", [])]
    palette_full = sns.color_palette("tab10", n_colors=max(1, len(preferred_order)))
    full_color_map = dict(zip(preferred_order, palette_full))

    # Keep only formats present in the dataframe (preserve player order)
    ordered_extensions = [c for c in preferred_order if c in df["format"].unique()]
    format_colors = {k: full_color_map.get(k) for k in ordered_extensions}
    return ordered_extensions, format_colors


def plot_scatter_tracks(
    benchmark, df: pd.DataFrame, ordered_extensions: list, format_colors: dict, report
) -> None:
    report.write("\n\n# Program Size vs Maximum Execution Time\n\n")
    fig, ax = plt.subplots(figsize=(10, 6))
    for source in df["sources"].unique():
        source_data = df[df["sources"] == source].sort_values("prog_size")
        ax.plot(
            source_data["prog_size"],
            source_data["max_execution_time"],
            color="gray",
            alpha=0.2,
            linewidth=1,
            zorder=1,
        )

    for fmt in ordered_extensions:
        format_data = df[df["format"] == fmt]
        # Use square marker for stable players, circle for others
        try:
            player_format = PlayerFormat.get_format(fmt)
            marker = "s" if player_format.is_stable() else "o"
        except Exception:
            marker = "o"

        # Scatter for this format (always run regardless of PlayerFormat lookup)
        ax.scatter(
            format_data["prog_size"],
            format_data["max_execution_time"],
            label=fmt,
            s=24,
            alpha=0.6,
            zorder=2,
            color=(format_colors.get(fmt) if format_colors else None),
            marker=marker,
        )

    ax.set_xlabel("Program Size (bytes)")
    ax.set_ylabel("Maximum Execution Time (nops)")
    ax.set_title("Program Size vs Maximum Execution Time by Player Format")
    ax.grid(True, alpha=0.3)

    # Add reference lines
    ax.axvline(
        x=16384,
        color="red",
        linestyle=":",
        linewidth=1.5,
        alpha=0.6,
        label="bank limitation",
    )
    ax.axvline(x=0x8000, color="red", linestyle=":", linewidth=1.5, alpha=0.6)
    ax.axvline(x=0xC000, color="red", linestyle=":", linewidth=1.5, alpha=0.6)
    ax.axhline(
        y=3328, color="blue", linestyle=":", linewidth=1.5, alpha=0.6, label="1 halt"
    )

    ax.legend()
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)

    # Format x-axis as hexadecimal
    ax.xaxis.set_major_formatter(
        FuncFormatter(lambda x, pos: f"0x{int(x):04X} ({int(x)})")
    )

    scatter_png = f"reports/scatter_prog_size_vs_exec_time_{benchmark.name}.png"
    try:
        fig.savefig(scatter_png, dpi=100, bbox_inches="tight")
        report.write(f"\n\n![Scatter Plot]({os.path.basename(scatter_png)})\n")
    except Exception as e:
        logging.error(f"Failed to save {scatter_png}: {e}")
    plt.close(fig)


def plot_scatter_median(
    benchmark, df: pd.DataFrame, ordered_extensions: list, format_colors: dict, report
) -> None:
    report.write("\n\n# Player Formats Comparison (Median Values)\n\n")
    fig, ax = plt.subplots(figsize=(10, 6))
    player_stats = []
    for fmt in ordered_extensions:
        format_data = df[df["format"] == fmt]
        median_prog_size = format_data["prog_size"].median()
        median_exec_time = format_data["max_execution_time"].median()
        std_prog_size = format_data["prog_size"].std()
        std_exec_time = format_data["max_execution_time"].std()
        player_stats.append(
            {
                "format": fmt,
                "prog_size": median_prog_size,
                "max_execution_time": median_exec_time,
                "std_prog_size": std_prog_size if not np.isnan(std_prog_size) else 0,
                "std_exec_time": std_exec_time if not np.isnan(std_exec_time) else 0,
            }
        )

    player_df = pd.DataFrame(player_stats)

    handles = []
    labels = []
    for _, row in player_df.iterrows():
        color = format_colors.get(row["format"]) if format_colors else "C0"
        # Use square marker for stable players, circle for others
        try:
            player_format = PlayerFormat.get_format(row["format"])
            marker = "s" if player_format.is_stable() else "o"
        except Exception:
            marker = "o"
        # Always create the scatter point and record its handle
        sc = ax.scatter(
            row["prog_size"],
            row["max_execution_time"],
            s=50,
            alpha=0.7,
            color=color,
            marker=marker,
            label=row["format"],
        )
        handles.append(sc)
        labels.append(row["format"])

        width = 2 * row["std_prog_size"]
        height = 2 * row["std_exec_time"]
        patch = Ellipse(
            (row["prog_size"], row["max_execution_time"]),
            width=width,
            height=height,
            alpha=0.2,
            color=color,
        )

        ax.add_patch(patch)
        ax.annotate(
            row["format"],
            (row["prog_size"], row["max_execution_time"]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=10,
        )

    pareto_indices = compute_pareto_front(player_df, "prog_size", "max_execution_time")
    draw_pareto_front(
        ax,
        player_df,
        pareto_indices,
        "prog_size",
        "max_execution_time",
        scatter_size=48,
        include_label=True,
    )

    ax.set_xlabel("Median Program Size (bytes)")
    ax.set_ylabel("Median Maximum Execution Time (nops)")
    ax.set_title("Player Formats Comparison (Median Values ± 1 Std Dev)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)

    # Format x-axis as hexadecimal
    ax.xaxis.set_major_formatter(
        FuncFormatter(lambda x, pos: f"0x{int(x):04X} ({int(x)})")
    )

    scatter_median_png = (
        f"reports/scatter_median_prog_size_vs_exec_time_{benchmark.name}.png"
    )
    try:
        fig.savefig(scatter_median_png, dpi=100, bbox_inches="tight")
        report.write(
            f"\n\n![Scatter Plot - Median Values]({os.path.basename(scatter_median_png)})\n"
        )
        report.write(
            "\nNote: Shaded regions show ±1 standard deviation (ellipse for circle markers, square for stable players). The dashed line represents the Pareto front (non-dominated players).\n"
        )
    except Exception as e:
        logging.error(f"Failed to save {scatter_median_png}: {e}")
    plt.close(fig)


def plot_parallel_coordinates(
    benchmark,
    summary: pd.DataFrame,
    ordered_extensions: list,
    comparison_key: str,
    title: str,
    report,
) -> None:
    plot_x = list(range(len(ordered_extensions)))
    fig, ax = plt.subplots(figsize=(10, 6))
    for _, row in summary.iterrows():
        ax.plot(plot_x, [row[k] for k in ordered_extensions], c="gray", alpha=0.4)
    ax.set_xticks(plot_x)
    ax.set_xticklabels(ordered_extensions)
    ax.set_xlabel("Format")
    ax.set_ylabel(title)
    parallel_png = f"reports/{comparison_key}_parallel_coordinates_{benchmark.name}.png"
    try:
        fig.savefig(parallel_png, dpi=100, bbox_inches="tight")
        report.write(f"\n\n![Parallel coordinates]({os.path.basename(parallel_png)})\n")
    except Exception as e:
        logging.error(f"Failed to save {parallel_png}: {e}")
    plt.close(fig)


def plot_boxplot(
    benchmark,
    df: pd.DataFrame,
    ordered_extensions: list,
    comparison_key: str,
    title: str,
    format_colors: dict = None,
    report=None,
) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))
    # Build palette mapping for ordered_extensions using local helper
    palette = _palette_for_ordered(format_colors, ordered_extensions)

    # Use hue='format' with dodge=False to apply explicit palette without deprecation warning
    try:
        sns.boxplot(
            data=df,
            x="format",
            y=comparison_key,
            hue="format",
            dodge=False,
            ax=ax,
            order=ordered_extensions,
            palette=palette,
        )
    except ValueError:
        logging.warning(
            "Boxplot palette mapping failed; retrying without explicit palette"
        )
        sns.boxplot(
            data=df,
            x="format",
            y=comparison_key,
            hue="format",
            dodge=False,
            ax=ax,
            order=ordered_extensions,
        )

    # remove redundant legend created by hue
    lg = ax.get_legend()
    if lg:
        lg.remove()
    ax.set_ylabel(title)
    boxplot_png = f"reports/{comparison_key}_boxplot_{benchmark.name}.png"
    try:
        fig.savefig(boxplot_png, dpi=100, bbox_inches="tight")
        if report is not None:
            report.write(f"\n\n![Boxplot]({os.path.basename(boxplot_png)})\n")
    except Exception as e:
        logging.error(f"Failed to save {boxplot_png}: {e}")
    plt.close(fig)


def plot_violin(
    benchmark,
    df: pd.DataFrame,
    ordered_extensions: list,
    comparison_key: str,
    title: str,
    format_colors: dict = None,
    report=None,
) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))
    # Build palette mapping for ordered_extensions using local helper
    palette = _palette_for_ordered(format_colors, ordered_extensions)

    try:
        sns.violinplot(
            data=df,
            x="format",
            y=comparison_key,
            hue="format",
            dodge=False,
            ax=ax,
            order=ordered_extensions,
            cut=0,
            inner="quartile",
            density_norm="width",
            linewidth=0.6,
            palette=palette,
        )
    except ValueError:
        logging.warning(
            "Violin plot palette mapping failed; retrying without explicit palette"
        )
        sns.violinplot(
            data=df,
            x="format",
            y=comparison_key,
            hue="format",
            dodge=False,
            ax=ax,
            order=ordered_extensions,
            cut=0,
            inner="quartile",
            density_norm="width",
            linewidth=0.6,
        )

    # remove redundant legend created by hue
    lg = ax.get_legend()
    if lg:
        lg.remove()
    ax.set_ylabel(title)
    violin_png = f"reports/{comparison_key}_violin_{benchmark.name}.png"
    try:
        fig.savefig(violin_png, dpi=100, bbox_inches="tight")
        if report is not None:
            report.write(f"\n\n![Violin Plot]({os.path.basename(violin_png)})\n")
    except Exception as e:
        logging.error(f"Failed to save {violin_png}: {e}")
    plt.close(fig)
