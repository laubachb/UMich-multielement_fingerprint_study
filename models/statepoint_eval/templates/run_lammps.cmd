#!/bin/bash
#SBATCH -J {{JOB_NAME}}
#SBATCH -N 1
#SBATCH --ntasks-per-node {{NCORES}}
#SBATCH -t {{WALLTIME}}
#SBATCH -p {{PARTITION}}
#SBATCH -A TG-CHM250118
#SBATCH -o stdoutmsg_%j
#SBATCH -e erroutmsg_%j

set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"

export MULTIELEMENT_ROOT="{{MULTIELEMENT_ROOT}}"
source "${MULTIELEMENT_ROOT}/setup/env.sh"
module load intel/24.0 impi/21.11 python

ibrun -n {{NTASKS}} "${LAMMPS_EXE}" -i in.lammps | tee output.txt
