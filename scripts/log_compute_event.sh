#!/usr/bin/env bash
# Log a single HPC job completion to Proj_C-multielement research notes.
# Called from SLURM job epilogues; safe to run when RESEARCH_NOTES_ROOT is unset (no-op).
#
#   log_compute_event.sh <event_type> <run_dir> [exit_code]
#
# event_type: chimes_gen | chimes_solve | statepoint_md | ...

set -uo pipefail

EVENT_TYPE="${1:-unknown}"
RUN_DIR="${2:-${SLURM_SUBMIT_DIR:-.}}"
EXIT_CODE="${3:-$?}"

if [[ -z "${MULTIELEMENT_ROOT:-}" ]]; then
    _script_file="$(readlink -f "${BASH_SOURCE[0]}")"
    _script_dir="$(cd "$(dirname "$_script_file")" && pwd)"
    export MULTIELEMENT_ROOT="$(cd "$_script_dir/.." && pwd)"
    unset _script_file _script_dir
fi

if [[ -z "${RESEARCH_NOTES_ROOT:-}" ]]; then
    exit 0
fi

python3 "${MULTIELEMENT_ROOT}/scripts/sync_proj_c_log.py" event \
    --type "${EVENT_TYPE}" \
    --run-dir "${RUN_DIR}" \
    --exit-code "${EXIT_CODE}" \
    || true
