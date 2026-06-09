#!/bin/bash
#SBATCH -J 000_CN_multi_frame_gen
#SBATCH -N 2
#SBATCH --ntasks-per-node 48
#SBATCH -t 24:00:00
#SBATCH -p skx
#SBATCH -A TG-CHM250118
#SBATCH -o stdoutmsg
source "${MULTIELEMENT_ROOT:-/work/09982/blaubach/stampede3/multielement_study}/setup/env.sh"

module load intel/24.0 impi/21.11 python

# Define paths
LAMMPS_EXE="${LAMMPS_EXE}"
HISTOGRAM_EXE="${HISTOGRAM_EXE}"
PARAMS_FILE="${CHIMES_PARAMS}"
POST_PROCESS_SH="${POST_PROCESS_SH}"
ALPHA=0.5

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
        ibrun -n 96 $HISTOGRAM_EXE $PARAMS_FILE $ALPHA > /dev/null 2>&1

        cd "$ROOT_DIR"
    fi
done

echo "All eligible frames processed."
