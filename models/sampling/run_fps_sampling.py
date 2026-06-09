#!/usr/bin/env python3
"""
Farthest-point sampling (FPS) on CN fingerprint vectors across ChIMES alpha spaces.

For each alpha value (0, 0.25, 0.50, 0.75, 1.0), selects diverse frame subsets
at 1%, 10%, and 50% retention using Euclidean distance in histogram space.
Multiple stochastic replicates differ only in the random initial frame.

Output layout
-------------
results/
  manifest.json
  summary.csv
  alpha_0.00/
    pct_001/
      replicate_00/
        selected_frames.txt   # FPS selection order (one frame per line)
        metadata.json
      replicate_01/
      ...
    pct_010/
    pct_050/
  alpha_0.25/
  ...

Usage
-----
  cd models/sampling
  python run_fps_sampling.py
  python run_fps_sampling.py --replicates 3 --seed 42
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
UMAP_DIR = SCRIPT_DIR.parent / "workflows" / "fingerprints" / "umap"
sys.path.insert(0, str(UMAP_DIR))

from make_umap_degeneracy import (  # noqa: E402
    ALPHAS,
    ALPHA_DIRS,
    discover_frames,
    drop_zero_cols,
    load_fp,
)

DEFAULT_RETENTIONS = (0.01, 0.10, 0.50)
DEFAULT_REPLICATES = 3
RESULTS_DIR = SCRIPT_DIR / "results"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fingerprints-dir",
        type=Path,
        default=ALPHA_DIRS[0.00].parent,
        help="Directory containing a*_fingerprints folders.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=RESULTS_DIR,
        help="Root directory for FPS outputs.",
    )
    parser.add_argument(
        "--retentions",
        type=float,
        nargs="+",
        default=list(DEFAULT_RETENTIONS),
        help="Retention fractions in (0, 1], e.g. 0.01 0.10 0.50.",
    )
    parser.add_argument(
        "--replicates",
        type=int,
        default=DEFAULT_REPLICATES,
        help="Number of independent FPS replicates per (alpha, retention).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Base RNG seed; replicate r uses seed + r.",
    )
    return parser.parse_args()


def alpha_dirs_from_root(fingerprints_dir: Path) -> dict[float, Path]:
    return {
        alpha: fingerprints_dir / path.name
        for alpha, path in ALPHA_DIRS.items()
    }


def retention_count(n_frames: int, fraction: float) -> int:
    if not 0 < fraction <= 1:
        raise ValueError(f"Retention must be in (0, 1]; got {fraction}")
    return max(1, int(round(n_frames * fraction)))


def pct_label(fraction: float) -> str:
    return f"pct_{int(round(fraction * 100)):03d}"


def alpha_label(alpha: float) -> str:
    return f"alpha_{alpha:.2f}"


def farthest_point_sampling(
    vectors: np.ndarray,
    k: int,
    rng: np.random.Generator,
) -> list[int]:
    """Greedy FPS in Euclidean space; returns indices in selection order."""
    n = vectors.shape[0]
    k = min(k, n)
    if k == 1:
        return [int(rng.integers(0, n))]

    start = int(rng.integers(0, n))
    selected = [start]
    min_dists = np.linalg.norm(vectors - vectors[start], axis=1)

    for _ in range(1, k):
        farthest = int(np.argmax(min_dists))
        selected.append(farthest)
        min_dists = np.minimum(
            min_dists,
            np.linalg.norm(vectors - vectors[farthest], axis=1),
        )

    return selected


def write_replicate(
    out_dir: Path,
    *,
    frame_dirs: list[str],
    selected_indices: list[int],
    alpha: float,
    retention: float,
    replicate: int,
    seed: int,
    fingerprint_shape: tuple[int, int],
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    selected_frames = [frame_dirs[i] for i in selected_indices]

    frames_path = out_dir / "selected_frames.txt"
    frames_path.write_text("\n".join(selected_frames) + "\n", encoding="utf-8")

    metadata = {
        "alpha": alpha,
        "retention_fraction": retention,
        "n_total_frames": len(frame_dirs),
        "n_selected": len(selected_frames),
        "replicate": replicate,
        "seed": seed,
        "fingerprint_shape": list(fingerprint_shape),
        "selected_frame_ids": [int(f.split("_")[1]) for f in selected_frames],
        "selected_indices": selected_indices,
    }
    meta_path = out_dir / "metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    return {
        "alpha": alpha,
        "retention_fraction": retention,
        "retention_pct": int(round(retention * 100)),
        "replicate": replicate,
        "seed": seed,
        "n_total_frames": len(frame_dirs),
        "n_selected": len(selected_frames),
        "output_dir": str(out_dir.relative_to(out_dir.parents[2])),
        "selected_frames": selected_frames,
    }


def main() -> None:
    args = parse_args()
    alpha_dirs = alpha_dirs_from_root(args.fingerprints_dir)

    for path in alpha_dirs.values():
        if not path.is_dir():
            raise FileNotFoundError(f"Missing alpha directory: {path}")

    frame_dirs = discover_frames(alpha_dirs)
    if not frame_dirs:
        raise RuntimeError("No valid frames discovered.")
    n_frames = len(frame_dirs)
    print(f"Using {n_frames} frames.")

    fingerprints: dict[float, np.ndarray] = {}
    for alpha in ALPHAS:
        raw = np.array([load_fp(alpha_dirs[alpha], frame) for frame in frame_dirs])
        fingerprints[alpha] = drop_zero_cols(raw)
        print(f"alpha={alpha:.2f}: fingerprint shape {fingerprints[alpha].shape}")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    summary_rows: list[dict] = []
    manifest = {
        "n_frames": n_frames,
        "frame_dirs": frame_dirs,
        "alphas": ALPHAS,
        "retentions": args.retentions,
        "replicates": args.replicates,
        "base_seed": args.seed,
        "runs": [],
    }

    print(f"\nFPS sampling: {n_frames} frames")
    print(f"Retentions: {[f'{r * 100:g}%' for r in args.retentions]}")
    print(f"Replicates: {args.replicates}\n")

    for alpha in ALPHAS:
        vectors = fingerprints[alpha]
        alpha_out = args.output_dir / alpha_label(alpha)

        for retention in args.retentions:
            k = retention_count(n_frames, retention)
            pct_dir = alpha_out / pct_label(retention)

            print(f"alpha={alpha:.2f}  retention={retention * 100:g}%  k={k}")

            for replicate in range(args.replicates):
                seed = args.seed + replicate
                rng = np.random.default_rng(seed)
                selected_indices = farthest_point_sampling(vectors, k, rng)

                rep_dir = pct_dir / f"replicate_{replicate:02d}"
                row = write_replicate(
                    rep_dir,
                    frame_dirs=frame_dirs,
                    selected_indices=selected_indices,
                    alpha=alpha,
                    retention=retention,
                    replicate=replicate,
                    seed=seed,
                    fingerprint_shape=vectors.shape,
                )
                summary_rows.append(
                    {
                        "alpha": alpha,
                        "retention_fraction": retention,
                        "retention_pct": row["retention_pct"],
                        "replicate": replicate,
                        "seed": seed,
                        "n_total_frames": n_frames,
                        "n_selected": k,
                        "output_dir": str(rep_dir.relative_to(args.output_dir)),
                    }
                )
                manifest["runs"].append(
                    {
                        "alpha": alpha,
                        "retention_fraction": retention,
                        "replicate": replicate,
                        "seed": seed,
                        "n_selected": k,
                        "path": str(rep_dir.relative_to(args.output_dir)),
                    }
                )

    summary_path = args.output_dir / "summary.csv"
    pd.DataFrame(summary_rows).to_csv(summary_path, index=False)

    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"\nWrote {len(summary_rows)} replicate sets to {args.output_dir}")
    print(f"  summary  → {summary_path}")
    print(f"  manifest → {manifest_path}")


if __name__ == "__main__":
    main()
