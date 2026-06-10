#!/usr/bin/env bash
# Submit NVT+RDF LAMMPS jobs for the full (100%) ChIMES model at all statepoints.
#
#   cd models/statepoint_eval
#   python prepare_runs.py --sync-params --models full
#   bash submit_full_model.sh
#   bash submit_full_model.sh --batch-size 10

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNS_DIR="${SCRIPT_DIR}/runs/full"
BATCH_SIZE=9999
PARTITION="skx"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --batch-size) BATCH_SIZE="$2"; shift ;;
        --partition) PARTITION="$2"; shift ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
    shift
done

echo "Refreshing run directories for model=full (partition=${PARTITION})..."
python3 "${SCRIPT_DIR}/prepare_runs.py" --sync-params --models full --partition "${PARTITION}"

if [[ ! -d "${RUNS_DIR}" ]]; then
    echo "No runs found under ${RUNS_DIR}" >&2
    exit 1
fi

submitted=0
for run_dir in "${RUNS_DIR}"/*/; do
    [[ -d "${run_dir}" ]] || continue
    name="$(basename "${run_dir}")"

    if [[ -f "${run_dir}/rdf.dat" ]]; then
        echo "Skipping ${name} (rdf.dat exists)"
        continue
    fi

    if [[ "${submitted}" -ge "${BATCH_SIZE}" ]]; then
        echo "Batch limit (${BATCH_SIZE}) reached; re-run to submit more."
        break
    fi

    cd "${run_dir}"
    if ! out="$(sbatch run_lammps.cmd 2>&1)"; then
        echo "FAILED ${name}: ${out}" >&2
        continue
    fi
    job_id="$(echo "${out}" | awk '/Submitted batch job/ {print $NF}')"
    echo "Submitted ${name}: job=${job_id}"
    submitted=$((submitted + 1))
done

echo "Submitted ${submitted} statepoint job(s) for model=full."
