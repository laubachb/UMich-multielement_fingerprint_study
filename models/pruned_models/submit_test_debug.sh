#!/usr/bin/env bash
# Submit a single 1% retention gen→solve chain on skx-dev for validation.
#
#   cd models/pruned_models
#   bash submit_test_debug.sh
#   bash submit_test_debug.sh a100_pct001_rep02

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNS_DIR="${SCRIPT_DIR}/runs"
RUN_NAME="${1:-a100_pct001_rep02}"
RUN_DIR="${RUNS_DIR}/${RUN_NAME}"

if [[ ! -d "${RUN_DIR}" ]]; then
    echo "Missing run directory: ${RUN_DIR}" >&2
    exit 1
fi

# Fresh test: remove prior submission marker and partial outputs
rm -f "${RUN_DIR}/submitted.json"
rm -f "${RUN_DIR}/params.txt" "${RUN_DIR}/solve.err"

cd "${RUN_DIR}"
echo "Test run: ${RUN_NAME} (partition=$(grep '^#SBATCH -p' run_gen_Amat.cmd | awk '{print $2}'))"

gen_id="$(sbatch run_gen_Amat.cmd | awk '/Submitted batch job/ {print $NF}')"
solve_id="$(sbatch --dependency=afterok:"${gen_id}" run_solve_Amat.cmd | awk '/Submitted batch job/ {print $NF}')"

printf '{"gen_job": %s, "solve_job": %s, "test": true}\n' "${gen_id}" "${solve_id}" > submitted.json
echo "Submitted test chain: gen=${gen_id} solve=${solve_id}"
echo "Monitor: squeue -u \$USER"
echo "Verify:  test -f ${RUN_DIR}/params.txt && grep ENDFILE ${RUN_DIR}/params.txt"
