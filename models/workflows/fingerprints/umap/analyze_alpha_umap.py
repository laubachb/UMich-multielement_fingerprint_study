#!/usr/bin/env python3
"""
Alpha-sweep analysis and visualization for CN fingerprint UMAP embeddings.

Generates a panel of figures in ./figures/ for comparing how frames move through
latent space as ChIMES alpha blends composition-only → structure-only fingerprints.

Figures
-------
  distance_correlation_heatmap.png   Spearman rho of pairwise UMAP distances
  aligned_umap_panels.png            1×5 Procrustes-aligned UMAP (frame index)
  alpha_trajectories.png             Per-frame paths through alpha (aligned)
  alpha0_to_alpha1_arrows.png        Displacement vectors α=0 → α=1
  fingerprint_displacement_vs_alpha.png L2 distance in histogram space vs alpha
  embedding_path_length_umap.png     α=1 UMAP colored by total aligned path length
  pca_fingerprint_sweep.png          PCA of stacked fingerprints, colored by alpha
  frame_metrics.csv                  Per-frame scalar metrics for ranking

Usage
-----
  cd models/fingerprints/umap
  python analyze_alpha_umap.py
  python analyze_alpha_umap.py --recompute
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import pandas as pd
from scipy.linalg import orthogonal_procrustes
from scipy.spatial.distance import pdist
from scipy.stats import spearmanr
from sklearn.decomposition import PCA

from make_umap_degeneracy import ALPHAS, FINGERPRINTS_DIR, SCRIPT_DIR
from umap_data import ensure_umap_data

FIGURES_DIR = SCRIPT_DIR / "figures"

mpl.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

ALPHA_LABELS = ["0", "0.25", "0.50", "0.75", "1"]
REF_ALPHA = 1.00


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fingerprints-dir", type=Path, default=FINGERPRINTS_DIR)
    parser.add_argument("--figures-dir", type=Path, default=FIGURES_DIR)
    parser.add_argument("--recompute", action="store_true")
    parser.add_argument("--n-neighbors", type=int, default=15)
    parser.add_argument("--min-dist", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--highlight-trajectories",
        type=int,
        default=25,
        help="Number of highest-displacement trajectories to highlight.",
    )
    return parser.parse_args()


def procrustes_align(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Align source (n, 2) to target (n, 2) via similarity Procrustes (no scaling)."""
    src_mean = source.mean(axis=0)
    tgt_mean = target.mean(axis=0)
    src_c = source - src_mean
    tgt_c = target - tgt_mean
    if np.linalg.norm(src_c) < 1e-12:
        return np.broadcast_to(tgt_mean, source.shape).copy()
    rotation, _ = orthogonal_procrustes(src_c, tgt_c)
    return src_c @ rotation + tgt_mean


def align_embeddings_to_reference(
    emb: dict[float, np.ndarray],
    ref_alpha: float = REF_ALPHA,
) -> dict[float, np.ndarray]:
    ref = emb[ref_alpha]
    return {alpha: procrustes_align(emb[alpha], ref) for alpha in ALPHAS}


def pairwise_distance_correlation(emb: dict[float, np.ndarray]) -> np.ndarray:
    n = len(ALPHAS)
    corr = np.zeros((n, n))
    dists = {alpha: pdist(emb[alpha]) for alpha in ALPHAS}
    for i, ai in enumerate(ALPHAS):
        for j, aj in enumerate(ALPHAS):
            rho, _ = spearmanr(dists[ai], dists[aj])
            corr[i, j] = rho
    return corr


def embedding_path_lengths(aligned: dict[float, np.ndarray]) -> np.ndarray:
    """Total path length in aligned UMAP space across alpha steps."""
    n_frames = aligned[ALPHAS[0]].shape[0]
    lengths = np.zeros(n_frames)
    for i in range(1, len(ALPHAS)):
        step = np.linalg.norm(aligned[ALPHAS[i]] - aligned[ALPHAS[i - 1]], axis=1)
        lengths += step
    return lengths


def fingerprint_displacements(fp_raw: dict[float, np.ndarray]) -> pd.DataFrame:
    """Per-frame L2 distance from alpha=0 and from alpha=1 in histogram space."""
    rows = []
    ref0 = fp_raw[0.00]
    ref1 = fp_raw[1.00]
    for i, alpha in enumerate(ALPHAS):
        dist0 = np.linalg.norm(fp_raw[alpha] - ref0, axis=1)
        dist1 = np.linalg.norm(fp_raw[alpha] - ref1, axis=1)
        rows.append({
            "alpha": alpha,
            "dist_from_alpha0_mean": dist0.mean(),
            "dist_from_alpha0_median": np.median(dist0),
            "dist_from_alpha0_q25": np.percentile(dist0, 25),
            "dist_from_alpha0_q75": np.percentile(dist0, 75),
            "dist_from_alpha1_mean": dist1.mean(),
            "dist_from_alpha1_median": np.median(dist1),
            "dist_from_alpha1_q25": np.percentile(dist1, 25),
            "dist_from_alpha1_q75": np.percentile(dist1, 75),
        })
    return pd.DataFrame(rows)


def build_frame_metrics(
    frame_ids: np.ndarray,
    fp_raw: dict[float, np.ndarray],
    aligned: dict[float, np.ndarray],
) -> pd.DataFrame:
    path_len = embedding_path_lengths(aligned)
    alpha0_to_1_umap = np.linalg.norm(
        aligned[0.00] - aligned[1.00], axis=1
    )
    alpha0_to_1_fp = np.linalg.norm(fp_raw[0.00] - fp_raw[1.00], axis=1)
    nnz = {alpha: (fp_raw[alpha] != 0).sum(axis=1) for alpha in ALPHAS}

    return pd.DataFrame({
        "frame_id": frame_ids,
        "embedding_path_length": path_len,
        "umap_alpha0_to_alpha1": alpha0_to_1_umap,
        "fp_alpha0_to_alpha1": alpha0_to_1_fp,
        **{f"nnz_alpha_{alpha:.2f}": nnz[alpha] for alpha in ALPHAS},
    })


def plot_distance_correlation_heatmap(corr: np.ndarray, output: Path) -> None:
    fig, ax = plt.subplots(figsize=(4.5, 4))
    im = ax.imshow(corr, vmin=0, vmax=1, cmap="YlOrRd")
    ax.set_xticks(range(len(ALPHAS)), ALPHA_LABELS)
    ax.set_yticks(range(len(ALPHAS)), ALPHA_LABELS)
    ax.set_xlabel(r"$\alpha$")
    ax.set_ylabel(r"$\alpha$")
    ax.set_title("Spearman $\\rho$ of pairwise\nUMAP distances")
    for i in range(len(ALPHAS)):
        for j in range(len(ALPHAS)):
            ax.text(j, i, f"{corr[i, j]:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(output, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved → {output}")


def plot_aligned_panels(
    aligned: dict[float, np.ndarray],
    frame_ids: np.ndarray,
    output: Path,
) -> None:
    all_xy = np.vstack([aligned[alpha] for alpha in ALPHAS])
    xlim = (all_xy[:, 0].min(), all_xy[:, 0].max())
    ylim = (all_xy[:, 1].min(), all_xy[:, 1].max())
    pad_x = 0.05 * (xlim[1] - xlim[0] + 1e-9)
    pad_y = 0.05 * (ylim[1] - ylim[0] + 1e-9)
    xlim = (xlim[0] - pad_x, xlim[1] + pad_x)
    ylim = (ylim[0] - pad_y, ylim[1] + pad_y)
    norm = mpl.colors.Normalize(frame_ids.min(), frame_ids.max())

    xlabels = [
        r"UMAP 1 ($\alpha = 0$, composition only)",
        r"UMAP 1 ($\alpha = 0.25$)",
        r"UMAP 1 ($\alpha = 0.50$)",
        r"UMAP 1 ($\alpha = 0.75$)",
        r"UMAP 1 ($\alpha = 1$, structure only)",
    ]

    fig, axes = plt.subplots(1, 5, figsize=(14, 3.2), sharex=True, sharey=True)
    fig.subplots_adjust(wspace=0.12, top=0.95, bottom=0.22)
    for col, alpha in enumerate(ALPHAS):
        ax = axes[col]
        sc = ax.scatter(
            aligned[alpha][:, 0],
            aligned[alpha][:, 1],
            c=frame_ids,
            cmap="viridis",
            norm=norm,
            s=16,
            linewidths=0,
            alpha=0.85,
            rasterized=True,
        )
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xlabel(xlabels[col], fontsize=8)
    axes[0].set_ylabel("UMAP 2", fontsize=8)
    cbar = fig.colorbar(sc, ax=axes, fraction=0.025, pad=0.02)
    cbar.set_label("Frame index")
    fig.savefig(output, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved → {output}")


def plot_alpha_trajectories(
    aligned: dict[float, np.ndarray],
    frame_ids: np.ndarray,
    path_lengths: np.ndarray,
    n_highlight: int,
    output: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(6, 5))
    norm = mpl.colors.Normalize(frame_ids.min(), frame_ids.max())
    cmap = plt.get_cmap("viridis")

    order = np.argsort(path_lengths)
    background = order[: max(0, len(order) - n_highlight)]
    highlight = order[-n_highlight:]

    for idx in background:
        pts = np.array([aligned[alpha][idx] for alpha in ALPHAS])
        ax.plot(pts[:, 0], pts[:, 1], color="0.8", lw=0.4, alpha=0.35, zorder=1)

    for idx in highlight:
        pts = np.array([aligned[alpha][idx] for alpha in ALPHAS])
        color = cmap(norm(frame_ids[idx]))
        ax.plot(pts[:, 0], pts[:, 1], color=color, lw=1.2, alpha=0.9, zorder=2)
        ax.scatter(
            pts[:, 0], pts[:, 1],
            c=[color], s=22, zorder=3, linewidths=0,
        )

    ax.set_xlabel("UMAP 1 (aligned to $\\alpha=1$)")
    ax.set_ylabel("UMAP 2 (aligned to $\\alpha=1$)")
    ax.set_title(
        f"Frame trajectories through $\\alpha$\n"
        f"({n_highlight} highest path-length frames highlighted)"
    )
    sm = mpl.cm.ScalarMappable(norm=norm, cmap=cmap)
    fig.colorbar(sm, ax=ax, label="Frame index", fraction=0.046)
    fig.tight_layout()
    fig.savefig(output, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved → {output}")


def plot_alpha0_to_alpha1_arrows(
    aligned: dict[float, np.ndarray],
    frame_ids: np.ndarray,
    path_lengths: np.ndarray,
    output: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(6, 5))
    start = aligned[0.00]
    end = aligned[1.00]
    disp = np.linalg.norm(end - start, axis=1)
    norm = mpl.colors.Normalize(disp.min(), disp.max())

    ax.scatter(
        end[:, 0], end[:, 1],
        c=frame_ids, cmap="viridis",
        s=14, alpha=0.35, linewidths=0, rasterized=True, zorder=1,
    )
    quiv = ax.quiver(
        start[:, 0], start[:, 1],
        end[:, 0] - start[:, 0],
        end[:, 1] - start[:, 1],
        disp, cmap="magma", norm=norm,
        angles="xy", scale_units="xy", scale=1,
        width=0.002, alpha=0.75, zorder=2,
    )
    ax.set_xlabel("UMAP 1 (aligned to $\\alpha=1$)")
    ax.set_ylabel("UMAP 2 (aligned to $\\alpha=1$)")
    ax.set_title("Displacement $\\alpha=0 \\rightarrow \\alpha=1$ per frame")
    fig.colorbar(quiv, ax=ax, label="UMAP displacement", fraction=0.046)
    fig.tight_layout()
    fig.savefig(output, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved → {output}")


def plot_fingerprint_displacement_vs_alpha(
    fp_raw: dict[float, np.ndarray],
    summary: pd.DataFrame,
    output: Path,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.5))

    x = summary["alpha"]
    panel_info = [
        (
            "dist_from_alpha0",
            r"$\alpha$ (composition $\rightarrow$ structure)",
            r"L2 distance from $\alpha = 0$",
        ),
        (
            "dist_from_alpha1",
            r"$\alpha$ (composition $\rightarrow$ structure)",
            r"L2 distance from $\alpha = 1$",
        ),
    ]
    for ax, (prefix, xlabel, ylabel) in zip(axes, panel_info):
        ax.fill_between(
            x,
            summary[f"{prefix}_q25"],
            summary[f"{prefix}_q75"],
            alpha=0.25, color="#4393c3",
        )
        ax.plot(x, summary[f"{prefix}_median"], "o-", color="#2166ac", lw=1.5)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_xticks(ALPHAS, ALPHA_LABELS)
    fig.tight_layout()
    fig.savefig(output, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved → {output}")


def plot_embedding_path_length_umap(
    aligned: dict[float, np.ndarray],
    path_lengths: np.ndarray,
    output: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    pts = aligned[REF_ALPHA]
    sc = ax.scatter(
        pts[:, 0], pts[:, 1],
        c=path_lengths, cmap="inferno",
        s=22, linewidths=0, alpha=0.9, rasterized=True,
    )
    ax.set_xlabel("UMAP 1 (aligned, $\\alpha=1$)")
    ax.set_ylabel("UMAP 2 (aligned, $\\alpha=1$)")
    ax.set_title("Total aligned UMAP path length\nacross $\\alpha=0\\rightarrow1$")
    fig.colorbar(sc, ax=ax, label="Path length", fraction=0.046)
    fig.tight_layout()
    fig.savefig(output, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved → {output}")


def plot_pca_fingerprint_sweep(
    fp_raw: dict[float, np.ndarray],
    frame_ids: np.ndarray,
    output: Path,
) -> None:
    blocks = []
    alpha_labels = []
    frame_labels = []
    for alpha in ALPHAS:
        blocks.append(fp_raw[alpha])
        alpha_labels.extend([alpha] * len(frame_ids))
        frame_labels.extend(frame_ids.tolist())
    matrix = np.vstack(blocks)
    alpha_labels = np.array(alpha_labels)
    frame_labels = np.array(frame_labels)

    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(matrix)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    ax = axes[0]
    for alpha in ALPHAS:
        mask = alpha_labels == alpha
        ax.scatter(
            coords[mask, 0], coords[mask, 1],
            s=12, alpha=0.55, label=rf"$\alpha={alpha:g}$",
            rasterized=True,
        )
    ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)")
    ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)")
    ax.set_title("PCA of stacked fingerprints\n(colored by $\\alpha$)")
    ax.legend(fontsize=7, markerscale=1.5, framealpha=0.9)

    ax = axes[1]
    sc = ax.scatter(
        coords[:, 0], coords[:, 1],
        c=frame_labels, cmap="viridis",
        s=12, alpha=0.65, linewidths=0, rasterized=True,
    )
    ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)")
    ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)")
    ax.set_title("Same PCA (colored by frame index)")
    fig.colorbar(sc, ax=ax, label="Frame index", fraction=0.046)

    fig.tight_layout()
    fig.savefig(output, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved → {output}")


def main() -> None:
    args = parse_args()
    args.figures_dir.mkdir(parents=True, exist_ok=True)

    data = ensure_umap_data(
        fingerprints_dir=args.fingerprints_dir,
        recompute=args.recompute,
        n_neighbors=args.n_neighbors,
        min_dist=args.min_dist,
        seed=args.seed,
    )

    frame_ids = data["frame_ids"]
    fp_raw = data["fp_raw"]
    emb = data["emb"]

    aligned = align_embeddings_to_reference(emb)
    corr = pairwise_distance_correlation(emb)
    path_lengths = embedding_path_lengths(aligned)
    disp_summary = fingerprint_displacements(fp_raw)
    metrics = build_frame_metrics(frame_ids, fp_raw, aligned)

    metrics_path = args.figures_dir / "frame_metrics.csv"
    metrics.sort_values("embedding_path_length", ascending=False).to_csv(
        metrics_path, index=False
    )
    print(f"Saved → {metrics_path}")

    plot_distance_correlation_heatmap(
        corr, args.figures_dir / "distance_correlation_heatmap.png"
    )
    plot_aligned_panels(
        aligned, frame_ids, args.figures_dir / "aligned_umap_panels.png"
    )
    plot_alpha_trajectories(
        aligned,
        frame_ids,
        path_lengths,
        args.highlight_trajectories,
        args.figures_dir / "alpha_trajectories.png",
    )
    plot_alpha0_to_alpha1_arrows(
        aligned,
        frame_ids,
        path_lengths,
        args.figures_dir / "alpha0_to_alpha1_arrows.png",
    )
    plot_fingerprint_displacement_vs_alpha(
        fp_raw,
        disp_summary,
        args.figures_dir / "fingerprint_displacement_vs_alpha.png",
    )
    plot_embedding_path_length_umap(
        aligned,
        path_lengths,
        args.figures_dir / "embedding_path_length_umap.png",
    )
    plot_pca_fingerprint_sweep(
        fp_raw,
        frame_ids,
        args.figures_dir / "pca_fingerprint_sweep.png",
    )

    print(f"\nAll figures written to {args.figures_dir.resolve()}")


if __name__ == "__main__":
    main()
