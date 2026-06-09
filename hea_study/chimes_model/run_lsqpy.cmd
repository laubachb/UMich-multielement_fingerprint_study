#!/bin/bash
#SBATCH -J test_lsq
#SBATCH -N 2
#SBATCH -n 224
#SBATCH -t 1:00:00
#SBATCH -p pdebug
# SBATCH -A pls2
#SBATCH -V
#SBATCH -o stdoutmsg
#SBATCH -e erroutmsg
module load cmake/3.21.1
module load intel-classic/2021.6.0-magic
module load mvapich2/2.3.7
module load mkl
ml python
python3 /p/lustre1/laubach2/multielement_fingerprint_tests/chimes_lsq-LLfork/build/chimes_lsq.py --algorithm dlasso --alpha 1.0E-5 --nodes 2 --cores 224 --mpistyle srun  | tee params.txt
