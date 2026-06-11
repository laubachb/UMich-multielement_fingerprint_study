"""Shared loaders for FPS α probe analyses."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
MULTIELEMENT_ROOT = SCRIPT_DIR.parents[1]
DEFAULT_SAMPLING_RESULTS = SCRIPT_DIR.parent / "sampling" / "results"
DEFAULT_CONVERGENCE_RESULTS = (
    SCRIPT_DIR.parent / "sampling" / "results_convergence_5pct"
)
DEFAULT_STATEPOINTS_JSON = SCRIPT_DIR.parent / "statepoint_eval" / "statepoints.json"

ALPHAS = (0.0, 0.25, 0.5, 0.75, 1.0)
# 5%, 10%, …, 95% — CN convergence grid (no model training)
RETENTIONS_5PCT = tuple(i / 100 for i in range(5, 100, 5))
FRAME_RE = re.compile(r"^frame_(\d+)$")


def load_statepoints(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return sorted(data["statepoints"], key=lambda sp: sp["full_dft_frame"])


def build_frame_statepoint_table(statepoints: list[dict]) -> pd.DataFrame:
    """Map 1-based full_dft frame IDs to evaluation statepoint metadata."""
    rows: list[dict] = []
    for i, sp in enumerate(statepoints):
        start = int(sp["full_dft_frame"])
        end = (
            int(statepoints[i + 1]["full_dft_frame"]) - 1
            if i + 1 < len(statepoints)
            else 10_000
        )
        for frame_id in range(start, end + 1):
            rows.append(
                {
                    "frame_id": frame_id,
                    "statepoint_id": sp["id"],
                    "case": sp["case"],
                    "n_pct": sp["n_pct"],
                    "density_gcc": sp["density_gcc"],
                    "temperature_k": sp["temperature_k"],
                }
            )
    return pd.DataFrame(rows)


def load_fps_selections(
    results_root: Path,
    *,
    retention_fractions: tuple[float, ...] | None = None,
) -> pd.DataFrame:
    """One row per (fps_alpha, retention, replicate) with selected frame IDs."""
    rows: list[dict] = []
    for meta_path in sorted(results_root.glob("alpha_*/*/replicate_*/metadata.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        retention = float(meta["retention_fraction"])
        if retention_fractions is not None and retention not in retention_fractions:
            continue
        frame_ids = [int(x) for x in meta["selected_frame_ids"]]
        rows.append(
            {
                "fps_alpha": float(meta["alpha"]),
                "retention_fraction": retention,
                "retention_pct": int(round(retention * 100)),
                "replicate": int(meta["replicate"]),
                "seed": int(meta["seed"]),
                "n_selected": int(meta["n_selected"]),
                "frame_ids": frame_ids,
                "sampling_path": str(meta_path.parent.relative_to(results_root)),
            }
        )
    if not rows:
        raise FileNotFoundError(f"No FPS metadata under {results_root}")
    return pd.DataFrame(rows)


def alpha_label(alpha: float) -> str:
    return f"{alpha:.2f}".rstrip("0").rstrip(".") if alpha % 1 else f"{int(alpha)}"
