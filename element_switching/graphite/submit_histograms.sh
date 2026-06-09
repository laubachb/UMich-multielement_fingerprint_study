#!/bin/bash
#SBATCH -J graphite_1500K_0262_20pct
#SBATCH -N 1
#SBATCH --ntasks-per-node 48
#SBATCH -t 01:00:00
#SBATCH -p skx-dev
#SBATCH -A TG-CHM250118
#SBATCH -V
#SBATCH -o stdoutmsg

module load intel/24.0 impi/21.11 python

HISTOGRAM_EXE=/work2/09982/blaubach/stampede3/multielement_study/chimes_calculator-myLLfork/chimesFF/src/FP/histogram
PARAMS_FILE=/work2/09982/blaubach/stampede3/multielement_study/element_switching/model/params.txt

ibrun -n 48 $HISTOGRAM_EXE $PARAMS_FILE 1.0

# /p/lustre1/laubach2/multielement_fingerprint_tests/chimes_calculator-LLfork/chimesFF/src/FP/histogram /p/lustre1/laubach2/multielement_fingerprint_tests/graphite_chimes_model_baseline/params.txt.reduced 0.5
