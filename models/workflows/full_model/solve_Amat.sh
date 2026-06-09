#!/bin/bash
#SBATCH -J full_dft-solve_Amat
#SBATCH -N 1
#SBATCH --ntasks-per-node 112
#SBATCH -t 12:00:00
#SBATCH -p spr
#SBATCH -A TG-CHM250118
#SBATCH -V
#SBATCH -o stdoutmsg
source "${MULTIELEMENT_ROOT:-/work/09982/blaubach/stampede3/multielement_study}/setup/env.sh"

# Load any modules you need
module load intel/24.0 impi/21.11 python

BASE="${CHIMES_LSQ_BIN}"
EXEC="$BASE/chimes_lsq"
PY="$BASE/chimes_lsq.py"

python3 $PY --algorithm dlasso --alpha 1.0E-5 --nodes 1 --cores 112 --mpistyle ibrun | tee params.txt
