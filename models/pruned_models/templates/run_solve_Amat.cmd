#!/bin/bash
#SBATCH -J {{JOB_PREFIX}}_solve
#SBATCH -N {{NNODES}}
#SBATCH --ntasks-per-node {{NCORES}}
#SBATCH -t {{SOLVE_WALLTIME}}
#SBATCH -p {{PARTITION}}
#SBATCH -A TG-CHM250118
#SBATCH -o stdoutmsg_solve_%j
#SBATCH -e erroutmsg_solve_%j

set -uo pipefail
cd "${SLURM_SUBMIT_DIR}"

export MULTIELEMENT_ROOT="{{MULTIELEMENT_ROOT}}"
source "${MULTIELEMENT_ROOT}/setup/env.sh"
module load intel/24.0 impi/21.11 python

if [[ -f "${CHIMES_LSQ}/build/chimes_lsq.py" ]]; then
    LSQ_PY="${CHIMES_LSQ}/build/chimes_lsq.py"
else
    LSQ_PY="${MULTIELEMENT_ROOT}/chimes_lsq-LLfork/build/chimes_lsq.py"
fi

_exit=0
python3 "${LSQ_PY}" \
    --algorithm dlasso \
    --alpha 1.0E-5 \
    --nodes {{NNODES}} \
    --cores {{NTASKS}} \
    --mpistyle ibrun > params.txt 2> solve.err || _exit=$?

if [[ "${_exit}" -eq 0 ]] && ! grep -q ENDFILE params.txt; then
    echo "ERROR: params.txt missing ENDFILE marker" >&2
    _exit=1
fi
if [[ "${_exit}" -eq 0 ]]; then
    echo "Wrote params.txt ($(wc -l < params.txt) lines)"
fi

"${MULTIELEMENT_ROOT}/scripts/log_compute_event.sh" chimes_solve "${SLURM_SUBMIT_DIR}" "${_exit}" || true
exit "${_exit}"
