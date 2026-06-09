import os
import re

# Root directory containing frame_* folders
ROOT_DIR = "."  # change if needed

# Counters
one_type_count = 0
two_type_count = 0

# Loop over all frame_* directories
for n in range(1, 569):  # 1 to 568 inclusive
    frame_dir = os.path.join(ROOT_DIR, f"frame_{n}")
    data_file = os.path.join(frame_dir, f"frame_{n}.data.in")
    lammps_in_file = os.path.join(frame_dir, "lammps.in")
    
    if not os.path.isfile(data_file):
        print(f"Skipping {data_file}, file does not exist.")
        continue
    if not os.path.isfile(lammps_in_file):
        print(f"Skipping {lammps_in_file}, file does not exist.")
        continue
    
    # Read the data file
    with open(data_file, "r") as f:
        lines = f.readlines()
    
    # Look for the line containing "atom types"
    atom_types = None
    for line in lines:
        if "atom types" in line:
            atom_types = int(line.strip().split()[0])
            break
    
    if atom_types is None:
        print(f"Could not find 'atom types' line in {data_file}")
        continue
    
    # Count atom types
    if atom_types == 1:
        one_type_count += 1
        print(f"{data_file} has 1 atom type → modifying {lammps_in_file}")
    elif atom_types == 2:
        two_type_count += 1

    # Read and modify the lammps.in file
    with open(lammps_in_file, "r") as f:
        in_lines = f.readlines()
    
    new_lines = []
    for line in in_lines:
        # Modify dump_modify line if single atom type
        if atom_types == 1 and line.startswith("dump_modify") and "sort id element" in line:
            line = re.sub(r"element\s+.*", "element Y", line)
        
        # Modify pair_coeff line to the new path
        if line.strip().startswith("pair_coeff") and "graphite_chimes_model_baseline/params.txt.reduced" in line:
            line = "pair_coeff    * * /work2/09982/blaubach/stampede3/multielement_study/hea_study/chimes_model/params.txt\n"
        
        new_lines.append(line)
    
    # Write back the modified file
    with open(lammps_in_file, "w") as f:
        f.writelines(new_lines)

# Print summary
print("\nSummary:")
print(f"Frames with 1 atom type: {one_type_count}")
print(f"Frames with 2 atom types: {two_type_count}")
