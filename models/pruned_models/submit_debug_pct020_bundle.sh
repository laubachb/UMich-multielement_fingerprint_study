#!/usr/bin/env bash
# Submit one SLURM job that sequentially fits all five 20% retention cuts
# (replicate 00, one per α) on a single skx allocation.
#
#   cd models/pruned_models
#   bash submit_debug_pct020_bundle.sh
#   bash submit_debug_pct020_bundle.sh --dry-run

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNS_DIR="${SCRIPT_DIR}/runs"
TEMPLATE="${SCRIPT_DIR}/templates/run_debug_pct020_bundle.cmd"
BUNDLE_CMD="${SCRIPT_DIR}/run_debug_pct020_bundle.cmd"
MULTIELEMENT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

PARTITION="skx"
WALLTIME="48:00:00"
NNODES=1
NCORES=48
NTASKS=48
DRY_RUN=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1 ;;
        --partition) PARTITION="$2"; shift ;;
        --walltime) WALLTIME="$2"; shift ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
    shift
done

job_active() {
    local jid="$1"
    [[ -n "${jid}" && "${jid}" != "None" && "${jid}" != "null" ]] \
        && squeue -j "${jid}" -h 2>/dev/null | grep -q .
}

params_complete() {
    [[ -f "$1/params.txt" ]] && grep -q ENDFILE "$1/params.txt" 2>/dev/null
}

echo "Refreshing run dirs for pct020 rep00..."
python3 "${SCRIPT_DIR}/prepare_runs.py" --replicate 0 --debug-queue

pending=()
for run_dir in "${RUNS_DIR}"/a*_pct020_rep00/; do
    [[ -d "${run_dir}" ]] || continue
    name="$(basename "${run_dir}")"
    if params_complete "${run_dir}"; then
        echo "  ${name}: complete"
    else
        echo "  ${name}: pending"
        pending+=("${name}")
    fi
done

if [[ "${#pending[@]}" -eq 0 ]]; then
    echo "All five pct020 rep00 models already complete; nothing to submit."
    exit 0
fi

if [[ -f "${SCRIPT_DIR}/pct020_bundle_submitted.json" ]]; then
    bundle_id="$(python3 -c "import json; print(json.load(open('${SCRIPT_DIR}/pct020_bundle_submitted.json')).get('bundle_job',''))" 2>/dev/null || true)"
    if job_active "${bundle_id}"; then
        echo "Bundle job ${bundle_id} still queued/running; not resubmitting."
        exit 0
    fi
fi

mapping=(
    "MULTIELEMENT_ROOT=${MULTIELEMENT_ROOT}"
    "PRUNED_MODELS_ROOT=${SCRIPT_DIR}"
    "PARTITION=${PARTITION}"
    "WALLTIME=${WALLTIME}"
    "NNODES=${NNODES}"
    "NCORES=${NCORES}"
    "NTASKS=${NTASKS}"
)

text="$(<"${TEMPLATE}")"
for pair in "${mapping[@]}"; do
    key="${pair%%=*}"
    value="${pair#*=}"
    text="${text//\{\{${key}\}\}/${value}}"
done
printf '%s\n' "${text}" > "${BUNDLE_CMD}"
chmod +x "${BUNDLE_CMD}"

echo ""
echo "Bundle will run ${#pending[@]} pending model(s) on ${PARTITION} (${WALLTIME}):"
printf '  %s\n' "${pending[@]}"

if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "Dry run: wrote ${BUNDLE_CMD}, not submitting."
    exit 0
fi

cd "${SCRIPT_DIR}"
if ! submit_out="$(sbatch "${BUNDLE_CMD}" 2>&1)"; then
    echo "FAILED submit: ${submit_out}" >&2
    exit 1
fi
bundle_id="$(echo "${submit_out}" | awk '/Submitted batch job/ {print $NF}')"
if [[ -z "${bundle_id}" ]]; then
    echo "FAILED submit: ${submit_out}" >&2
    exit 1
fi

PENDING_JSON="$(printf '%s\n' "${pending[@]}" | python3 -c 'import json,sys; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))')"
python3 - <<PY
import json
from pathlib import Path

out = Path("${SCRIPT_DIR}") / "pct020_bundle_submitted.json"
out.write_text(json.dumps({
    "bundle_job": "${bundle_id}",
    "partition": "${PARTITION}",
    "walltime": "${WALLTIME}",
    "pending": json.loads("""${PENDING_JSON}"""),
    "debug": True,
}, indent=2) + "\n", encoding="utf-8")
PY

echo "Submitted pct020 bundle: job=${bundle_id}"
echo "Monitor: squeue -j ${bundle_id}"
echo "Log:     ${SCRIPT_DIR}/pct020_bundle_${bundle_id}.out"

if [[ -n "${RESEARCH_NOTES_ROOT:-}" ]]; then
    python3 "${SCRIPT_DIR}/../../scripts/sync_proj_c_log.py" scan || true
fi
