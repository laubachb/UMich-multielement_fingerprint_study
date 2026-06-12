#!/usr/bin/env bash
# Submit gen→solve chains for FPS replicates 01–09 at 1% and 10% retention.
# (20% / 50% paused — use submit_debug_pct020_bundle.sh when ready.)
#
# rep00 at each cut is handled separately (debug bundles or already complete).
# Requires FPS sampling with 10 replicates first.
#
#   cd models/pruned_models
#   bash submit_replicates_1_10_20.sh
#   bash submit_replicates_1_10_20.sh --batch-size 25
#   bash submit_replicates_1_10_20.sh --dry-run

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNS_DIR="${SCRIPT_DIR}/runs"

BATCH_SIZE=15
DRY_RUN=0
MIN_REP=1
MAX_REP=9

while [[ $# -gt 0 ]]; do
    case "$1" in
        --batch-size) BATCH_SIZE="$2"; shift ;;
        --dry-run) DRY_RUN=1 ;;
        --min-replicate) MIN_REP="$2"; shift ;;
        --max-replicate) MAX_REP="$2"; shift ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
    shift
done

echo "Preparing run dirs for 1%/10% × replicates ${MIN_REP}–${MAX_REP} (skx walltimes)..."
python3 "${SCRIPT_DIR}/prepare_runs.py" \
    --retention-fractions 0.01 0.10

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

submit_chain() {
    local run_dir="$1"
    local name="$2"

    cd "${run_dir}"

    if gen_complete "${run_dir}"; then
        if ! solve_out="$(sbatch run_solve_Amat.cmd 2>&1)"; then
            echo "FAILED solve-only ${name}: ${solve_out}" >&2
            return 1
        fi
        solve_id="$(echo "${solve_out}" | awk '/Submitted batch job/ {print $NF}')"
        gen_id="$(python3 -c "import json; print(json.load(open('submitted.json')).get('gen_job','null') if __import__('pathlib').Path('submitted.json').exists() else 'null')" 2>/dev/null || echo "null")"
        printf '{"gen_job": %s, "solve_job": %s, "replicate_batch": true, "solve_only": true}\n' \
            "${gen_id}" "${solve_id}" > submitted.json
        echo "Submitted solve-only ${name}: solve=${solve_id}"
        return 0
    fi

    if ! gen_out="$(sbatch run_gen_Amat.cmd 2>&1)"; then
        echo "FAILED gen ${name}: ${gen_out}" >&2
        if echo "${gen_out}" | grep -q QOSMaxSubmitJobPerUserLimit; then
            return 2
        fi
        return 1
    fi
    gen_id="$(echo "${gen_out}" | awk '/Submitted batch job/ {print $NF}')"
    if [[ -z "${gen_id}" ]]; then
        echo "FAILED gen ${name}: ${gen_out}" >&2
        return 1
    fi

    if ! solve_out="$(sbatch --dependency=afterok:"${gen_id}" run_solve_Amat.cmd 2>&1)"; then
        echo "FAILED solve ${name} (gen=${gen_id}): ${solve_out}" >&2
        printf '{"gen_job": %s, "solve_job": null, "replicate_batch": true}\n' "${gen_id}" > submitted.json
        return 1
    fi
    solve_id="$(echo "${solve_out}" | awk '/Submitted batch job/ {print $NF}')"

    printf '{"gen_job": %s, "solve_job": %s, "replicate_batch": true}\n' \
        "${gen_id}" "${solve_id}" > submitted.json
    echo "Submitted ${name}: gen=${gen_id} solve=${solve_id}"
}

submitted=0
skipped_complete=0
skipped_active=0

for pct in pct001 pct010; do
    for rep in $(seq "${MIN_REP}" "${MAX_REP}"); do
        rep_tag="$(printf 'rep%02d' "${rep}")"
        for run_dir in "${RUNS_DIR}"/a*_"${pct}"_"${rep_tag}"/; do
            [[ -d "${run_dir}" ]] || continue
            name="$(basename "${run_dir}")"

            if params_complete "${run_dir}"; then
                skipped_complete=$((skipped_complete + 1))
                continue
            fi

            if [[ -f "${run_dir}/submitted.json" ]]; then
                gen_id="$(python3 -c "import json; print(json.load(open('${run_dir}/submitted.json')).get('gen_job',''))" 2>/dev/null || true)"
                solve_id="$(python3 -c "import json; print(json.load(open('${run_dir}/submitted.json')).get('solve_job','') or '')" 2>/dev/null || true)"
                if job_active "${gen_id}" || job_active "${solve_id}"; then
                    skipped_active=$((skipped_active + 1))
                    continue
                fi
            fi

            if [[ "${submitted}" -ge "${BATCH_SIZE}" ]]; then
                echo "Batch limit (${BATCH_SIZE}) reached; re-run to submit more."
                echo "Submitted ${submitted} chain(s) this run."
                exit 0
            fi

            if [[ "${DRY_RUN}" -eq 1 ]]; then
                echo "[dry-run] would submit ${name}"
                submitted=$((submitted + 1))
                continue
            fi

            rc=0
            submit_chain "${run_dir}" "${name}" || rc=$?
            if [[ "${rc}" -eq 2 ]]; then
                echo "QOS submit limit reached; re-run when jobs complete."
                echo "Done. submitted=${submitted} skipped_complete=${skipped_complete} skipped_active=${skipped_active}"
                exit 0
            elif [[ "${rc}" -eq 0 ]]; then
                submitted=$((submitted + 1))
            fi
        done
    done
done

echo "Done. submitted=${submitted} skipped_complete=${skipped_complete} skipped_active=${skipped_active}"
if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "(dry run)"
elif [[ "${submitted}" -gt 0 ]]; then
    echo "Monitor: squeue -u \$USER"
fi

if [[ -n "${RESEARCH_NOTES_ROOT:-}" && "${DRY_RUN}" -eq 0 ]]; then
    python3 "${SCRIPT_DIR}/../../scripts/sync_proj_c_log.py" scan || true
fi
