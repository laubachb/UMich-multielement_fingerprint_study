"""HEA loaders for FPS α probe analyses."""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
HEA_DIR = SCRIPT_DIR.parent
DEFAULT_CONVERGENCE_RESULTS = HEA_DIR / "sampling" / "results_convergence_5pct"
LABEL_DIR = HEA_DIR / "alpha_0-histograms"

ALPHAS = (0.0, 0.25, 0.5, 0.75, 1.0)
ALPHA_DIR_NAMES = {
    0.0: "alpha_0-histograms",
    0.25: "alpha_025-histograms",
    0.5: "alpha_050-histograms",
    0.75: "alpha_075-histograms",
    1.0: "alpha_1-histograms",
}
HIST_FILES = (
    "0-0.2b_clu-s.hist",
    "0-0.3b_clu-s.hist",
    "0-0.4b_clu-s.hist",
)
RETENTIONS_5PCT = tuple(i / 100 for i in range(5, 100, 5))
FRAME_RE = re.compile(r"^frame_(\d+)$")
CLUSTER_FILE = "0.all-2b-clusters.txt"

COMPOSITION_ORDER = ("y_only", "mg_only", "mixed")
COMPOSITION_LABELS = {
    "y_only": "Y only",
    "mg_only": "Mg only",
    "mixed": "Mixed",
}


def alpha_label(alpha: float) -> str:
    return f"{alpha:.2f}".rstrip("0").rstrip(".") if alpha % 1 else f"{int(alpha)}"


def frame_composition_label(frame: str, label_dir: Path) -> int:
    data = np.loadtxt(label_dir / frame / CLUSTER_FILE)
    if data.ndim == 1:
        data = data[np.newaxis, :]
    unique = set(data[:, 1:].astype(int).flatten())
    if unique == {0}:
        return 0
    if unique == {1}:
        return 1
    return 2


def alpha_dirs_from_root(hea_root: Path = HEA_DIR) -> dict[float, Path]:
    return {a: hea_root / name for a, name in ALPHA_DIR_NAMES.items()}


def get_frame_list(base_dir: Path) -> list[str]:
    return sorted(
        [d.name for d in base_dir.iterdir() if d.is_dir() and FRAME_RE.match(d.name)],
        key=lambda x: int(FRAME_RE.match(x).group(1)),
    )


def frame_ok(frame: str, label_dir: Path, alpha_dirs: dict[float, Path]) -> bool:
    if not (label_dir / frame / CLUSTER_FILE).is_file():
        return False
    for alpha_dir in alpha_dirs.values():
        for hist_name in HIST_FILES:
            hist_path = alpha_dir / frame / hist_name
            if not hist_path.is_file():
                return False
            try:
                if np.isnan(np.loadtxt(hist_path)).any():
                    return False
            except Exception:
                return False
    return True


def discover_valid_frames(hea_root: Path = HEA_DIR) -> list[str]:
    alpha_dirs = alpha_dirs_from_root(hea_root)
    label_dir = alpha_dirs[0.0]
    return [f for f in get_frame_list(label_dir) if frame_ok(f, label_dir, alpha_dirs)]


def load_fp(alpha_dir: Path, frame: str) -> np.ndarray:
    fdir = alpha_dir / frame
    return np.concatenate([np.loadtxt(fdir / h)[:, 1] for h in HIST_FILES])


def drop_zero_cols(arr: np.ndarray) -> np.ndarray:
    return arr[:, arr.any(axis=0)]


def load_fingerprint_matrices(
    hea_root: Path = HEA_DIR,
) -> tuple[list[int], dict[float, np.ndarray]]:
    """Return aligned frame_ids and per-α fingerprint matrices (n_frames × n_feat)."""
    alpha_dirs = alpha_dirs_from_root(hea_root)
    frame_dirs = discover_valid_frames(hea_root)
    frame_ids = [int(f.split("_")[1]) for f in frame_dirs]
    matrices: dict[float, np.ndarray] = {}
    for alpha in ALPHAS:
        raw = np.array([load_fp(alpha_dirs[alpha], f) for f in frame_dirs])
        matrices[alpha] = drop_zero_cols(raw)
    return frame_ids, matrices


def build_frame_composition_table(label_dir: Path = LABEL_DIR) -> pd.DataFrame:
    rows: list[dict] = []
    for d in sorted(label_dir.iterdir(), key=lambda p: int(FRAME_RE.match(p.name).group(1)) if FRAME_RE.match(p.name) else 0):
        if not d.is_dir() or not FRAME_RE.match(d.name):
            continue
        if not (d / CLUSTER_FILE).is_file():
            continue
        fid = int(FRAME_RE.match(d.name).group(1))
        comp_id = frame_composition_label(d.name, label_dir)
        comp_key = COMPOSITION_ORDER[comp_id]
        rows.append(
            {
                "frame_id": fid,
                "frame": d.name,
                "composition_id": comp_id,
                "composition_class": comp_key,
                "composition_label": COMPOSITION_LABELS[comp_key],
            }
        )
    return pd.DataFrame(rows)


def load_fps_selections(
    results_root: Path,
    *,
    retention_fractions: tuple[float, ...] | None = None,
) -> pd.DataFrame:
    rows: list[dict] = []
    for meta_path in sorted(results_root.glob("alpha_*/*/replicate_*/metadata.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        retention = float(meta["retention_fraction"])
        if retention_fractions is not None and retention not in retention_fractions:
            continue
        rows.append(
            {
                "fps_alpha": float(meta["alpha"]),
                "retention_fraction": retention,
                "retention_pct": int(round(retention * 100)),
                "replicate": int(meta["replicate"]),
                "seed": int(meta["seed"]),
                "n_selected": int(meta["n_selected"]),
                "frame_ids": [int(x) for x in meta["selected_frame_ids"]],
                "sampling_path": str(meta_path.parent.relative_to(results_root)),
            }
        )
    if not rows:
        raise FileNotFoundError(f"No HEA FPS metadata under {results_root}")
    return pd.DataFrame(rows)
