#!/usr/bin/env bash
# Submit gen→solve for 1% retention, replicate 00, all five α values on skx-dev.
#
#   cd models/pruned_models
#   bash submit_debug_pct001.sh
#   bash submit_debug_pct001.sh --batch-size 2

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNS_DIR="${SCRIPT_DIR}/runs"

BATCH_SIZE=9999
while [[ $# -gt 0 ]]; do
    case "$1" in
        --batch-size) BATCH_SIZE="$2"; shift ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
    shift
done

echo "Refreshing SLURM scripts for pct001 rep00 on skx-dev..."
python3 "${SCRIPT_DIR}/prepare_runs.py" --replicate 0 --debug-queue

job_active() {
    local jid="$1"
    [[ -n "${jid}" && "${jid}" != "None" && "${jid}" != "null" ]] \
        && squeue -j "${jid}" -h 2>/dev/null | grep -q .
}

params_complete() {
    [[ -f "$1/params.txt" ]] && grep -q ENDFILE "$1/params.txt" 2>/dev/null
}

gen_complete() {
    [[ -f "$1/A.txt" && -f "$1/fm_setup.log" ]]
}

submitted=0
for run_dir in "${RUNS_DIR}"/a*_pct001_rep00/; do
    [[ -d "${run_dir}" ]] || continue
    name="$(basename "${run_dir}")"

    if params_complete "${run_dir}"; then
        echo "Skipping ${name} (params.txt complete)"
        continue
    fi

    if [[ -f "${run_dir}/submitted.json" ]]; then
        gen_id="$(python3 -c "import json; print(json.load(open('${run_dir}/submitted.json')).get('gen_job',''))" 2>/dev/null || true)"
        solve_id="$(python3 -c "import json; print(json.load(open('${run_dir}/submitted.json')).get('solve_job','') or '')" 2>/dev/null || true)"
        if job_active "${gen_id}" || job_active "${solve_id}"; then
            echo "Skipping ${name} (jobs still queued/running)"
            continue
        fi
    fi

    if [[ "${submitted}" -ge "${BATCH_SIZE}" ]]; then
        echo "Batch limit (${BATCH_SIZE}) reached; re-run to submit more."
        break
    fi

    cd "${run_dir}"

    if gen_complete "${run_dir}"; then
        if ! solve_out="$(sbatch run_solve_Amat.cmd 2>&1)"; then
            echo "FAILED solve-only ${name}: ${solve_out}" >&2
            continue
        fi
        solve_id="$(echo "${solve_out}" | awk '/Submitted batch job/ {print $NF}')"
        gen_id="$(python3 -c "import json; print(json.load(open('submitted.json')).get('gen_job','null') if __import__('pathlib').Path('submitted.json').exists() else 'null')" 2>/dev/null || echo "null")"
        printf '{"gen_job": %s, "solve_job": %s, "debug": true, "solve_only": true}\n' \
            "${gen_id}" "${solve_id}" > submitted.json
        echo "Submitted solve-only ${name}: solve=${solve_id}"
        submitted=$((submitted + 1))
        continue
    fi

    if ! gen_out="$(sbatch run_gen_Amat.cmd 2>&1)"; then
        echo "FAILED gen ${name}: ${gen_out}" >&2
        continue
    fi
    gen_id="$(echo "${gen_out}" | awk '/Submitted batch job/ {print $NF}')"
    if [[ -z "${gen_id}" ]]; then
        echo "FAILED gen ${name}: ${gen_out}" >&2
        continue
    fi

    if ! solve_out="$(sbatch --dependency=afterok:"${gen_id}" run_solve_Amat.cmd 2>&1)"; then
        echo "FAILED solve ${name} (gen=${gen_id}): ${solve_out}" >&2
        printf '{"gen_job": %s, "solve_job": null, "debug": true}\n' "${gen_id}" > submitted.json
        continue
    fi
    solve_id="$(echo "${solve_out}" | awk '/Submitted batch job/ {print $NF}')"

    printf '{"gen_job": %s, "solve_job": %s, "debug": true}\n' \
        "${gen_id}" "${solve_id}" > submitted.json
    echo "Submitted ${name}: gen=${gen_id} solve=${solve_id}"
    submitted=$((submitted + 1))
done

echo "Submitted ${submitted} pct001 rep00 chain(s). Monitor: squeue -u \$USER"

if [[ -n "${RESEARCH_NOTES_ROOT:-}" ]]; then
    python3 "${SCRIPT_DIR}/../../scripts/sync_proj_c_log.py" scan || true
fi
