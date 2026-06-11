#!/usr/bin/env python3
"""
Statepoint coverage of FPS training subsets across fingerprint α.

Tags each corpus frame with (N%, ρ, T) via statepoints.json anchor frames,
then counts how many selected training frames fall in each thermodynamic case.

Outputs
-------
  output/coverage/counts_long.csv
  output/coverage/uniformity_metrics.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from probe_data import (
    ALPHAS,
    DEFAULT_SAMPLING_RESULTS,
    DEFAULT_STATEPOINTS_JSON,
    alpha_label,
    build_frame_statepoint_table,
    load_fps_selections,
    load_statepoints,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def counts_for_selection(
    frame_ids: list[int],
    frame_table: pd.DataFrame,
    statepoint_order: list[str],
) -> pd.Series:
    sub = frame_table[frame_table["frame_id"].isin(frame_ids)]
    counts = sub.groupby("statepoint_id").size()
    return pd.Series(
        {sp: int(counts.get(sp, 0)) for sp in statepoint_order},
        dtype=int,
    )


def uniformity_metrics(counts: pd.Series, n_cases: int) -> dict[str, float]:
    arr = counts.to_numpy(dtype=float)
    total = arr.sum()
    if total <= 0:
        return {
            "n_cases_covered": 0.0,
            "coverage_fraction": 0.0,
            "entropy_norm": 0.0,
            "min_count": 0.0,
            "max_count": 0.0,
            "cv_count": np.nan,
        }
    probs = arr / total
    probs_nz = probs[probs > 0]
    entropy = -np.sum(probs_nz * np.log(probs_nz))
    entropy_norm = entropy / np.log(n_cases) if n_cases > 1 else 1.0
    mean = arr.mean()
    cv = float(arr.std() / mean) if mean > 0 else np.nan
    return {
        "n_cases_covered": float((arr > 0).sum()),
        "coverage_fraction": float((arr > 0).sum() / n_cases),
        "entropy_norm": float(entropy_norm),
        "min_count": float(arr.min()),
        "max_count": float(arr.max()),
        "cv_count": cv,
    }


def plot_coverage_heatmap(
    pivot: pd.DataFrame,
    out_path: Path,
    title: str,
    *,
    annot_fmt: str | None = None,
) -> None:
    if annot_fmt is None:
        annot_fmt = "d" if np.issubdtype(pivot.dtypes.iloc[0], np.integer) else ".1f"
    fig_h = max(4.0, 0.35 * len(pivot.index))
    fig, ax = plt.subplots(figsize=(6.5, fig_h))
    sns.heatmap(
        pivot,
        annot=True,
        fmt=annot_fmt,
        cmap="Blues",
        cbar_kws={"label": "Selected frames"},
        ax=ax,
    )
    ax.set_xlabel("FPS α")
    ax.set_ylabel("Statepoint")
    ax.set_title(title)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def plot_uniformity(
    metrics: pd.DataFrame,
    retention_pct: int,
    out_path: Path,
) -> None:
    sub = metrics[metrics["retention_pct"] == retention_pct].copy()
    if sub.empty:
        return
    agg = (
        sub.groupby("fps_alpha")[
            ["coverage_fraction", "entropy_norm", "cv_count"]
        ]
        .agg(["mean", "std"])
        .reset_index()
    )
    alphas = [alpha_label(a) for a in agg["fps_alpha"]]

    fig, axes = plt.subplots(1, 3, figsize=(11, 3.5), sharex=True)
    specs = [
        ("coverage_fraction", "Cases with ≥1 frame", (0, 1.05)),
        ("entropy_norm", "Normalized entropy", (0, 1.05)),
        ("cv_count", "Count CV (lower = more uniform)", None),
    ]
    for ax, (col, ylabel, ylim) in zip(axes, specs):
        mean = agg[(col, "mean")].to_numpy()
        std = agg[(col, "std")].fillna(0).to_numpy()
        x = np.arange(len(alphas))
        ax.bar(x, mean, yerr=std, capsize=3, color="#4c72b0", alpha=0.85)
        ax.set_xticks(x)
        ax.set_xticklabels(alphas)
        ax.set_xlabel("FPS α")
        ax.set_ylabel(ylabel)
        if ylim:
            ax.set_ylim(*ylim)
    fig.suptitle(f"Statepoint coverage uniformity ({retention_pct}% retention)")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def run(
    selections: pd.DataFrame,
    frame_table: pd.DataFrame,
    output_dir: Path,
    *,
    retention_fractions: tuple[float, ...] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if retention_fractions is not None:
        selections = selections[
            selections["retention_fraction"].isin(retention_fractions)
        ].copy()

    statepoint_order = sorted(frame_table["statepoint_id"].unique())
    n_cases = len(statepoint_order)

    cov_dir = output_dir / "coverage"
    cov_dir.mkdir(parents=True, exist_ok=True)

    count_rows: list[dict] = []
    metric_rows: list[dict] = []

    for row in selections.itertuples(index=False):
        counts = counts_for_selection(row.frame_ids, frame_table, statepoint_order)
        metrics = uniformity_metrics(counts, n_cases)
        metric_rows.append(
            {
                "fps_alpha": row.fps_alpha,
                "retention_fraction": row.retention_fraction,
                "retention_pct": row.retention_pct,
                "replicate": row.replicate,
                "seed": row.seed,
                **metrics,
            }
        )
        for sp_id, n in counts.items():
            count_rows.append(
                {
                    "fps_alpha": row.fps_alpha,
                    "retention_fraction": row.retention_fraction,
                    "retention_pct": row.retention_pct,
                    "replicate": row.replicate,
                    "statepoint_id": sp_id,
                    "n_frames": int(n),
                }
            )

    counts_long = pd.DataFrame(count_rows)
    metrics_df = pd.DataFrame(metric_rows)
    counts_long.to_csv(cov_dir / "counts_long.csv", index=False)
    metrics_df.to_csv(cov_dir / "uniformity_metrics.csv", index=False)

    return counts_long, metrics_df


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sampling-results",
        type=Path,
        default=DEFAULT_SAMPLING_RESULTS,
    )
    parser.add_argument(
        "--statepoints-json",
        type=Path,
        default=DEFAULT_STATEPOINTS_JSON,
    )
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument(
        "--retentions",
        type=float,
        nargs="+",
        default=[0.01, 0.10, 0.20],
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    retentions = tuple(args.retentions)
    statepoints = load_statepoints(args.statepoints_json)
    frame_table = build_frame_statepoint_table(statepoints)
    frame_table.to_csv(args.output_dir / "coverage" / "frame_statepoint_map.csv", index=False)

    selections = load_fps_selections(
        args.sampling_results, retention_fractions=retentions
    )
    counts_long, metrics_df = run(
        selections,
        frame_table,
        args.output_dir,
        retention_fractions=retentions,
    )
    print(f"Wrote coverage tables to {args.output_dir / 'coverage'}")
    print(f"  count rows: {len(counts_long)}")
    print(f"  metric rows: {len(metrics_df)}")


if __name__ == "__main__":
    main()
