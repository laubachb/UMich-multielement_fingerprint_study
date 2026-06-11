#!/usr/bin/env bash
# Validate LAMMPS launch on skx-dev with one (model, statepoint) pair.
#
#   cd models/statepoint_eval
#   bash submit_test_debug.sh
#   bash submit_test_debug.sh a000_pct001_rep00 0.20.3percN_2.0gcc

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_ID="${1:-a000_pct001_rep00}"
STATEPOINT_ID="${2:-0.20.3percN_2.0gcc}"
RUN_DIR="${SCRIPT_DIR}/runs/${MODEL_ID}/${STATEPOINT_ID}"

echo "Preparing debug run: ${MODEL_ID}/${STATEPOINT_ID} (skx-dev)..."
python3 "${SCRIPT_DIR}/prepare_runs.py" \
    --sync-params \
    --models "${MODEL_ID}" \
    --statepoints "${STATEPOINT_ID}" \
    --debug-queue

if [[ ! -f "${RUN_DIR}/run_lammps.cmd" ]]; then
    echo "ERROR: missing ${RUN_DIR}/run_lammps.cmd" >&2
    exit 1
fi

cd "${RUN_DIR}"
out="$(sbatch run_lammps.cmd)"
job_id="$(echo "${out}" | awk '/Submitted batch job/ {print $NF}')"
echo "Submitted debug LAMMPS: job=${job_id}"
echo "Monitor: squeue -j ${job_id}"
echo "Verify:  test -f ${RUN_DIR}/rdf.dat && head ${RUN_DIR}/rdf.dat"
