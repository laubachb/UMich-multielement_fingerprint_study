#!/bin/bash
#SBATCH -J full_dft-model_training
#SBATCH -N 1
#SBATCH --ntasks-per-node 112
#SBATCH -t 24:00:00
#SBATCH -p spr
#SBATCH -A TG-CHM250118
#SBATCH -V
#SBATCH -o stdoutmsg
source "${MULTIELEMENT_ROOT:-/work/09982/blaubach/stampede3/multielement_study}/setup/env.sh"

module load intel/24.0 impi/21.11 python

ibrun -n 112 ${CHIMES_LSQ_BIN}
