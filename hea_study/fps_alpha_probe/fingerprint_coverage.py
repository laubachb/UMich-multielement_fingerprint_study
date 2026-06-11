#!/usr/bin/env python3
"""
Fingerprint-space coverage and similarity of HEA FPS subsets vs pruning level.

Without thermodynamic statepoints, we measure how well each pruned training set
represents the full corpus in the α-space used for FPS:

  - mean / max hold-out NN distance (normalized by corpus scale)
  - mean cosine similarity to nearest selected frame
  - coverage_fraction: share of corpus within a local neighborhood radius
  - selected-set internal spread (diversity of the training subset)

Outputs
-------
  output/convergence/fingerprint_coverage_long.csv
  output/convergence/fingerprint_coverage_vs_retention.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

from probe_data import (
    DEFAULT_CONVERGENCE_RESULTS,
    HEA_DIR,
    load_fingerprint_matrices,
    load_fps_selections,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "output"

COVERAGE_RADIUS_PERCENTILE = 10.0


def _corpus_scale(vectors: np.ndarray) -> tuple[float, float]:
    """Robust distance scale from 1-NN distances (handles duplicate/degenerate frames)."""
    n = vectors.shape[0]
    if n < 2:
        return 1.0, 1.0
    nn = NearestNeighbors(n_neighbors=2, metric="euclidean")
    nn.fit(vectors)
    dists, _ = nn.kneighbors(vectors)
    nn1 = dists[:, 1]
    nn1_nz = nn1[nn1 > 1e-10]
    if nn1_nz.size == 0:
        return 1.0, 0.0
    median_dist = float(np.median(nn1_nz))
    ref_radius = float(np.percentile(nn1_nz, COVERAGE_RADIUS_PERCENTILE))
    return max(median_dist, 1e-12), ref_radius


def _l2_normalize(rows: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(rows, axis=1, keepdims=True)
    norms = np.where(norms > 0, norms, 1.0)
    return rows / norms


def metrics_for_selection(
    unit_vectors: np.ndarray,
    selected_indices: list[int],
    *,
    corpus_median_dist: float,
    ref_radius: float,
) -> dict[str, float]:
    k = len(selected_indices)
    if k == 0:
        return {
            "mean_nn_dist_norm": np.nan,
            "max_nn_dist_norm": np.nan,
            "p95_nn_dist_norm": np.nan,
            "mean_nn_cosine_sim": np.nan,
            "coverage_fraction": 0.0,
            "selected_spread_norm": np.nan,
        }

    selected = unit_vectors[selected_indices]
    nn = NearestNeighbors(n_neighbors=1, metric="euclidean")
    nn.fit(selected)
    nn_dists, _ = nn.kneighbors(unit_vectors)
    nn_dists = nn_dists[:, 0]

    cos_sims = 1.0 - 0.5 * np.square(nn_dists)

    if k > 1:
        # Sample pairs when k is large (high retention) to keep runtime bounded.
        n_pairs = k * (k - 1) // 2
        if n_pairs <= 10_000:
            sel_dists = np.linalg.norm(
                selected[:, None, :] - selected[None, :, :], axis=2
            )
            triu = sel_dists[np.triu_indices(k, k=1)]
        else:
            rng = np.random.default_rng(0)
            idx_i = rng.integers(0, k, size=10_000)
            idx_j = rng.integers(0, k, size=10_000)
            mask = idx_i != idx_j
            triu = np.linalg.norm(selected[idx_i[mask]] - selected[idx_j[mask]], axis=1)
        selected_spread = float(np.mean(triu)) if triu.size else 0.0
    else:
        selected_spread = 0.0

    return {
        "mean_nn_dist_norm": float(np.mean(nn_dists) / corpus_median_dist),
        "max_nn_dist_norm": float(np.max(nn_dists) / corpus_median_dist),
        "p95_nn_dist_norm": float(np.percentile(nn_dists, 95) / corpus_median_dist),
        "mean_nn_cosine_sim": float(np.mean(cos_sims)),
        "coverage_fraction": float(np.mean(nn_dists <= ref_radius)),
        "selected_spread_norm": float(selected_spread / corpus_median_dist),
    }


def fingerprint_coverage_table(
    selections: pd.DataFrame,
    frame_ids: list[int],
    fingerprints: dict[float, np.ndarray],
) -> pd.DataFrame:
    id_to_idx = {fid: i for i, fid in enumerate(frame_ids)}
    unit_fingerprints = {a: _l2_normalize(v) for a, v in fingerprints.items()}
    corpus_scales: dict[float, tuple[float, float]] = {}
    for alpha, vectors in unit_fingerprints.items():
        corpus_scales[alpha] = _corpus_scale(vectors)

    rows: list[dict] = []
    for row in selections.itertuples(index=False):
        alpha = float(row.fps_alpha)
        unit_vectors = unit_fingerprints[alpha]
        corpus_median, ref_radius = corpus_scales[alpha]
        selected_indices = [id_to_idx[fid] for fid in row.frame_ids if fid in id_to_idx]
        metrics = metrics_for_selection(
            unit_vectors,
            selected_indices,
            corpus_median_dist=corpus_median,
            ref_radius=ref_radius,
        )
        rows.append(
            {
                "fps_alpha": alpha,
                "retention_fraction": row.retention_fraction,
                "retention_pct": row.retention_pct,
                "replicate": row.replicate,
                "n_selected": row.n_selected,
                "corpus_median_dist": corpus_median,
                "ref_radius": ref_radius,
                **metrics,
            }
        )
    return pd.DataFrame(rows)


def aggregate_fingerprint_coverage(long_df: pd.DataFrame) -> pd.DataFrame:
    metric_cols = [
        "mean_nn_dist_norm",
        "max_nn_dist_norm",
        "p95_nn_dist_norm",
        "mean_nn_cosine_sim",
        "coverage_fraction",
        "selected_spread_norm",
    ]
    agg = (
        long_df.groupby(["fps_alpha", "retention_fraction", "retention_pct"])[metric_cols]
        .agg(["mean", "std"])
        .reset_index()
        .sort_values(["fps_alpha", "retention_pct"])
    )
    agg.columns = [f"{a}_{b}" if b else a for a, b in agg.columns.to_flat_index()]
    return agg


def run(
    selections: pd.DataFrame,
    output_dir: Path,
    *,
    hea_root: Path = HEA_DIR,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame_ids, fingerprints = load_fingerprint_matrices(hea_root)
    long_df = fingerprint_coverage_table(selections, frame_ids, fingerprints)
    agg_df = aggregate_fingerprint_coverage(long_df)

    conv_dir = output_dir / "convergence"
    conv_dir.mkdir(parents=True, exist_ok=True)
    long_df.to_csv(conv_dir / "fingerprint_coverage_long.csv", index=False)
    agg_df.to_csv(conv_dir / "fingerprint_coverage_vs_retention.csv", index=False)
    return long_df, agg_df


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sampling-results", type=Path, default=DEFAULT_CONVERGENCE_RESULTS)
    parser.add_argument("--hea-root", type=Path, default=HEA_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selections = load_fps_selections(args.sampling_results)
    long_df, agg_df = run(selections, args.output_dir, hea_root=args.hea_root)
    print(f"Wrote fingerprint coverage for {len(long_df)} selections to {args.output_dir / 'convergence'}")
    print(f"  corpus frames: {agg_df['fps_alpha'].nunique()} α values × {len(agg_df)} retention bins")


if __name__ == "__main__":
    main()
