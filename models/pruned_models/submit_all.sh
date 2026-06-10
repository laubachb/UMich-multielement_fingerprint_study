#!/usr/bin/env bash
# Submit gen_Amat → solve_Amat chains for all prepared pruned-model runs.
#
#   cd models/pruned_models
#   bash submit_all.sh
#   bash submit_all.sh --dry-run
#   bash submit_all.sh --batch-size 5   # respect QOS submit limits; re-run until done

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNS_DIR="${SCRIPT_DIR}/runs"
export MULTIELEMENT_ROOT="${MULTIELEMENT_ROOT:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"

DRY_RUN=0
BATCH_SIZE=9999
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1 ;;
        --batch-size) BATCH_SIZE="$2"; shift ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
    shift
done

if [[ ! -d "${RUNS_DIR}" ]]; then
    echo "Missing ${RUNS_DIR}. Run: python prepare_runs.py"
    exit 1
fi

SUBMIT_LOG="${RUNS_DIR}/submitted_jobs.json"
echo "[" > "${SUBMIT_LOG}"

first=1
count=0
submitted_this_run=0

for run_dir in "${RUNS_DIR}"/a*_pct*_rep*/; do
    if [[ "${submitted_this_run}" -ge "${BATCH_SIZE}" ]]; then
        echo "Batch limit (${BATCH_SIZE}) reached; re-run to submit remaining runs."
        break
    fi
    [[ -d "${run_dir}" ]] || continue
    gen_script="${run_dir}/run_gen_Amat.cmd"
    solve_script="${run_dir}/run_solve_Amat.cmd"
    if [[ ! -f "${gen_script}" || ! -f "${solve_script}" ]]; then
        echo "Skipping incomplete run: ${run_dir}"
        continue
    fi

    name="$(basename "${run_dir}")"
    if [[ "${DRY_RUN}" -eq 1 ]]; then
        echo "[dry-run] would submit ${name}"
        continue
    fi

    if [[ -f "${run_dir}/params.txt" ]] && grep -q ENDFILE "${run_dir}/params.txt" 2>/dev/null; then
        echo "Skipping ${name} (params.txt complete)"
        continue
    fi

    if [[ -f "${run_dir}/submitted.json" ]]; then
        echo "Skipping ${name} (already submitted; delete submitted.json to retry)"
        continue
    fi

    cd "${run_dir}"
    gen_id="$(sbatch run_gen_Amat.cmd | awk '/Submitted batch job/ {print $NF}')"
    if [[ -z "${gen_id}" ]]; then
        echo "ERROR: gen_Amat submission failed for ${name}" >&2
        exit 1
    fi
    solve_id="$(sbatch --dependency=afterok:"${gen_id}" run_solve_Amat.cmd | awk '/Submitted batch job/ {print $NF}')"
    if [[ -z "${solve_id}" ]]; then
        echo "ERROR: solve_Amat submission failed for ${name} (gen=${gen_id})" >&2
        exit 1
    fi
    echo "Submitted ${name}: gen=${gen_id} solve=${solve_id} (afterok)"
    printf '{"gen_job": %s, "solve_job": %s}\n' "${gen_id}" "${solve_id}" > submitted.json

    if [[ "${first}" -eq 0 ]]; then
        echo "," >> "${SUBMIT_LOG}"
    fi
    first=0
    printf '  {"run": "%s", "gen_job": %s, "solve_job": %s}' \
        "${name}" "${gen_id}" "${solve_id}" >> "${SUBMIT_LOG}"
    count=$((count + 1))
    submitted_this_run=$((submitted_this_run + 1))
done

echo "" >> "${SUBMIT_LOG}"
echo "]" >> "${SUBMIT_LOG}"

if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "Dry run complete."
else
    echo "Submitted ${count} gen→solve chains. Job IDs: ${SUBMIT_LOG}"
fi
