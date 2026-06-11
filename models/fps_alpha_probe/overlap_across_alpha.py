#!/usr/bin/env python3
"""
Jaccard overlap of FPS-selected frame sets across fingerprint α values.

For each (retention, replicate), compares which frames were chosen when FPS
runs in different α-spaces (paired by seed). Low overlap means α materially
changes the training subset; high overlap means FPS picks similar frames.

Outputs
-------
  output/overlap/jaccard_{retention_pct}pct_rep{rep:02d}.csv   5×5 matrix
  output/overlap/jaccard_mean_{retention_pct}pct.csv            mean over reps
  output/overlap/jaccard_summary.csv                              long-form table
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from probe_data import ALPHAS, DEFAULT_SAMPLING_RESULTS, alpha_label, load_fps_selections

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def jaccard(a: set[int], b: set[int]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def matrix_for_group(group: pd.DataFrame, alphas: tuple[float, ...]) -> pd.DataFrame:
    sets_by_alpha = {
        row.fps_alpha: set(row.frame_ids)
        for row in group.itertuples(index=False)
    }
    labels = [alpha_label(a) for a in alphas]
    mat = np.zeros((len(alphas), len(alphas)))
    for i, ai in enumerate(alphas):
        for j, aj in enumerate(alphas):
            mat[i, j] = jaccard(sets_by_alpha.get(ai, set()), sets_by_alpha.get(aj, set()))
    return pd.DataFrame(mat, index=labels, columns=labels)


def plot_heatmap(df: pd.DataFrame, out_path: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    sns.heatmap(
        df,
        annot=True,
        fmt=".2f",
        vmin=0.0,
        vmax=1.0,
        cmap="viridis",
        square=True,
        cbar_kws={"label": "Jaccard index"},
        ax=ax,
    )
    ax.set_xlabel("FPS α")
    ax.set_ylabel("FPS α")
    ax.set_title(title)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def run(
    selections: pd.DataFrame,
    output_dir: Path,
    *,
    retention_fractions: tuple[float, ...] | None = None,
) -> pd.DataFrame:
    if retention_fractions is not None:
        selections = selections[
            selections["retention_fraction"].isin(retention_fractions)
        ].copy()

    overlap_dir = output_dir / "overlap"
    overlap_dir.mkdir(parents=True, exist_ok=True)

    summary_rows: list[dict] = []
    for (retention, rep), group in selections.groupby(
        ["retention_fraction", "replicate"], sort=True
    ):
        if group["fps_alpha"].nunique() < 2:
            continue
        mat = matrix_for_group(group, ALPHAS)
        pct = int(round(retention * 100))
        mat.to_csv(overlap_dir / f"jaccard_{pct}pct_rep{rep:02d}.csv")

        for i, ai in enumerate(ALPHAS):
            for j, aj in enumerate(ALPHAS):
                if j <= i:
                    continue
                summary_rows.append(
                    {
                        "retention_fraction": retention,
                        "retention_pct": pct,
                        "replicate": rep,
                        "alpha_a": ai,
                        "alpha_b": aj,
                        "jaccard": float(mat.iloc[i, j]),
                    }
                )

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(overlap_dir / "jaccard_summary.csv", index=False)

    labels = [alpha_label(a) for a in ALPHAS]
    for retention, _ in selections.groupby("retention_fraction"):
        pct = int(round(retention * 100))
        mats: list[np.ndarray] = []
        for _, group in selections[selections["retention_fraction"] == retention].groupby(
            "replicate"
        ):
            if group["fps_alpha"].nunique() < len(ALPHAS):
                continue
            mats.append(matrix_for_group(group, ALPHAS).to_numpy())
        if not mats:
            continue
        mean_df = pd.DataFrame(
            np.mean(mats, axis=0), index=labels, columns=labels
        )
        mean_df.to_csv(overlap_dir / f"jaccard_mean_{pct}pct.csv")

    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sampling-results",
        type=Path,
        default=DEFAULT_SAMPLING_RESULTS,
    )
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument(
        "--retentions",
        type=float,
        nargs="+",
        default=[0.01, 0.10, 0.20],
        help="Retention fractions to include.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    retentions = tuple(args.retentions)
    selections = load_fps_selections(
        args.sampling_results, retention_fractions=retentions
    )
    summary = run(selections, args.output_dir, retention_fractions=retentions)
    print(f"Wrote overlap tables to {args.output_dir / 'overlap'}")
    print(f"  pairwise rows: {len(summary)}")


if __name__ == "__main__":
    main()
