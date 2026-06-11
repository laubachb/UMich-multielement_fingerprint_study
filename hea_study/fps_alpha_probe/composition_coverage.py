"""Composition-class coverage of HEA FPS training subsets."""

from __future__ import annotations

import numpy as np
import pandas as pd

from probe_data import COMPOSITION_ORDER


def counts_for_selection(
    frame_ids: list[int],
    frame_table: pd.DataFrame,
    composition_order: tuple[str, ...] = COMPOSITION_ORDER,
) -> pd.Series:
    sub = frame_table[frame_table["frame_id"].isin(frame_ids)]
    counts = sub.groupby("composition_class").size()
    return pd.Series(
        {c: int(counts.get(c, 0)) for c in composition_order},
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
