#!/bin/bash

# Parent directory containing all the subdirectories (same as before)
base_dir="/p/lustre1/laubach2/multielement_fingerprint_tests/chimes_pruning/fingerprints/multielement"

# Path to xyzf2data.py (assumed to be in your current working directory)
xyzf2data_path="$(pwd)/xyzf2data.py"

# Check that the Python script exists
if [[ ! -f "$xyzf2data_path" ]]; then
    echo "❌ xyzf2data.py not found in current directory: $xyzf2data_path"
    exit 1
fi

# Loop through each subdirectory
for dir in "$base_dir"/*; do
    [[ -d "$dir" ]] || continue  # skip if not a directory

    echo "📂 Entering directory: $dir"

    # Loop over all .xyzf files inside this directory
    for xyzf_file in "$dir"/*.xyzf; do
        [[ -e "$xyzf_file" ]] || continue  # skip if none exist

        # Derive output file name (.data.in)
        output_file="${xyzf_file%.xyzf}.data.in"

        echo "➡️ Converting $(basename "$xyzf_file") → $(basename "$output_file")"

        # Run the Python converter
        python "$xyzf2data_path" "$xyzf_file" "$output_file"
    done
done

echo "✅ All .xyzf files have been converted to .data.in files."
