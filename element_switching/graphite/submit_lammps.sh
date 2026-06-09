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

LAMMPS_EXE=/work2/09982/blaubach/stampede3/multielement_study/chimes_calculator-myLLfork/etc/lmp/exe/lmp_mpi_chimes

ibrun -n 48 $LAMMPS_EXE -i in.lammps | tee output.txt