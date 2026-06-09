#!/bin/bash

# Configuration
BASE_DIR="$(pwd)"
LAMMPS_EXE="/p/lustre1/laubach2/multielement_fingerprint_tests/chimes_calculator-LLfork/etc/lmp/exe/lmp_mpi_chimes"
FRAMES_PER_JOB=25  # Number of frames to run per SLURM job

# Get all frame directories (sorted numerically)
frame_dirs=($(ls -d frame_*/ | sed 's:/$::' | sort -V))
total_frames=${#frame_dirs[@]}

echo "Found $total_frames frame directories"
echo "Batching into groups of $FRAMES_PER_JOB frames per job"

# Calculate number of jobs needed
num_jobs=$(( (total_frames + FRAMES_PER_JOB - 1) / FRAMES_PER_JOB ))
echo "Will create $num_jobs SLURM job(s)"
echo ""

# Loop through batches
for (( job_idx=0; job_idx<num_jobs; job_idx++ )); do
    # Calculate start and end indices for this batch
    start_idx=$(( job_idx * FRAMES_PER_JOB ))
    end_idx=$(( start_idx + FRAMES_PER_JOB ))
    if (( end_idx > total_frames )); then
        end_idx=$total_frames
    fi

    # Create submit script for this batch
    submit_file="$BASE_DIR/submit_batch_${job_idx}.slurm"

    echo "Creating batch $job_idx (frames $start_idx to $((end_idx-1)))..."

    cat > "$submit_file" << EOF
#!/bin/bash
#SBATCH -J hea_frames_batch_${job_idx}
#SBATCH -N 1
#SBATCH --ntasks-per-node 112
#SBATCH -t 1:00:00
#SBATCH -p pdebug
#SBATCH -A pls2
#SBATCH -o ${BASE_DIR}/slurm_batch_${job_idx}_%j.out
#SBATCH -e ${BASE_DIR}/slurm_batch_${job_idx}_%j.err

module load cmake intel impi

echo "=========================================="
echo "Starting LAMMPS batch $job_idx"
echo "Job ID: \${SLURM_JOB_ID}"
echo "Node: \${SLURMD_NODENAME}"
echo "Date: \$(date)"
echo "=========================================="
echo ""

EOF

    # Add commands for each frame in this batch
    for (( i=start_idx; i<end_idx; i++ )); do
        frame_dir="${frame_dirs[$i]}"

        # Check if lammps.in exists
        if [[ -f "$BASE_DIR/$frame_dir/lammps.in" ]]; then
            # Check if output files already exist (skip if completed)
            if ! ls "$BASE_DIR/$frame_dir"/*.hist &> /dev/null; then
                cat >> "$submit_file" << EOF
echo "Running $frame_dir..."
cd "$BASE_DIR/$frame_dir"
srun -N 1 -n 112 "$LAMMPS_EXE" -i lammps.in > out.lammps 2>&1
echo "  Completed $frame_dir"
echo ""

EOF
            else
                echo "  ⚠️  Skipping $frame_dir (already has .hist files)"
            fi
        else
            echo "  ⚠️  Skipping $frame_dir (no lammps.in file)"
        fi
    done

    cat >> "$submit_file" << 'EOF'
echo "=========================================="
echo "Batch completed: $(date)"
echo "=========================================="
EOF

    # Submit the job if there are srun commands in it
    if grep -q "srun" "$submit_file"; then
        chmod +x "$submit_file"
        sbatch "$submit_file"
        echo "✅ Submitted batch $job_idx (${submit_file})"
    else
        echo "⚠️  No frames to run in batch $job_idx, skipping submission."
        rm "$submit_file"
    fi
    echo ""
done

echo "=========================================="
echo "All batches submitted!"
echo "Monitor with: squeue -u \$USER"
echo "=========================================="
