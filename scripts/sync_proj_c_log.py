#!/usr/bin/env python3
"""
Sync multielement_study compute status to Proj_C-multielement research notes.

Requires RESEARCH_NOTES_ROOT pointing at the UMich-research_notes clone
(not tracked in this repository).

Usage
-----
  export RESEARCH_NOTES_ROOT=/path/to/UMich-research_notes

  # Full scan (manual / cron)
  python scripts/sync_proj_c_log.py scan

  # Single job event (called from SLURM epilogue via log_compute_event.sh)
  python scripts/sync_proj_c_log.py event --type chimes_solve --run-dir ... --exit-code 0

After updating logs, auto-commits and pushes only files under
`02_projects/Proj_C-multielement/logs/` in the research-notes repo.
Set RESEARCH_NOTES_AUTO_PUSH=0 to disable.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
MULTIELEMENT_ROOT = SCRIPT_DIR.parent
PROJ_C_REL = Path("02_projects/Proj_C-multielement/logs")
STATE_FILE = MULTIELEMENT_ROOT / ".proj_c_compute_log_state.json"

ALPHA_DIRS = ("a000", "a025", "a050", "a075", "a100")
HEA_ALPHA_DIRS = (
    "alpha_0-histograms",
    "alpha_025-histograms",
    "alpha_050-histograms",
    "alpha_075-histograms",
    "alpha_1-histograms",
)
PRUNED_RUN_RE = re.compile(r"^a(?P<alpha>\d{3})_pct(?P<pct>\d{3})_rep(?P<rep>\d{2})$")
AUTO_SYNC_BEGIN = "<!-- AUTO-SYNC:BEGIN -->"
AUTO_SYNC_END = "<!-- AUTO-SYNC:END -->"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def today_header() -> str:
    return datetime.now().strftime("%Y-%m-%d (%A)")


def research_notes_root() -> Path | None:
    raw = os.environ.get("RESEARCH_NOTES_ROOT", "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser().resolve()
    if not path.is_dir():
        print(f"Warning: RESEARCH_NOTES_ROOT not found: {path}", file=sys.stderr)
        return None
    return path


def proj_c_logs(root: Path) -> tuple[Path, Path]:
    log_dir = root / PROJ_C_REL
    log_dir.mkdir(parents=True, exist_ok=True)
    compute_log = log_dir / "COMPUTE_LOG.md"
    daily_log = log_dir / "DAILY_LOG.md"
    if not compute_log.exists():
        compute_log.write_text(
            "---\n"
            'title: "Proj_C-multielement Compute Log"\n'
            'type: "Log"\n'
            "auto_generated: true\n"
            "---\n\n"
            "# Proj_C-multielement — Compute Log\n\n"
            "Append-only HPC events synced from "
            "`multielement_study` (via `RESEARCH_NOTES_ROOT`). "
            "Narrative context → [[DAILY_LOG]].\n\n"
            "---\n\n",
            encoding="utf-8",
        )
    return compute_log, daily_log


def load_state() -> dict:
    if STATE_FILE.is_file():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"logged_keys": [], "last_scan": None}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def state_key(*parts: str) -> str:
    return ":".join(parts)


def already_logged(state: dict, key: str) -> bool:
    return key in state.get("logged_keys", [])


def mark_logged(state: dict, key: str) -> None:
    keys = state.setdefault("logged_keys", [])
    if key not in keys:
        keys.append(key)


def tail_lines(path: Path, n: int = 10) -> list[str]:
    if not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return lines[-n:] if lines else []


def find_log_tail(run_dir: Path, event_type: str) -> list[str]:
    candidates: list[Path] = []
    if event_type.startswith("chimes"):
        candidates.extend(
            sorted(run_dir.glob("solve.err"))
            + sorted(run_dir.glob("erroutmsg_solve_*"))
            + sorted(run_dir.glob("stdoutmsg_solve_*"))
            + sorted(run_dir.glob("erroutmsg_gen_*"))
            + sorted(run_dir.glob("stdoutmsg_gen_*"))
            + sorted(run_dir.glob("fm_setup.log"))
        )
    elif event_type == "statepoint_md":
        candidates.extend(
            sorted(run_dir.glob("erroutmsg_*"))
            + sorted(run_dir.glob("stdoutmsg_*"))
            + sorted(run_dir.glob("output.txt"))
            + sorted(run_dir.glob("log.lammps"))
        )
    else:
        candidates.extend(sorted(run_dir.glob("*.err")) + sorted(run_dir.glob("*.log")))

    for path in candidates:
        tail = tail_lines(path, 10)
        if tail:
            return [f"(from {path.name})"] + tail
    return []


def params_complete(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        return "ENDFILE" in path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False


def format_entry(
    event_type: str,
    label: str,
    status: str,
    details: list[str],
    tail: list[str] | None = None,
) -> str:
    ts = utc_now()
    lines = [
        f"### {ts} | {event_type} | {label} | {status}",
        "",
    ]
    for detail in details:
        lines.append(f"- {detail}")
    if tail:
        lines.append("- **tail (last 10 lines):**")
        lines.append("```")
        lines.extend(tail)
        lines.append("```")
    lines.append("")
    return "\n".join(lines)


def append_compute_log(compute_log: Path, entry: str) -> None:
    with compute_log.open("a", encoding="utf-8") as handle:
        handle.write(entry)
        if not entry.endswith("\n"):
            handle.write("\n")


def update_daily_log_summary(daily_log: Path, summary_lines: list[str]) -> None:
    if not daily_log.is_file():
        return
    text = daily_log.read_text(encoding="utf-8")
    header = f"## {today_header()}"
    block = (
        f"{AUTO_SYNC_BEGIN}\n"
        "**Compute sync (auto):**\n"
        + "\n".join(f"- {line}" for line in summary_lines)
        + f"\n{AUTO_SYNC_END}"
    )

    if header in text:
        pattern = re.compile(
            re.escape(AUTO_SYNC_BEGIN) + r".*?" + re.escape(AUTO_SYNC_END),
            re.DOTALL,
        )
        if pattern.search(text):
            text = pattern.sub(block, text, count=1)
        else:
            idx = text.index(header) + len(header)
            text = text[:idx] + "\n\n" + block + text[idx:]
    else:
        text = text.rstrip() + f"\n\n---\n\n{header}\n\n{block}\n"

    daily_log.write_text(text, encoding="utf-8")


def log_event(
    state: dict,
    compute_log: Path,
    event_type: str,
    label: str,
    status: str,
    details: list[str],
    run_dir: Path | None = None,
    force: bool = False,
) -> bool:
    key = state_key(event_type, label, status)
    if not force and already_logged(state, key):
        return False
    tail = None
    if status != "SUCCESS" and run_dir is not None:
        tail = find_log_tail(run_dir, event_type)
    append_compute_log(
        compute_log,
        format_entry(event_type, label, status, details, tail=tail),
    )
    mark_logged(state, key)
    return True


def scan_pruned_models(state: dict, compute_log: Path) -> dict[str, int]:
    runs_dir = MULTIELEMENT_ROOT / "models/pruned_models/runs"
    counts = {"complete": 0, "partial": 0, "not_started": 0}
    if not runs_dir.is_dir():
        return counts

    for run_dir in sorted(runs_dir.iterdir()):
        if not run_dir.is_dir() or not PRUNED_RUN_RE.match(run_dir.name):
            continue
        name = run_dir.name
        if params_complete(run_dir / "params.txt"):
            counts["complete"] += 1
            key = state_key("chimes_fit", name, "SUCCESS")
            if not already_logged(state, key):
                nlines = sum(1 for _ in (run_dir / "params.txt").open())
                log_event(
                    state,
                    compute_log,
                    "chimes_fit",
                    name,
                    "SUCCESS",
                    [
                        f"path: `models/pruned_models/runs/{name}/`",
                        f"params.txt: {nlines} lines, ENDFILE ok",
                    ],
                )
        elif (run_dir / "A.txt").is_file():
            counts["partial"] += 1
            if (run_dir / "solve.err").is_file() and not params_complete(run_dir / "params.txt"):
                key = state_key("chimes_fit", name, "FAILED")
                if not already_logged(state, key):
                    log_event(
                        state,
                        compute_log,
                        "chimes_solve",
                        name,
                        "FAILED",
                        [
                            f"path: `models/pruned_models/runs/{name}/`",
                            "A.txt present but params.txt incomplete",
                        ],
                        run_dir=run_dir,
                    )
        else:
            counts["not_started"] += 1
    return counts


def scan_statepoint_md(state: dict, compute_log: Path) -> dict[str, int]:
    runs_dir = MULTIELEMENT_ROOT / "models/statepoint_eval/runs"
    counts = {"complete": 0, "total": 0}
    if not runs_dir.is_dir():
        return counts

    for model_dir in sorted(runs_dir.iterdir()):
        if not model_dir.is_dir():
            continue
        for run_dir in sorted(model_dir.iterdir()):
            if not run_dir.is_dir():
                continue
            counts["total"] += 1
            label = f"{model_dir.name}/{run_dir.name}"
            if (run_dir / "rdf.dat").is_file():
                counts["complete"] += 1
                key = state_key("statepoint_md", label, "SUCCESS")
                if not already_logged(state, key):
                    log_event(
                        state,
                        compute_log,
                        "statepoint_md",
                        label,
                        "SUCCESS",
                        [
                            f"path: `models/statepoint_eval/runs/{label}/`",
                            "rdf.dat written",
                        ],
                    )
    return counts


def count_hist_frames(fp_dir: Path) -> int:
    if not fp_dir.is_dir():
        return 0
    return sum(1 for d in fp_dir.iterdir() if d.is_dir() and d.name.startswith("frame_") and list(d.glob("*.hist")))


def scan_cn_fingerprints(state: dict, compute_log: Path) -> dict[str, int]:
    base = MULTIELEMENT_ROOT / "models/fingerprints"
    counts: dict[str, int] = {}
    for alpha in ALPHA_DIRS:
        fp_dir = base / f"{alpha}_fingerprints"
        n = count_hist_frames(fp_dir)
        counts[alpha] = n
        key = state_key("cn_fingerprints", alpha, str(n))
        if not already_logged(state, key):
            log_event(
                state,
                compute_log,
                "cn_fingerprints",
                alpha,
                "SCAN",
                [
                    f"path: `models/fingerprints/{alpha}_fingerprints/`",
                    f"frames with *.hist: {n}",
                ],
            )
    return counts


def scan_hea_fingerprints(state: dict, compute_log: Path) -> dict[str, int]:
    base = MULTIELEMENT_ROOT / "hea_study"
    counts: dict[str, int] = {}
    for alpha_dir in HEA_ALPHA_DIRS:
        fp_dir = base / alpha_dir
        n = count_hist_frames(fp_dir)
        counts[alpha_dir] = n
        key = state_key("hea_fingerprints", alpha_dir, str(n))
        if not already_logged(state, key):
            log_event(
                state,
                compute_log,
                "hea_fingerprints",
                alpha_dir,
                "SCAN",
                [
                    f"path: `hea_study/{alpha_dir}/`",
                    f"frames with *.hist: {n}",
                ],
            )
    return counts


def scan_element_switching(state: dict, compute_log: Path) -> dict[str, str]:
    base = MULTIELEMENT_ROOT / "element_switching"
    summary: dict[str, str] = {}
    for system in ("graphite", "liquid"):
        fp_root = base / system / "fingerprints"
        if not fp_root.is_dir():
            alt = MULTIELEMENT_ROOT / "element_switching/data" / system / "fingerprints"
            fp_root = alt if alt.is_dir() else fp_root
        n_dirs = len([d for d in fp_root.glob("*") if d.is_dir()]) if fp_root.is_dir() else 0
        summary[system] = f"{n_dirs} fingerprint subdirs"
        key = state_key("element_switching", system, str(n_dirs))
        if not already_logged(state, key):
            log_event(
                state,
                compute_log,
                "element_switching",
                system,
                "SCAN",
                [
                    f"path: `element_switching/{system}/`",
                    summary[system],
                ],
            )
    return summary


def count_pruned_models() -> dict[str, int]:
    runs_dir = MULTIELEMENT_ROOT / "models/pruned_models/runs"
    counts = {"complete": 0, "partial": 0, "not_started": 0}
    if not runs_dir.is_dir():
        return counts
    for run_dir in runs_dir.iterdir():
        if not run_dir.is_dir() or not PRUNED_RUN_RE.match(run_dir.name):
            continue
        if params_complete(run_dir / "params.txt"):
            counts["complete"] += 1
        elif (run_dir / "A.txt").is_file():
            counts["partial"] += 1
        else:
            counts["not_started"] += 1
    return counts


def count_pct001_rep00() -> int:
    runs_dir = MULTIELEMENT_ROOT / "models/pruned_models/runs"
    if not runs_dir.is_dir():
        return 0
    return sum(
        1
        for alpha in ALPHA_DIRS
        if params_complete(runs_dir / f"{alpha}_pct001_rep00" / "params.txt")
    )


def count_statepoint_md() -> dict[str, int]:
    runs_dir = MULTIELEMENT_ROOT / "models/statepoint_eval/runs"
    counts = {"complete": 0, "total": 0}
    if not runs_dir.is_dir():
        return counts
    for model_dir in runs_dir.iterdir():
        if not model_dir.is_dir():
            continue
        for run_dir in model_dir.iterdir():
            if not run_dir.is_dir():
                continue
            counts["total"] += 1
            if (run_dir / "rdf.dat").is_file():
                counts["complete"] += 1
    return counts


def count_cn_fingerprints() -> dict[str, int]:
    base = MULTIELEMENT_ROOT / "models/fingerprints"
    return {
        alpha: count_hist_frames(base / f"{alpha}_fingerprints") for alpha in ALPHA_DIRS
    }


def auto_push_enabled() -> bool:
    return os.environ.get("RESEARCH_NOTES_AUTO_PUSH", "1").lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def maybe_push_research_notes(root: Path, log_paths: list[Path]) -> None:
    """Commit and push Proj_C log files in the research-notes repo only."""
    if not auto_push_enabled():
        return
    if not (root / ".git").is_dir():
        print(
            f"Warning: RESEARCH_NOTES_ROOT is not a git repo; skip push: {root}",
            file=sys.stderr,
        )
        return

    rel_paths = sorted(
        {str(path.relative_to(root)) for path in log_paths if path.is_file()}
    )
    if not rel_paths:
        return

    status = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "--", *rel_paths],
        capture_output=True,
        text=True,
        check=False,
    )
    if status.returncode != 0:
        print(
            f"Warning: could not check research notes git status: {status.stderr.strip()}",
            file=sys.stderr,
        )
        return
    if not status.stdout.strip():
        return

    add = subprocess.run(
        ["git", "-C", str(root), "add", "--", *rel_paths],
        capture_output=True,
        text=True,
        check=False,
    )
    if add.returncode != 0:
        print(
            f"Warning: research notes git add failed: {add.stderr.strip()}",
            file=sys.stderr,
        )
        return

    commit = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "commit",
            "-m",
            f"auto: Proj_C compute log sync ({utc_now()})",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if commit.returncode != 0:
        print(
            f"Warning: research notes commit failed: {commit.stderr.strip()}",
            file=sys.stderr,
        )
        return

    push = subprocess.run(
        ["git", "-C", str(root), "push", "origin", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if push.returncode == 0:
        print(f"Pushed research notes ({', '.join(rel_paths)})")
    else:
        print(
            "Warning: research notes push failed "
            f"(changes committed locally; retry on next sync): {push.stderr.strip()}",
            file=sys.stderr,
        )


def build_summary() -> list[str]:
    pruned = count_pruned_models()
    statepoint = count_statepoint_md()
    cn = count_cn_fingerprints()
    return [
        f"Pruned ChIMES fits: {pruned['complete']} complete, "
        f"{pruned['partial']} in progress, {pruned['not_started']} not started",
        f"1% rep00 models (5 α): {count_pct001_rep00()}/5 complete",
        f"Statepoint MD: {statepoint['complete']}/{statepoint['total']} runs with rdf.dat",
        "CN fingerprints (frames w/ hist): "
        + ", ".join(f"{a}={cn.get(a, 0)}" for a in ALPHA_DIRS),
    ]


def cmd_scan(args: argparse.Namespace) -> int:
    root = research_notes_root()
    if root is None:
        print("RESEARCH_NOTES_ROOT not set; skipping sync.", file=sys.stderr)
        return 0

    compute_log, daily_log = proj_c_logs(root)
    state = load_state()

    pruned = scan_pruned_models(state, compute_log)
    statepoint = scan_statepoint_md(state, compute_log)
    cn = scan_cn_fingerprints(state, compute_log)
    scan_hea_fingerprints(state, compute_log)
    scan_element_switching(state, compute_log)

    state["last_scan"] = utc_now()
    save_state(state)

    summary = build_summary()
    update_daily_log_summary(daily_log, summary)
    print("Scan complete. Updated:")
    print(f"  {compute_log}")
    print(f"  {daily_log} (auto-sync block)")
    for line in summary:
        print(f"  - {line}")
    maybe_push_research_notes(root, [compute_log, daily_log])
    return 0


def cmd_event(args: argparse.Namespace) -> int:
    root = research_notes_root()
    if root is None:
        return 0

    compute_log, daily_log = proj_c_logs(root)
    state = load_state()

    run_dir = Path(args.run_dir).resolve()
    label = run_dir.name
    if args.type == "statepoint_md" and run_dir.parent.name != "runs":
        label = f"{run_dir.parent.name}/{run_dir.name}"

    exit_code = int(args.exit_code)
    status = "SUCCESS" if exit_code == 0 else "FAILED"
    partition = os.environ.get("SLURM_JOB_PARTITION", "unknown")
    job_id = os.environ.get("SLURM_JOB_ID", "local")

    details = [
        f"path: `{run_dir.relative_to(MULTIELEMENT_ROOT)}`",
        f"partition: {partition} | job_id: {job_id} | exit_code: {exit_code}",
    ]

    if status == "SUCCESS" and args.type == "chimes_solve":
        pt = run_dir / "params.txt"
        if pt.is_file():
            details.append(f"params.txt: {sum(1 for _ in pt.open())} lines")
    if status == "SUCCESS" and args.type == "statepoint_md":
        if (run_dir / "rdf.dat").is_file():
            details.append("rdf.dat written")

    log_event(
        state,
        compute_log,
        args.type,
        label,
        status,
        details,
        run_dir=run_dir,
        force=args.force,
    )
    save_state(state)
    update_daily_log_summary(daily_log, build_summary())
    maybe_push_research_notes(root, [compute_log, daily_log])
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    scan_p = sub.add_parser("scan", help="Full repository scan")
    scan_p.set_defaults(func=cmd_scan)

    event_p = sub.add_parser("event", help="Log single job completion")
    event_p.add_argument("--type", required=True)
    event_p.add_argument("--run-dir", required=True)
    event_p.add_argument("--exit-code", default="0")
    event_p.add_argument("--force", action="store_true")
    event_p.set_defaults(func=cmd_event)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
