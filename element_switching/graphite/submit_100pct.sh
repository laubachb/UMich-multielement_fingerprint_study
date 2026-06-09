#!/bin/bash
#SBATCH -J run_100pct_graphite
#SBATCH -N 1
#SBATCH --ntasks-per-node 48
#SBATCH -t 01:00:00
#SBATCH -p skx-dev
#SBATCH -A TG-CHM250118
#SBATCH -V
#SBATCH -o stdoutmsg

module load intel/24.0 impi/21.11 python

BASEDIR=$(pwd)
ERROR_LOG="$BASEDIR/run_errors_100pct.log"
SUCCESS_LOG="$BASEDIR/run_summary_100pct.log"

# Clear previous logs
> "$ERROR_LOG"
> "$SUCCESS_LOG"

echo "Starting 100pct alpha job run..." | tee -a "$SUCCESS_LOG"
echo "Running from base directory: $BASEDIR" | tee -a "$SUCCESS_LOG"
echo "Error log: $ERROR_LOG" | tee -a "$SUCCESS_LOG"
echo "" | tee -a "$SUCCESS_LOG"

# Executables
LAMMPS_EXE=/work2/09982/blaubach/stampede3/multielement_study/chimes_calculator-myLLfork/etc/lmp/exe/lmp_mpi_chimes
HISTOGRAM_EXE=/work2/09982/blaubach/stampede3/multielement_study/chimes_calculator-myLLfork/chimesFF/src/FP/histogram
PARAMS_FILE=/work2/09982/blaubach/stampede3/multielement_study/element_switching/model/params.txt
POST_PROCESS_SH=/work2/09982/blaubach/stampede3/multielement_study/chimes_calculator-myLLfork/chimesFF/src/FP/post_process.sh

# Counters
TOTAL_ALPHA_DIRS=0
SUCCESS_ALPHA_DIRS=0
FAILED_ALPHA_DIRS=0

# Only process 100pct directory
gdir="fingerprints/graphite_1500K_0262_100pct"
if [ ! -d "$gdir" ]; then
    echo "ERROR: $gdir not found" | tee -a "$ERROR_LOG"
    exit 1
fi

echo "==========================================" | tee -a "$SUCCESS_LOG"
echo "Processing $gdir" | tee -a "$SUCCESS_LOG"
echo "==========================================" | tee -a "$SUCCESS_LOG"

# Reference alpha directory
REF_ALPHA_DIR="$BASEDIR/$gdir/alpha_000"
if [ ! -d "$REF_ALPHA_DIR" ]; then
    echo "ERROR: Reference directory $REF_ALPHA_DIR not found" | tee -a "$ERROR_LOG"
    exit 1
fi

cd "$REF_ALPHA_DIR" || { echo "ERROR: Cannot cd to $REF_ALPHA_DIR" | tee -a "$ERROR_LOG"; exit 1; }

echo "  Running LAMMPS in alpha_000..." | tee -a "$SUCCESS_LOG"
ibrun -n 48 $LAMMPS_EXE -i in.lammps > /dev/null 2>&1
LAMMPS_EXIT=$?

if [ $LAMMPS_EXIT -ne 0 ]; then
    echo "ERROR: LAMMPS failed for $gdir (exit code: $LAMMPS_EXIT)" | tee -a "$ERROR_LOG"
    exit 1
fi
echo "  LAMMPS completed successfully" | tee -a "$SUCCESS_LOG"

# Generate combined cluster files
bash $POST_PROCESS_SH > /dev/null 2>&1
# Optional: check POST_EXIT if needed

if [ ! -f "0.all-2b-clusters.txt" ] || [ ! -f "0.all-3b-clusters.txt" ] || [ ! -f "0.all-4b-clusters.txt" ]; then
    echo "ERROR: Cluster files not generated in $gdir/alpha_000" | tee -a "$ERROR_LOG"
    exit 1
fi
echo "  Cluster files generated successfully in alpha_000" | tee -a "$SUCCESS_LOG"

# Copy cluster files and run histogram in all alpha directories
for adir in "$BASEDIR/$gdir"/alpha_*; do
    TOTAL_ALPHA_DIRS=$((TOTAL_ALPHA_DIRS + 1))
    adir_name=$(basename "$adir")

    # Copy cluster files if not alpha_000
    if [ "$adir_name" != "alpha_000" ]; then
        cp "$REF_ALPHA_DIR/0.all-2b-clusters.txt" "$adir/" 2>/dev/null
        cp "$REF_ALPHA_DIR/0.all-3b-clusters.txt" "$adir/" 2>/dev/null
        cp "$REF_ALPHA_DIR/0.all-4b-clusters.txt" "$adir/" 2>/dev/null

        if [ ! -f "$adir/0.all-2b-clusters.txt" ] || [ ! -f "$adir/0.all-3b-clusters.txt" ] || [ ! -f "$adir/0.all-4b-clusters.txt" ]; then
            echo "ERROR: Failed to copy cluster files to $gdir/$adir_name" >> "$ERROR_LOG"
            FAILED_ALPHA_DIRS=$((FAILED_ALPHA_DIRS + 1))
            continue
        fi
        echo "    Copied cluster files to $adir_name" >> "$SUCCESS_LOG"
    fi

    # Run histogram in all alpha directories including alpha_000
    RAW_ALPHA=${adir_name#alpha_}
    ALPHA=$(echo "$RAW_ALPHA" | awk '{printf "%.2f", $1/100}')

    echo "    Running histogram for $adir_name (alpha=$ALPHA)..." >> "$SUCCESS_LOG"
    cd "$adir" || continue
    ibrun -n 48 $HISTOGRAM_EXE $PARAMS_FILE $ALPHA > /dev/null 2>&1
    cd "$BASEDIR"

    SUCCESS_ALPHA_DIRS=$((SUCCESS_ALPHA_DIRS + 1))
done

echo "" | tee -a "$SUCCESS_LOG"
echo "==========================================" | tee -a "$SUCCESS_LOG"
echo "Processing of 100pct directory completed." | tee -a "$SUCCESS_LOG"
echo "Alpha directories:" | tee -a "$SUCCESS_LOG"
echo "  Total: $TOTAL_ALPHA_DIRS" | tee -a "$SUCCESS_LOG"
echo "  Successful: $SUCCESS_ALPHA_DIRS" | tee -a "$SUCCESS_LOG"
echo "  Failed: $FAILED_ALPHA_DIRS" | tee -a "$SUCCESS_LOG"
echo "==========================================" | tee -a "$SUCCESS_LOG"
echo "Check $ERROR_LOG for error details" | tee -a "$SUCCESS_LOG"
echo "Job complete!" | tee -a "$SUCCESS_LOG"
