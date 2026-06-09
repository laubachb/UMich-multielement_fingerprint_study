#!/bin/bash
#SBATCH -J {{JOB_PREFIX}}_solve
#SBATCH -N {{NNODES}}
#SBATCH --ntasks-per-node {{NCORES}}
#SBATCH -t {{SOLVE_WALLTIME}}
#SBATCH -p {{PARTITION}}
#SBATCH -A TG-CHM250118
#SBATCH -o stdoutmsg_solve_%j
#SBATCH -e erroutmsg_solve_%j

set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"

export MULTIELEMENT_ROOT="${MULTIELEMENT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}"
source "${MULTIELEMENT_ROOT}/setup/env.sh"
module load intel/24.0 impi/21.11 python

if [[ -f "${CHIMES_LSQ}/build/chimes_lsq.py" ]]; then
    LSQ_PY="${CHIMES_LSQ}/build/chimes_lsq.py"
else
    LSQ_PY="${MULTIELEMENT_ROOT}/chimes_lsq-LLfork/build/chimes_lsq.py"
fi

python3 "${LSQ_PY}" \
    --algorithm dlasso \
    --alpha 1.0E-5 \
    --nodes {{NNODES}} \
    --cores {{NTASKS}} \
    --mpistyle ibrun | tee solve.log
