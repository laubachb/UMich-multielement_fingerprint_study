#!/usr/bin/env python3
"""
Prepare ChIMES LSQ run directories for FPS-pruned CN training subsets.

Reads frame lists from models/sampling/results/, extracts matching frames from
models/full_model/full_dft.xyzf, writes fm_setup.in and SLURM launch scripts
per subset (alpha × retention × replicate).

Usage
-----
  cd models/pruned_models
  python prepare_runs.py
  python prepare_runs.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
MULTIELEMENT_ROOT = SCRIPT_DIR.parents[1]
SAMPLING_RESULTS = SCRIPT_DIR.parent / "sampling" / "results"
FULL_XYZF = SCRIPT_DIR.parent / "full_model" / "full_dft.xyzf"
TEMPLATE_DIR = SCRIPT_DIR / "templates"
RUNS_DIR = SCRIPT_DIR / "runs"
FRAME_RE = re.compile(r"^frame_(\d+)$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sampling-results",
        type=Path,
        default=SAMPLING_RESULTS,
        help="Root of FPS sampling outputs.",
    )
    parser.add_argument(
        "--source-xyzf",
        type=Path,
        default=FULL_XYZF,
        help="Full CN training trajectory (298 frames).",
    )
    parser.add_argument(
        "--runs-dir",
        type=Path,
        default=RUNS_DIR,
        help="Output root for per-subset run directories.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--replicate",
        type=int,
        default=None,
        help="Only prepare runs for this replicate index (e.g. 0).",
    )
    parser.add_argument(
        "--debug-queue",
        action="store_true",
        help="Use skx-dev partition for all runs (longer walltimes for larger subsets).",
    )
    parser.add_argument(
        "--retention-fractions",
        type=float,
        nargs="+",
        default=None,
        help="Only prepare runs at these retention fractions (e.g. 0.01 0.10 0.20).",
    )
    return parser.parse_args()


def iter_xyzf_frames(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        while True:
            line = handle.readline()
            if not line:
                break
            n_atoms = int(line.strip())
            box_line = handle.readline()
            atoms = [handle.readline() for _ in range(n_atoms)]
            yield n_atoms, box_line, atoms


def load_all_frames(path: Path) -> list[tuple[int, str, list[str]]]:
    return list(iter_xyzf_frames(path))


def frame_to_index(frame_name: str) -> int:
    match = FRAME_RE.match(frame_name)
    if not match:
        raise ValueError(f"Invalid frame name: {frame_name}")
    return int(match.group(1))


def write_subset_xyzf(
    frames: list[tuple[int, str, list[str]]],
    indices: list[int],
    output_path: Path,
) -> None:
    with output_path.open("w", encoding="utf-8") as handle:
        for idx in indices:
            n_atoms, box_line, atoms = frames[idx]
            handle.write(f"{n_atoms}\n")
            handle.write(box_line)
            handle.writelines(atoms)


def resources_for_n_frames(n_frames: int, *, debug_queue: bool = False) -> dict[str, str | int]:
    if debug_queue:
        if n_frames <= 10:
            gen_wall, solve_wall = "01:00:00", "02:00:00"
        elif n_frames <= 50:
            gen_wall, solve_wall = "02:00:00", "02:00:00"
        else:
            gen_wall, solve_wall = "02:00:00", "02:00:00"
        return {
            "partition": "skx-dev",
            "nnodes": 1,
            "ncores": 48,
            "ntasks": 48,
            "gen_walltime": gen_wall,
            "solve_walltime": solve_wall,
        }
    if n_frames <= 10:
        return {
            "partition": "skx-dev",
            "nnodes": 1,
            "ncores": 48,
            "ntasks": 48,
            "gen_walltime": "01:00:00",
            "solve_walltime": "01:00:00",
        }
    if n_frames <= 50:
        return {
            "partition": "skx",
            "nnodes": 1,
            "ncores": 48,
            "ntasks": 48,
            "gen_walltime": "04:00:00",
            "solve_walltime": "06:00:00",
        }
    return {
        "partition": "skx",
        "nnodes": 1,
        "ncores": 96,
        "ntasks": 96,
        "gen_walltime": "12:00:00",
        "solve_walltime": "06:00:00",
    }


def render_template(template_path: Path, mapping: dict[str, str | int]) -> str:
    text = template_path.read_text(encoding="utf-8")
    for key, value in mapping.items():
        text = text.replace(f"{{{{{key}}}}}", str(value))
    return text


def run_name(alpha_dir: str, pct_dir: str, rep_dir: str) -> str:
    alpha = alpha_dir.replace("alpha_", "a").replace(".", "")
    pct = pct_dir.replace("pct_", "")
    rep = rep_dir.replace("replicate_", "rep")
    return f"{alpha}_pct{pct}_{rep}"


def discover_sampling_runs(results_root: Path) -> list[dict]:
    runs = []
    for meta_path in sorted(results_root.glob("alpha_*/*/replicate_*/metadata.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        sel_path = meta_path.parent / "selected_frames.txt"
        runs.append(
            {
                "alpha": meta["alpha"],
                "retention_fraction": meta["retention_fraction"],
                "replicate": meta["replicate"],
                "seed": meta["seed"],
                "n_selected": meta["n_selected"],
                "selected_frames": sel_path.read_text(encoding="utf-8").strip().split("\n"),
                "sampling_path": str(meta_path.parent.relative_to(results_root)),
                "name": run_name(
                    meta_path.parents[2].name,
                    meta_path.parents[1].name,
                    meta_path.parent.name,
                ),
            }
        )
    return runs


def prepare_run(
    run: dict,
    *,
    all_frames: list,
    runs_dir: Path,
    dry_run: bool,
    debug_queue: bool = False,
) -> Path:
    out_dir = runs_dir / run["name"]
    frame_indices = [frame_to_index(frame) for frame in run["selected_frames"]]
    n_frames = len(frame_indices)
    resources = resources_for_n_frames(n_frames, debug_queue=debug_queue)
    trjfile = "training.xyzf"

    if dry_run:
        print(f"[dry-run] {out_dir.name}: n={n_frames}, alpha={run['alpha']}")
        return out_dir

    out_dir.mkdir(parents=True, exist_ok=True)

    write_subset_xyzf(all_frames, frame_indices, out_dir / trjfile)

    fm_setup = render_template(
        TEMPLATE_DIR / "fm_setup.in.template",
        {"TRJFILE": trjfile, "NFRAMES": n_frames},
    )
    (out_dir / "fm_setup.in").write_text(fm_setup, encoding="utf-8")

    job_prefix = run["name"]
    mapping = {
        "JOB_PREFIX": job_prefix,
        "MULTIELEMENT_ROOT": str(MULTIELEMENT_ROOT),
        "PARTITION": resources["partition"],
        "NNODES": resources["nnodes"],
        "NCORES": resources["ncores"],
        "NTASKS": resources["ntasks"],
        "GEN_WALLTIME": resources["gen_walltime"],
        "SOLVE_WALLTIME": resources["solve_walltime"],
    }

    gen_cmd = render_template(TEMPLATE_DIR / "run_gen_Amat.cmd", mapping)
    solve_cmd = render_template(TEMPLATE_DIR / "run_solve_Amat.cmd", mapping)

    gen_path = out_dir / "run_gen_Amat.cmd"
    solve_path = out_dir / "run_solve_Amat.cmd"
    gen_path.write_text(gen_cmd, encoding="utf-8")
    solve_path.write_text(solve_cmd, encoding="utf-8")
    gen_path.chmod(0o755)
    solve_path.chmod(0o755)

    manifest = {
        "name": run["name"],
        "alpha": run["alpha"],
        "retention_fraction": run["retention_fraction"],
        "replicate": run["replicate"],
        "seed": run["seed"],
        "n_frames": n_frames,
        "frame_indices": frame_indices,
        "selected_frames": run["selected_frames"],
        "sampling_path": run["sampling_path"],
        "resources": resources,
    }
    (out_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return out_dir


def main() -> None:
    args = parse_args()

    if not args.sampling_results.is_dir():
        raise FileNotFoundError(f"Missing sampling results: {args.sampling_results}")
    if not args.source_xyzf.is_file():
        raise FileNotFoundError(f"Missing source xyzf: {args.source_xyzf}")

    runs = discover_sampling_runs(args.sampling_results)
    if not runs:
        raise RuntimeError(f"No sampling runs found under {args.sampling_results}")

    if args.replicate is not None:
        runs = [r for r in runs if r["replicate"] == args.replicate]
    if args.retention_fractions is not None:
        allowed = set(args.retention_fractions)
        runs = [r for r in runs if r["retention_fraction"] in allowed]
    if not runs:
        raise RuntimeError("No runs matched the requested filters.")

    label = f"{len(runs)} pruned-model runs"
    if args.replicate is not None:
        label += f" (replicate {args.replicate:02d})"
    if args.debug_queue:
        label += " [skx-dev]"
    print(f"Preparing {label} from {args.sampling_results}")
    all_frames = None if args.dry_run else load_all_frames(args.source_xyzf)
    if all_frames is not None:
        print(f"Loaded {len(all_frames)} frames from {args.source_xyzf}")

    prepared = []
    for run in runs:
        out_dir = prepare_run(
            run,
            all_frames=all_frames,
            runs_dir=args.runs_dir,
            dry_run=args.dry_run,
            debug_queue=args.debug_queue,
        )
        prepared.append(out_dir)

    if not args.dry_run:
        index = {
            "n_runs": len(prepared),
            "source_xyzf": str(args.source_xyzf),
            "runs": [str(p.relative_to(args.runs_dir)) for p in prepared],
        }
        args.runs_dir.mkdir(parents=True, exist_ok=True)
        (args.runs_dir / "index.json").write_text(
            json.dumps(index, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"\nWrote {len(prepared)} run directories to {args.runs_dir}")


if __name__ == "__main__":
    main()
