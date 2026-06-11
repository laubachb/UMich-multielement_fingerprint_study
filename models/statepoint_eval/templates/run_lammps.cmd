#!/bin/bash
#SBATCH -J {{JOB_NAME}}
#SBATCH -N 1
#SBATCH --ntasks-per-node {{NCORES}}
#SBATCH -t {{WALLTIME}}
#SBATCH -p {{PARTITION}}
#SBATCH -A TG-CHM250118
#SBATCH -o stdoutmsg_%j
#SBATCH -e erroutmsg_%j

set -uo pipefail
cd "${SLURM_SUBMIT_DIR}"

export MULTIELEMENT_ROOT="{{MULTIELEMENT_ROOT}}"
source "${MULTIELEMENT_ROOT}/setup/env.sh"
module load intel/24.0 impi/21.11 python

if [[ ! -x "${LAMMPS_EXE}" ]]; then
    echo "ERROR: LAMMPS_EXE not found or not executable: ${LAMMPS_EXE}" >&2
    exit 127
fi

_exit=0
ibrun -n {{NTASKS}} "${LAMMPS_EXE}" -i in.lammps | tee output.txt || _exit=$?

"${MULTIELEMENT_ROOT}/scripts/log_compute_event.sh" statepoint_md "${SLURM_SUBMIT_DIR}" "${_exit}" || true
exit "${_exit}"
