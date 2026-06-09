#!/bin/bash
#SBATCH -J {{JOB_PREFIX}}_genA
#SBATCH -N {{NNODES}}
#SBATCH --ntasks-per-node {{NCORES}}
#SBATCH -t {{GEN_WALLTIME}}
#SBATCH -p {{PARTITION}}
#SBATCH -A TG-CHM250118
#SBATCH -o stdoutmsg_gen_%j
#SBATCH -e erroutmsg_gen_%j

set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"

export MULTIELEMENT_ROOT="${MULTIELEMENT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}"
source "${MULTIELEMENT_ROOT}/setup/env.sh"
module load intel/24.0 impi/21.11 python

if [[ -x "${CHIMES_LSQ}/build/chimes_lsq" ]]; then
    LSQ_EXE="${CHIMES_LSQ}/build/chimes_lsq"
else
    LSQ_EXE="${MULTIELEMENT_ROOT}/chimes_lsq-LLfork/build/chimes_lsq"
fi

ibrun -n {{NTASKS}} "${LSQ_EXE}" fm_setup.in | tee fm_setup.log
