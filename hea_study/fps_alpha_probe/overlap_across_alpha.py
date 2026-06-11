"""Jaccard overlap helpers for HEA FPS α probe."""

from __future__ import annotations

import numpy as np
import pandas as pd

from probe_data import alpha_label


def jaccard(a: set[int], b: set[int]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def matrix_for_group(group: pd.DataFrame, alphas: tuple[float, ...]) -> pd.DataFrame:
    sets_by_alpha = {
        row.fps_alpha: set(row.frame_ids) for row in group.itertuples(index=False)
    }
    labels = [alpha_label(a) for a in alphas]
    mat = np.zeros((len(alphas), len(alphas)))
    for i, ai in enumerate(alphas):
        for j, aj in enumerate(alphas):
            mat[i, j] = jaccard(sets_by_alpha.get(ai, set()), sets_by_alpha.get(aj, set()))
    return pd.DataFrame(mat, index=labels, columns=labels)
