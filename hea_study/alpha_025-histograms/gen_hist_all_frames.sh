#!/bin/bash
#SBATCH -J 025_hea_multi_frame_gen
#SBATCH -N 1
#SBATCH --ntasks-per-node 48
#SBATCH -t 02:00:00
#SBATCH -p skx-dev
#SBATCH -A TG-CHM250118
#SBATCH -o stdoutmsg

module load intel/24.0 impi/21.11 python

# Define paths
LAMMPS_EXE=/work/09982/blaubach/stampede3/multielement_study/chimes_calculator-myLLfork/etc/lmp/exe/lmp_mpi_chimes
HISTOGRAM_EXE=/work/09982/blaubach/stampede3/multielement_study/chimes_calculator-myLLfork/chimesFF/src/FP/histogram
PARAMS_FILE=/work2/09982/blaubach/stampede3/multielement_study/hea_study/chimes_model/params.txt
POST_PROCESS_SH=/work/09982/blaubach/stampede3/multielement_study/chimes_calculator-myLLfork/chimesFF/src/FP/post_process.sh
ALPHA=0.25

ROOT_DIR=$(pwd)

for dir in frame_*; do
    if [ -d "$dir" ]; then
        
        # Check if any .hist files exist in the directory
        # ls -1 lists files, 2>/dev/null hides errors if no files found
        if ls "$dir"/*.hist >/dev/null 2>&1; then
            echo "Skipping $dir: .hist file already exists."
            continue
        fi

        echo "--> Processing: $dir"
        cd "$dir" || { echo "Failed to enter $dir"; continue; }

        # Run Histogram generation (uncomment others if needed)
        # ibrun -n 48 $LAMMPS_EXE -i lammps.in | tee output.txt
        # sh $POST_PROCESS_SH
        ibrun -n 48 $HISTOGRAM_EXE $PARAMS_FILE $ALPHA > /dev/null 2>&1

        cd "$ROOT_DIR"
    fi
done

echo "All eligible frames processed."