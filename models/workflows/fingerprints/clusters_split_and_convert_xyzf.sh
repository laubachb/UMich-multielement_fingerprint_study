#!/bin/bash

# Input xyzf file
INPUT_FILE="rotated_full_dft.xyzf"

# Check if input file exists
if [[ ! -f "$INPUT_FILE" ]]; then
    echo "Error: Input file '$INPUT_FILE' not found."
    exit 1
fi

# Check if xyzf2data.py exists
if [[ ! -f "xyzf2data.py" ]]; then
    echo "Error: xyzf2data.py not found in current directory."
    exit 1
fi

echo "Starting to split and convert $INPUT_FILE..."

# Initialize variables
frame_number=0
line_number=0
total_lines=$(wc -l < "$INPUT_FILE")

# Read the file line by line
while IFS= read -r line || [[ -n "$line" ]]; do
    ((line_number++))

    # Check if this is the start of a new frame (atom count line)
    if [[ "$line" =~ ^[0-9]+$ ]]; then
        # Close previous frame if it exists
        if [[ $frame_number -gt 0 ]]; then
            exec 3>&-  # Close the file descriptor

            # Convert the split file to LAMMPS data format
            echo "  Converting frame_${frame_number}.xyzf to data file..."
            python xyzf2data.py "frame_${frame_number}/frame_${frame_number}.xyzf" "frame_${frame_number}/data.in"

            if [[ $? -eq 0 ]]; then
                echo "  Successfully converted frame_${frame_number}"
            else
                echo "  Error converting frame_${frame_number}"
            fi
        fi

        # Start new frame
        ((frame_number++))
        atom_count=$line

        # Create directory for this frame
        mkdir -p "frame_${frame_number}"

        echo "Processing frame $frame_number (${atom_count} atoms)..."

        # Open file descriptor for writing this frame
        exec 3>"frame_${frame_number}/frame_${frame_number}.xyzf"

        # Write atom count
        echo "$line" >&3
    else
        # Write line to current frame file
        echo "$line" >&3
    fi
done < "$INPUT_FILE"

# Close and convert the last frame
if [[ $frame_number -gt 0 ]]; then
    exec 3>&-

    echo "  Converting frame_${frame_number}.xyzf to data file..."
    python xyzf2data.py "frame_${frame_number}/frame_${frame_number}.xyzf" "frame_${frame_number}/frame_${frame_number}.data.in"

    if [[ $? -eq 0 ]]; then
        echo "  Successfully converted frame_${frame_number}"
    else
        echo "  Error converting frame_${frame_number}"
    fi
fi

echo ""
echo "Completed! Split into $frame_number frames."
echo "Each frame is in its own directory (frame_1, frame_2, etc.) with:"
echo "  - frame_N.xyzf (split xyzf file)"
echo "  - frame_N.data.in (converted LAMMPS data file)"
