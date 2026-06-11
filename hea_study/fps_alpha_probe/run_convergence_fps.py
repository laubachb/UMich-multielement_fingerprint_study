#!/usr/bin/env python3
"""
Run 5%-step HEA FPS and generate convergence figures.

  cd hea_study/fps_alpha_probe
  python run_convergence_fps.py
  python run_convergence_fps.py --skip-fps
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from convergence_vs_retention import run as run_convergence
from fingerprint_coverage import run as run_fingerprint_coverage
from probe_data import (
    DEFAULT_CONVERGENCE_RESULTS,
    HEA_DIR,
    RETENTIONS_5PCT,
    build_frame_composition_table,
    load_fps_selections,
)

SCRIPT_DIR = Path(__file__).resolve().parent
SAMPLING_SCRIPT = SCRIPT_DIR.parent / "sampling" / "run_fps_sampling.py"
OUTPUT_DIR = SCRIPT_DIR / "output"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sampling-results", type=Path, default=DEFAULT_CONVERGENCE_RESULTS)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--hea-root", type=Path, default=HEA_DIR)
    parser.add_argument("--replicates", type=int, default=10)
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
        print("HEA FPS convergence grid: 5%–95% retention, 5 α values")
        print(f"  output: {args.sampling_results}")
        if args.dry_run:
            print(" ".join(fps_cmd))
            return
        subprocess.run(fps_cmd, check=True)

    selections = load_fps_selections(args.sampling_results)
    frame_table = build_frame_composition_table()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    run_convergence(selections, frame_table, args.output_dir)
    run_fingerprint_coverage(selections, args.output_dir, hea_root=args.hea_root)

    figures_script = SCRIPT_DIR / "make_probe_figures.py"
    subprocess.run(
        [
            sys.executable,
            str(figures_script),
            "--output-dir",
            str(args.output_dir),
            "--hea-root",
            str(args.hea_root),
        ],
        check=True,
    )
    print(f"Done. {len(selections)} HEA FPS selections analyzed.")


if __name__ == "__main__":
    main()
