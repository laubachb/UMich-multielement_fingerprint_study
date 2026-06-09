#!/bin/bash
#SBATCH -J 025_missing_hist_dbg
#SBATCH -N 1
#SBATCH --ntasks-per-node 48
#SBATCH -t 2:00:00
#SBATCH -p skx-dev
#SBATCH -A TG-CHM250118
#SBATCH -o stdoutmsg_missing_hists_debug
source "${MULTIELEMENT_ROOT:-/work/09982/blaubach/stampede3/multielement_study}/setup/env.sh"

module load intel/24.0 impi/21.11 python

LAMMPS_EXE="${LAMMPS_EXE}"
HISTOGRAM_EXE="${HISTOGRAM_EXE}"
PARAMS_FILE="${CHIMES_PARAMS}"
POST_PROCESS_SH="${POST_PROCESS_SH}"
ALPHA=0.25

ROOT_DIR=$(pwd)

MISSING_FRAMES=(
    frame_9
    frame_80
    frame_81
    frame_82
    frame_83
    frame_84
    frame_85
    frame_86
    frame_87
    frame_88
    frame_89
    frame_90
    frame_91
    frame_92
    frame_93
    frame_94
    frame_95
    frame_96
    frame_97
    frame_98
    frame_99
)

for dir in "${MISSING_FRAMES[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "Skipping $dir: directory not found."
        continue
    fi

    if [ -f "$dir/0-0.4b_clu-s.hist" ]; then
        echo "Skipping $dir: 0-0.4b_clu-s.hist already exists."
        continue
    fi

    for body in 2b 3b 4b; do
        if [ ! -f "$dir/0.all-${body}-clusters.txt" ]; then
            echo "Skipping $dir: missing 0.all-${body}-clusters.txt"
            continue 2
        fi
    done

    echo "--> Processing: $dir"
    cd "$dir" || { echo "Failed to enter $dir"; continue; }

    ibrun -n 48 $HISTOGRAM_EXE $PARAMS_FILE $ALPHA > /dev/null 2>&1

    cd "$ROOT_DIR"
done

echo "Missing-frame histogram generation complete."
