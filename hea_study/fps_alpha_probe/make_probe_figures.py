#!/usr/bin/env python3
"""
Publication macro figures for HEA FPS α probe (four panels only).

Uses fingerprint-space coverage/similarity (not composition bins) for panels
that replace CN statepoint stratification.

  cd hea_study/fps_alpha_probe
  python make_probe_figures.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from convergence_vs_retention import jaccard_alpha0_vs_alpha1
from fingerprint_coverage import aggregate_fingerprint_coverage, fingerprint_coverage_table
from overlap_across_alpha import matrix_for_group
from plot_style import ALPHA_COLORS, apply_style
from probe_data import (
    ALPHAS,
    DEFAULT_CONVERGENCE_RESULTS,
    HEA_DIR,
    alpha_label,
    load_fingerprint_matrices,
    load_fps_selections,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "output"

PANEL_RETENTIONS_PCT = (10, 20, 30, 50, 70)

MACRO_FIGURES = (
    "panel_convergence_summary.png",
    "uniformity_coverage_heatmap.png",
    "jaccard_heatmap_evolution.png",
    "coverage_fingerprint_x_retention.png",
)

FP_METRIC_ROWS = (
    ("mean_nn_cosine_sim", "Mean cosine sim\n(nearest selected)"),
    ("coverage_fraction", "Corpus within\nlocal radius"),
    ("mean_nn_dist_norm", "Proximity score\n(1 / (1 + NN dist))"),
)


def _heatmap_score(col: str, value: float) -> float:
    if col == "mean_nn_dist_norm":
        return 1.0 / (1.0 + value)
    return value


def fig_panel_convergence_summary(
    jacc: pd.DataFrame,
    fp: pd.DataFrame,
    out_path: Path,
) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(9, 7))

    ax = axes[0, 0]
    ax.errorbar(
        jacc["retention_pct"],
        jacc["mean"],
        yerr=jacc["std"].fillna(0),
        color="#333333",
        marker="o",
        capsize=2,
        lw=1.5,
    )
    ax.set_xlabel("Retention (%)")
    ax.set_ylabel("Jaccard(α=0, α=1)")
    ax.set_title("A  Frame-set overlap (composition vs structure)")
    ax.set_ylim(0, 1.05)
    ax.axhline(0.5, color="#999999", ls="--", lw=0.8, alpha=0.7)

    metrics = [
        ("coverage_fraction", "B  Fingerprint neighborhood coverage", "Fraction of corpus"),
        ("mean_nn_cosine_sim", "C  Hold-out similarity", "Mean cosine sim to nearest selected"),
        ("max_nn_dist_norm", "D  Worst-case hold-out distance", "Max NN dist / corpus scale"),
    ]
    for ax, (col, title, ylabel) in zip(
        [axes[0, 1], axes[1, 0], axes[1, 1]], metrics
    ):
        for alpha in ALPHAS:
            sub = fp[fp["fps_alpha"] == alpha].sort_values("retention_pct")
            ax.errorbar(
                sub["retention_pct"],
                sub[f"{col}_mean"],
                yerr=sub[f"{col}_std"].fillna(0),
                marker="o",
                capsize=1.5,
                lw=1.2,
                color=ALPHA_COLORS[alpha],
                label=f"α={alpha_label(alpha)}",
            )
        ax.set_xlabel("Retention (%)")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        if col in ("coverage_fraction", "mean_nn_cosine_sim"):
            ax.set_ylim(0, 1.05)

    handles, labels = axes[0, 1].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=5, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("HEA FPS convergence: fingerprint α and pruning", y=1.02, fontsize=11)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def fig_jaccard_heatmap_evolution(
    selections: pd.DataFrame,
    out_path: Path,
    *,
    retentions_pct: tuple[int, ...] = PANEL_RETENTIONS_PCT,
) -> None:
    n = len(retentions_pct)
    fig, axes = plt.subplots(1, n, figsize=(2.8 * n, 3.2), squeeze=False)
    labels = [alpha_label(a) for a in ALPHAS]
    for ax, pct in zip(axes[0], retentions_pct):
        retention = pct / 100.0
        mats = []
        for _, group in selections[
            selections["retention_fraction"] == retention
        ].groupby("replicate"):
            if group["fps_alpha"].nunique() < len(ALPHAS):
                continue
            mats.append(matrix_for_group(group, ALPHAS).to_numpy())
        if not mats:
            ax.set_visible(False)
            continue
        mean_mat = np.mean(mats, axis=0)
        sns.heatmap(
            pd.DataFrame(mean_mat, index=labels, columns=labels),
            annot=True,
            fmt=".2f",
            vmin=0,
            vmax=1,
            cmap="viridis",
            square=True,
            cbar=False,
            ax=ax,
        )
        ax.set_title(f"{pct}% retention")
        ax.set_xlabel("FPS α")
        ax.set_ylabel("FPS α")
    fig.suptitle("Mean Jaccard overlap across FPS α (HEA, over replicates)", y=1.05)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def fig_coverage_fingerprint_x_retention(fp: pd.DataFrame, out_path: Path) -> None:
    """Per-α heatmaps: fingerprint coverage metrics × retention %."""
    fig, axes = plt.subplots(1, len(ALPHAS), figsize=(3.4 * len(ALPHAS), 4.8), squeeze=False)
    for ax, alpha in zip(axes[0], ALPHAS):
        sub = fp[fp["fps_alpha"] == alpha].sort_values("retention_pct")
        rows: dict[str, list[float]] = {label: [] for _, label in FP_METRIC_ROWS}
        cols: list[int] = []
        for _, row in sub.iterrows():
            cols.append(int(row["retention_pct"]))
            for col, label in FP_METRIC_ROWS:
                rows[label].append(_heatmap_score(col, float(row[f"{col}_mean"])))
        pivot = pd.DataFrame(rows, index=cols).T
        sns.heatmap(
            pivot,
            annot=True,
            fmt=".2f",
            cmap="YlGnBu",
            vmin=0,
            vmax=1,
            cbar=ax == axes[0][-1],
            ax=ax,
        )
        ax.set_title(f"α={alpha_label(alpha)}")
        ax.set_xlabel("Retention (%)")
        if ax == axes[0][0]:
            ax.set_ylabel("Fingerprint metric")
        else:
            ax.set_ylabel("")
            ax.set_yticklabels([])
    fig.suptitle(
        "Fingerprint-space coverage vs pruning (mean over replicates)",
        y=1.02,
    )
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def fig_uniformity_heatmap(fp: pd.DataFrame, out_path: Path) -> None:
    pivot = (
        fp.pivot(index="fps_alpha", columns="retention_pct", values="coverage_fraction_mean")
        .reindex(list(ALPHAS))
    )
    pivot.index = [f"α={alpha_label(a)}" for a in pivot.index]
    fig, ax = plt.subplots(figsize=(10, 3.5))
    sns.heatmap(
        pivot,
        annot=True,
        fmt=".2f",
        cmap="YlGnBu",
        vmin=0,
        vmax=1,
        cbar_kws={"label": "Neighborhood coverage"},
        ax=ax,
    )
    ax.set_xlabel("Retention (%)")
    ax.set_ylabel("FPS α")
    ax.set_title("HEA fingerprint neighborhood coverage: FPS α vs pruning")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def run(convergence_results: Path, fig_dir: Path, *, hea_root: Path = HEA_DIR) -> None:
    apply_style()
    fig_dir.mkdir(parents=True, exist_ok=True)

    conv = load_fps_selections(convergence_results)
    conv_dir = OUTPUT_DIR / "convergence"
    conv_dir.mkdir(parents=True, exist_ok=True)
    fp_csv = conv_dir / "fingerprint_coverage_vs_retention.csv"
    if fp_csv.is_file():
        fp = pd.read_csv(fp_csv)
        fp_long = pd.read_csv(conv_dir / "fingerprint_coverage_long.csv")
    else:
        frame_ids, fingerprints = load_fingerprint_matrices(hea_root)
        fp_long = fingerprint_coverage_table(conv, frame_ids, fingerprints)
        fp = aggregate_fingerprint_coverage(fp_long)
        fp_long.to_csv(conv_dir / "fingerprint_coverage_long.csv", index=False)
        fp.to_csv(fp_csv, index=False)

    jacc = jaccard_alpha0_vs_alpha1(conv)

    fig_panel_convergence_summary(jacc, fp, fig_dir / "panel_convergence_summary.png")
    fig_jaccard_heatmap_evolution(conv, fig_dir / "jaccard_heatmap_evolution.png")
    fig_coverage_fingerprint_x_retention(fp, fig_dir / "coverage_fingerprint_x_retention.png")
    fig_uniformity_heatmap(fp, fig_dir / "uniformity_coverage_heatmap.png")

    stale = fig_dir / "coverage_composition_x_retention.png"
    if stale.is_file():
        stale.unlink()

    print(f"Wrote macro figures to {fig_dir}:")
    for name in MACRO_FIGURES:
        print(f"  {name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--convergence-results", type=Path, default=DEFAULT_CONVERGENCE_RESULTS)
    parser.add_argument("--hea-root", type=Path, default=HEA_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run(args.convergence_results, args.output_dir / "figures", hea_root=args.hea_root)


if __name__ == "__main__":
    main()
