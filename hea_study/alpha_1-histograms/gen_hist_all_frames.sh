#!/bin/bash
#SBATCH -J 100_hea_multi_frame_gen
#SBATCH -N 1
#SBATCH --ntasks-per-node 48
#SBATCH -t 02:00:00          # Increased time for multiple frames
#SBATCH -p skx-dev 
#SBATCH -A TG-CHM250118
#SBATCH -o stdoutmsg_%j      # Added job ID to output for better tracking

# Load environment
module load intel/24.0 impi/21.11 python

# Define paths
LAMMPS_EXE=/work2/09982/blaubach/stampede3/multielement_study/chimes_calculator-myLLfork/etc/lmp/exe/lmp_mpi_chimes
HISTOGRAM_EXE=/work2/09982/blaubach/stampede3/multielement_study/chimes_calculator-myLLfork/chimesFF/src/FP/histogram
PARAMS_FILE=/work2/09982/blaubach/stampede3/multielement_study/hea_study/chimes_model/params.txt
POST_PROCESS_SH=/work2/09982/blaubach/stampede3/multielement_study/chimes_calculator-myLLfork/chimesFF/src/FP/post_process.sh
ALPHA=1.0

# Iterate through all directories starting with "frame_"
for dir in frame_*; do
    if [ -d "$dir" ]; then
        echo "--> Entering: $dir"
        
        # Move into the directory, run commands, then move back
        cd "$dir" || { echo "Failed to enter $dir"; continue; }

        # 1. Run LAMMPS
        # ibrun -n 48 $LAMMPS_EXE -i lammps.in | tee output.txt

        # # 2. Run Post-Processing script
        # sh $POST_PROCESS_SH

        # # 3. Run Histogram generation
        # ibrun $HISTOGRAM_EXE $PARAMS_FILE $ALPHA > /dev/null 2>&1
        ibrun -n 48 $HISTOGRAM_EXE $PARAMS_FILE $ALPHA > /dev/null 2>&1

        # Return to parent directory to find the next frame
        cd ..
    else
        echo "No directories matching frame_* found."
    fi
done

echo "All frames processed."