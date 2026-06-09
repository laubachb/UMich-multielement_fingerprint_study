#!/bin/bash

# Root directory containing frame_* folders
ROOT_DIR="/work/09982/blaubach/stampede3/multielement_study/hea_study/frame_clusters"  # change if needed

# Path to the post_process.sh script
POST_PROCESS_SCRIPT="/work2/09982/blaubach/stampede3/multielement_study/chimes_calculator-myLLfork/chimesFF/src/FP/post_process.sh"

# Make sure the script is executable
if [ ! -x "$POST_PROCESS_SCRIPT" ]; then
    echo "Error: $POST_PROCESS_SCRIPT is not executable!"
    exit 1
fi

# Loop over frame_* directories
for n in {1..568}; do
    FRAME_DIR="$ROOT_DIR/frame_$n"
    
    if [ -d "$FRAME_DIR" ]; then
        echo "Running post_process.sh in $FRAME_DIR"
        cd "$FRAME_DIR" || continue
        
        # Call the post_process script
        "$POST_PROCESS_SCRIPT"
        
        # Return to root directory
        cd "$ROOT_DIR" || exit
    else
        echo "Skipping $FRAME_DIR (directory does not exist)"
    fi
done