#!/bin/bash
#SBATCH -J run_all_alphas_graphited
#SBATCH -N 1
#SBATCH --ntasks-per-node 48
#SBATCH -t 01:00:00
#SBATCH -p skx-dev
#SBATCH -A TG-CHM250118
#SBATCH -V
#SBATCH -o /dev/null

module load intel/24.0 impi/21.11 python

BASEDIR=$(pwd)
ERROR_LOG="$BASEDIR/run_errors.log"
SUCCESS_LOG="$BASEDIR/run_summary.log"

# Clear previous logs
> "$ERROR_LOG"
> "$SUCCESS_LOG"

echo "Starting optimized alpha job run..." | tee -a "$SUCCESS_LOG"
echo "Running from base directory: $BASEDIR" | tee -a "$SUCCESS_LOG"
echo "Error log: $ERROR_LOG" | tee -a "$SUCCESS_LOG"
echo "" | tee -a "$SUCCESS_LOG"

# Executables
LAMMPS_EXE=/work2/09982/blaubach/stampede3/multielement_study/chimes_calculator-myLLfork/etc/lmp/exe/lmp_mpi_chimes
HISTOGRAM_EXE=/work2/09982/blaubach/stampede3/multielement_study/chimes_calculator-myLLfork/chimesFF/src/FP/histogram
PARAMS_FILE=/work2/09982/blaubach/stampede3/multielement_study/element_switching/model/params.txt
POST_PROCESS_SH=/work2/09982/blaubach/stampede3/multielement_study/chimes_calculator-myLLfork/chimesFF/src/FP/post_process.sh

# Counters
TOTAL_PCT_DIRS=0
SUCCESS_PCT_DIRS=0
FAILED_PCT_DIRS=0
TOTAL_ALPHA_DIRS=0
SUCCESS_ALPHA_DIRS=0
FAILED_ALPHA_DIRS=0

# Loop over all graphite percentage directories
for gdir in fingerprints/*pct; do
    TOTAL_PCT_DIRS=$((TOTAL_PCT_DIRS + 1))

    echo "==========================================" | tee -a "$SUCCESS_LOG"
    echo "Processing $gdir" | tee -a "$SUCCESS_LOG"
    echo "==========================================" | tee -a "$SUCCESS_LOG"

    # Use alpha_000 as the reference directory for LAMMPS run
    REF_ALPHA_DIR="$BASEDIR/$gdir/alpha_000"

    if [ ! -d "$REF_ALPHA_DIR" ]; then
        echo "ERROR: Reference directory $REF_ALPHA_DIR not found" | tee -a "$ERROR_LOG"
        FAILED_PCT_DIRS=$((FAILED_PCT_DIRS + 1))
        continue
    fi

    cd "$REF_ALPHA_DIR" || {
        echo "ERROR: Cannot cd to $REF_ALPHA_DIR" | tee -a "$ERROR_LOG"
        FAILED_PCT_DIRS=$((FAILED_PCT_DIRS + 1))
        continue
    }

    echo "  Running LAMMPS in alpha_000..." | tee -a "$SUCCESS_LOG"

    # Run LAMMPS once per percentage directory
    ibrun -n 48 $LAMMPS_EXE -i in.lammps > /dev/null 2>&1
    LAMMPS_EXIT=$?

    if [ $LAMMPS_EXIT -ne 0 ]; then
        echo "ERROR: LAMMPS failed for $gdir (exit code: $LAMMPS_EXIT)" | tee -a "$ERROR_LOG"
        FAILED_PCT_DIRS=$((FAILED_PCT_DIRS + 1))
        cd "$BASEDIR"
        continue
    fi
    echo "  LAMMPS completed successfully" | tee -a "$SUCCESS_LOG"

    # echo "  Running post_process.sh..." | tee -a "$SUCCESS_LOG"

    Run post_process.sh to generate combined cluster files
    bash $POST_PROCESS_SH > /dev/null 2>&1
    # POST_EXIT=$?

    # if [ $POST_EXIT -ne 0 ]; then
    #     echo "ERROR: post_process.sh failed for $gdir (exit code: $POST_EXIT)" | tee -a "$ERROR_LOG"
    #     FAILED_PCT_DIRS=$((FAILED_PCT_DIRS + 1))
    #     cd "$BASEDIR"
    #     continue
    # fi
    # echo "  post_process.sh completed successfully" | tee -a "$SUCCESS_LOG"

    # Check that cluster files were created
    if [ ! -f "0.all-2b-clusters.txt" ] || \
       [ ! -f "0.all-3b-clusters.txt" ] || \
       [ ! -f "0.all-4b-clusters.txt" ]; then
        echo "ERROR: Cluster files not generated in $gdir/alpha_000" | tee -a "$ERROR_LOG"
        FAILED_PCT_DIRS=$((FAILED_PCT_DIRS + 1))
        cd "$BASEDIR"
        continue
    fi

    SUCCESS_PCT_DIRS=$((SUCCESS_PCT_DIRS + 1))
    echo "  Cluster files generated successfully" | tee -a "$SUCCESS_LOG"

    # Copy cluster files to all other alpha directories and run histogram
    echo "  Copying cluster files to other alpha directories and running histogram..." | tee -a "$SUCCESS_LOG"

    for adir in "$BASEDIR/$gdir"/alpha_*; do
        TOTAL_ALPHA_DIRS=$((TOTAL_ALPHA_DIRS + 1))
        adir_name=$(basename "$adir")

        # Copy cluster files if not alpha_000
        if [ "$adir_name" != "alpha_000" ]; then
            cp "$REF_ALPHA_DIR/0.all-2b-clusters.txt" "$adir/" 2>/dev/null
            cp "$REF_ALPHA_DIR/0.all-3b-clusters.txt" "$adir/" 2>/dev/null
            cp "$REF_ALPHA_DIR/0.all-4b-clusters.txt" "$adir/" 2>/dev/null

            # Verify files were copied
            if [ ! -f "$adir/0.all-2b-clusters.txt" ] || \
            [ ! -f "$adir/0.all-3b-clusters.txt" ] || \
            [ ! -f "$adir/0.all-4b-clusters.txt" ]; then
                echo "ERROR: Failed to copy cluster files to $gdir/$adir_name" >> "$ERROR_LOG"
                FAILED_ALPHA_DIRS=$((FAILED_ALPHA_DIRS + 1))
                continue
            fi

            echo "    Copied to $adir_name" >> "$SUCCESS_LOG"
        fi

        # Extract alpha value for histogram calculation
        RAW_ALPHA=${adir_name#alpha_}
        ALPHA=$(echo "$RAW_ALPHA" | awk '{printf "%.2f", $1/100}')

        # Run histogram in every alpha directory, including alpha_000
        echo "    Running histogram for $adir_name (alpha=$ALPHA)..." >> "$SUCCESS_LOG"
        cd "$adir" || continue
        ibrun -n 48 $HISTOGRAM_EXE $PARAMS_FILE $ALPHA > /dev/null 2>&1
        cd "$BASEDIR"

        SUCCESS_ALPHA_DIRS=$((SUCCESS_ALPHA_DIRS + 1))
    done


    cd "$BASEDIR"
done

echo "" | tee -a "$SUCCESS_LOG"
echo "==========================================" | tee -a "$SUCCESS_LOG"
echo "Processing completed." | tee -a "$SUCCESS_LOG"
echo "==========================================" | tee -a "$SUCCESS_LOG"
echo "Percentage directories:" | tee -a "$SUCCESS_LOG"
echo "  Total: $TOTAL_PCT_DIRS" | tee -a "$SUCCESS_LOG"
echo "  Successful: $SUCCESS_PCT_DIRS" | tee -a "$SUCCESS_LOG"
echo "  Failed: $FAILED_PCT_DIRS" | tee -a "$SUCCESS_LOG"
echo "" | tee -a "$SUCCESS_LOG"
echo "Alpha directories:" | tee -a "$SUCCESS_LOG"
echo "  Total: $TOTAL_ALPHA_DIRS" | tee -a "$SUCCESS_LOG"
echo "  Successful: $SUCCESS_ALPHA_DIRS" | tee -a "$SUCCESS_LOG"
echo "  Failed: $FAILED_ALPHA_DIRS" | tee -a "$SUCCESS_LOG"
echo "==========================================" | tee -a "$SUCCESS_LOG"
echo "" | tee -a "$SUCCESS_LOG"
echo "Check $ERROR_LOG for error details" | tee -a "$SUCCESS_LOG"
echo "Job complete!" | tee -a "$SUCCESS_LOG"
