#!/usr/bin/env python3
"""
Run 5%-step FPS on the CN corpus and convergence diagnostics (no model training).

  cd models/fps_alpha_probe
  python run_convergence_fps.py
  python run_convergence_fps.py --skip-fps    # analyze existing results only
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from convergence_vs_retention import run as run_convergence
from probe_data import (
    DEFAULT_CONVERGENCE_RESULTS,
    DEFAULT_STATEPOINTS_JSON,
    RETENTIONS_5PCT,
    build_frame_statepoint_table,
    load_fps_selections,
    load_statepoints,
)

SCRIPT_DIR = Path(__file__).resolve().parent
SAMPLING_SCRIPT = SCRIPT_DIR.parent / "sampling" / "run_fps_sampling.py"
OUTPUT_DIR = SCRIPT_DIR / "output"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sampling-results",
        type=Path,
        default=DEFAULT_CONVERGENCE_RESULTS,
    )
    parser.add_argument(
        "--statepoints-json",
        type=Path,
        default=DEFAULT_STATEPOINTS_JSON,
    )
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument(
        "--replicates",
        type=int,
        default=10,
        help="FPS replicates per (α, retention).",
    )
    parser.add_argument("--skip-fps", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    fps_cmd = [
        sys.executable,
        str(SAMPLING_SCRIPT),
        "--output-dir",
        str(args.sampling_results),
        "--retentions",
        *[str(r) for r in RETENTIONS_5PCT],
        "--replicates",
        str(args.replicates),
    ]

    if not args.skip_fps:
        print("CN FPS convergence grid: 5%–95% retention, 5 α values")
        print(f"  output: {args.sampling_results}")
        print(f"  retentions: {[int(r * 100) for r in RETENTIONS_5PCT]}")
        if args.dry_run:
            print(" ".join(fps_cmd))
            return
        subprocess.run(fps_cmd, check=True)

    selections = load_fps_selections(args.sampling_results)
    statepoints = load_statepoints(args.statepoints_json)
    frame_table = build_frame_statepoint_table(statepoints)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    run_convergence(selections, frame_table, args.output_dir)

    figures_script = SCRIPT_DIR / "make_probe_figures.py"
    if figures_script.is_file():
        subprocess.run(
            [sys.executable, str(figures_script), "--output-dir", str(args.output_dir)],
            check=True,
        )

    print(f"Done. {len(selections)} FPS selections analyzed.")


if __name__ == "__main__":
    main()
