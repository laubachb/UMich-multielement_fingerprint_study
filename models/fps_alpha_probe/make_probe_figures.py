#!/usr/bin/env python3
"""
Publication macro figures for CN FPS α probe (four panels only).

Reads models/sampling/results_convergence_5pct/ and output/convergence/*.csv.

Usage
-----
  cd models/fps_alpha_probe
  python make_probe_figures.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from convergence_vs_retention import (
    jaccard_alpha0_vs_alpha1,
    uniformity_vs_retention,
)
from overlap_across_alpha import matrix_for_group
from plot_style import ALPHA_COLORS, apply_style
from probe_data import (
    ALPHAS,
    DEFAULT_CONVERGENCE_RESULTS,
    DEFAULT_STATEPOINTS_JSON,
    alpha_label,
    build_frame_statepoint_table,
    load_fps_selections,
    load_statepoints,
)
from statepoint_coverage import counts_for_selection

OUTPUT_DIR = Path(__file__).resolve().parent / "output"

PANEL_RETENTIONS_PCT = (10, 20, 30, 50, 70)

MACRO_FIGURES = (
    "panel_convergence_summary.png",
    "uniformity_coverage_heatmap.png",
    "jaccard_heatmap_evolution.png",
    "coverage_statepoint_x_retention.png",
)


def statepoint_labels(statepoints: list[dict]) -> dict[str, str]:
    return {
        sp["id"]: f"#{sp['case']}  {int(sp['temperature_k'])} K\n{sp['density_gcc']} g/cc"
        for sp in statepoints
    }


def coverage_grid_by_alpha(
    selections: pd.DataFrame,
    frame_table: pd.DataFrame,
    statepoint_order: list[str],
) -> dict[float, pd.DataFrame]:
    grids: dict[float, list[dict]] = {a: [] for a in ALPHAS}
    for row in selections.itertuples(index=False):
        counts = counts_for_selection(row.frame_ids, frame_table, statepoint_order)
        for sp_id, n in counts.items():
            grids[row.fps_alpha].append(
                {
                    "statepoint_id": sp_id,
                    "retention_pct": row.retention_pct,
                    "n_frames": int(n),
                }
            )
    out: dict[float, pd.DataFrame] = {}
    for alpha in ALPHAS:
        sub = pd.DataFrame(grids[alpha])
        pivot = (
            sub.groupby(["statepoint_id", "retention_pct"])["n_frames"]
            .mean()
            .reset_index()
            .pivot(index="statepoint_id", columns="retention_pct", values="n_frames")
            .reindex(statepoint_order)
        )
        out[alpha] = pivot
    return out


def fig_panel_convergence_summary(
    jacc: pd.DataFrame,
    uni: pd.DataFrame,
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
        ("coverage_fraction", "B  Statepoint case coverage", "Fraction of 10 cases"),
        ("entropy_norm", "C  Coverage uniformity", "Normalized entropy"),
        ("n_cases_covered", "D  Cases represented (of 10)", "Mean count"),
    ]
    for ax, (col, title, ylabel) in zip(
        [axes[0, 1], axes[1, 0], axes[1, 1]], metrics
    ):
        for alpha in ALPHAS:
            sub = uni[uni["fps_alpha"] == alpha].sort_values("retention_pct")
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
        if col in ("coverage_fraction", "entropy_norm"):
            ax.set_ylim(0, 1.05)

    handles, labels = axes[0, 1].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=5, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("CN FPS convergence: fingerprint α and retention", y=1.02, fontsize=11)
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
    fig.suptitle("Mean Jaccard overlap across FPS α (CN, over replicates)", y=1.05)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def fig_coverage_statepoint_x_retention(
    grids: dict[float, pd.DataFrame],
    sp_labels: dict[str, str],
    out_path: Path,
) -> None:
    fig, axes = plt.subplots(1, len(ALPHAS), figsize=(3.2 * len(ALPHAS), 5.5), squeeze=False)
    vmax = max(g.max().max() for g in grids.values() if not g.empty)
    for ax, alpha in zip(axes[0], ALPHAS):
        pivot = grids[alpha].rename(index=sp_labels)
        sns.heatmap(
            pivot,
            cmap="Blues",
            annot=False,
            vmin=0,
            vmax=vmax,
            cbar=ax == axes[0][-1],
            ax=ax,
        )
        ax.set_title(f"α={alpha_label(alpha)}")
        ax.set_xlabel("Retention (%)")
        if ax == axes[0][0]:
            ax.set_ylabel("Statepoint")
        else:
            ax.set_ylabel("")
            ax.set_yticklabels([])
    fig.suptitle("Mean selected frames per CN statepoint (over replicates)", y=1.02)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def fig_uniformity_heatmap(uni: pd.DataFrame, out_path: Path) -> None:
    pivot = (
        uni.pivot(index="fps_alpha", columns="retention_pct", values="coverage_fraction_mean")
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
        cbar_kws={"label": "Case coverage"},
        ax=ax,
    )
    ax.set_xlabel("Retention (%)")
    ax.set_ylabel("FPS α")
    ax.set_title("CN thermodynamic coverage: FPS α vs retention")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def run(
    convergence_results: Path,
    statepoints_json: Path,
    fig_dir: Path,
) -> None:
    apply_style()
    fig_dir.mkdir(parents=True, exist_ok=True)

    statepoints = load_statepoints(statepoints_json)
    frame_table = build_frame_statepoint_table(statepoints)
    sp_labels = statepoint_labels(statepoints)
    statepoint_order = [sp["id"] for sp in statepoints]

    conv = load_fps_selections(convergence_results)
    jacc = jaccard_alpha0_vs_alpha1(conv)
    uni = uniformity_vs_retention(conv, frame_table)
    grids = coverage_grid_by_alpha(conv, frame_table, statepoint_order)

    fig_panel_convergence_summary(jacc, uni, fig_dir / "panel_convergence_summary.png")
    fig_jaccard_heatmap_evolution(conv, fig_dir / "jaccard_heatmap_evolution.png")
    fig_coverage_statepoint_x_retention(
        grids, sp_labels, fig_dir / "coverage_statepoint_x_retention.png"
    )
    fig_uniformity_heatmap(uni, fig_dir / "uniformity_coverage_heatmap.png")

    print(f"Wrote macro figures to {fig_dir}:")
    for name in MACRO_FIGURES:
        print(f"  {name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--convergence-results", type=Path, default=DEFAULT_CONVERGENCE_RESULTS)
    parser.add_argument("--statepoints-json", type=Path, default=DEFAULT_STATEPOINTS_JSON)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run(
        args.convergence_results,
        args.statepoints_json,
        args.output_dir / "figures",
    )


if __name__ == "__main__":
    main()
