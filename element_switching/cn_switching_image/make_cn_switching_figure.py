#!/usr/bin/env python3
"""
CN element-switching fingerprint figure for graphite at 1500 K.

Reads element-aware cluster-graph fingerprints across five nitrogen compositions
(0%, 25%, 50%, 75%, 100%) and five ChIMES alpha values (0.00–1.00).

The fingerprint vector for each (composition, alpha) pair is the concatenation
of the second column from 2B, 3B, and 4B histogram files (300 bins total).

Layout
------
5 subplots stacked vertically, one per nitrogen composition (increasing from
top to bottom). Within each subplot, lines for all 5 alpha values are drawn
and colored by viridis. A single shared colorbar on the right encodes alpha.
Dashed vertical lines separate the 2-body, 3-body, and 4-body fingerprint
regions.

Output
------
./cn_switching_fingerprints.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize

matplotlib.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_FP_BASE = SCRIPT_DIR.parent / "data" / "graphite" / "fingerprints"

COMPOSITIONS = [0, 25, 50, 75, 100]
ALPHA_INTS = [0, 25, 50, 75, 100]
ALPHA_VALS = [0.00, 0.25, 0.50, 0.75, 1.00]

HIST_FILES = [
    "0-0.2b_clu-s.hist",
    "0-0.3b_clu-s.hist",
    "0-0.4b_clu-s.hist",
]
BODY_LABELS = ["2-body", "3-body", "4-body"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fingerprints-dir",
        type=Path,
        default=DEFAULT_FP_BASE,
        help="Root directory with graphite_1500K_0262_*pct/ subdirs.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=SCRIPT_DIR / "cn_switching_fingerprints.png",
        help="Output figure path.",
    )
    return parser.parse_args()


def load_fp(fp_base: Path, comp: int, alpha_int: int) -> np.ndarray:
    base = fp_base / f"graphite_1500K_0262_{comp}pct" / f"alpha_{alpha_int:03d}"
    return np.concatenate([
        np.loadtxt(base / hist_name)[:, 1]
        for hist_name in HIST_FILES
    ])


def segment_bounds(fp_base: Path) -> tuple[list[int], int]:
    lengths = [
        len(np.loadtxt(
            fp_base
            / f"graphite_1500K_0262_{COMPOSITIONS[0]}pct"
            / f"alpha_{ALPHA_INTS[0]:03d}"
            / hist_name
        ))
        for hist_name in HIST_FILES
    ]
    bounds = [0] + list(np.cumsum(lengths))
    return bounds, bounds[-1]


def plot_figure(
    output: Path,
    *,
    fp_base: Path,
) -> None:
    fps = {
        (comp, alpha_int): load_fp(fp_base, comp, alpha_int)
        for comp in COMPOSITIONS
        for alpha_int in ALPHA_INTS
    }
    bounds, n_bins = segment_bounds(fp_base)
    x = np.arange(n_bins)

    cmap = plt.cm.viridis
    norm = Normalize(vmin=0.0, vmax=1.0)

    fig, axes = plt.subplots(5, 1, figsize=(3, 5), sharex=True)
    fig.subplots_adjust(left=0.22, right=0.78, top=0.96, bottom=0.11, hspace=0.65)

    for i, comp in enumerate(COMPOSITIONS):
        ax = axes[i]
        for alpha_int, alpha_val in zip(ALPHA_INTS, ALPHA_VALS):
            ax.plot(
                x, fps[(comp, alpha_int)],
                color=cmap(norm(alpha_val)), lw=0.9, alpha=0.92,
            )
        for b in bounds[1:-1]:
            ax.axvline(b, color="#aaaaaa", lw=0.7, ls="--", zorder=0)

        ax.set_title(f"{comp} % N", fontsize=10, pad=2, fontweight="bold")
        ax.set_ylabel(r"$P(d)$" if i == 2 else "", fontsize=10, labelpad=2)
        ax.set_ylim(0, 0.5)
        ax.tick_params(labelsize=10, length=3)
        ax.set_xlim(0, n_bins - 1)

    mid = [(bounds[j] + bounds[j + 1]) / 2 for j in range(3)]
    axes[-1].set_xticks(mid)
    axes[-1].set_xticklabels(BODY_LABELS, fontsize=10)

    sm = ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    subplot_h = (0.96 - 0.11) / (5 + 4 * 0.65)
    cbar_h = 3.0 * subplot_h
    cbar_bot = (0.96 + 0.11) / 2 - cbar_h / 2
    cax = fig.add_axes([0.80, cbar_bot, 0.05, cbar_h])
    cbar = fig.colorbar(sm, cax=cax)
    cbar.set_label(r"$\alpha$", fontsize=10, labelpad=3)
    cbar.set_ticks(ALPHA_VALS)
    cbar.ax.tick_params(labelsize=10)

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180, bbox_inches="tight", facecolor="white")
    print(f"Saved → {output}")


def main() -> None:
    args = parse_args()
    if not args.fingerprints_dir.is_dir():
        raise FileNotFoundError(
            f"Missing fingerprints directory: {args.fingerprints_dir}\n"
            "Run graphite element-switching workflows first."
        )
    plot_figure(args.output, fp_base=args.fingerprints_dir)


if __name__ == "__main__":
    main()
