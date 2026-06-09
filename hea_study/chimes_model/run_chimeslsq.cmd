#!/bin/bash
#SBATCH -J test_LSQ
#SBATCH -N 2
#SBATCH --ntasks-per-node 112
#SBATCH -t 01:00:00
#SBATCH -p pdebug
#SBATCH -A pls2
#SBATCH -V 
#SBATCH -o stdoutmsg
module load cmake/3.21.1 intel-classic/2021.6.0-magic mvapich2/2.3.7 mkl
srun -n 224 /p/lustre1/laubach2/multielement_fingerprint_tests/chimes_lsq-LLfork/build/chimes_lsq test_setup.in | tee fm_setup.log
