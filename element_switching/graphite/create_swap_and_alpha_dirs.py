import random
import math
import os
import subprocess
import shutil

# -----------------------------
# User settings
# -----------------------------
input_file = "graphite_1500K_#0262.xyzf"
xyzf2data_script = "xyzf2data.py"         # must be in current working directory
output_root = "fingerprints"
output_prefix = "graphite_1500K_0262"
increment = 0.25        # 5% increments
max_fraction = 1.0     # go up to 25%

# Alpha directory settings
alpha_min = 0           # minimum alpha value (will be formatted as alpha_000)
alpha_max = 100         # maximum alpha value (will be formatted as alpha_100)
alpha_step = 25          # step size for alpha values

# Files to copy into each alpha directory
files_to_copy = ["in.lammps"]  # Add any other files you need copied
# -----------------------------


# Read file
with open(input_file, "r") as f:
    lines = f.readlines()

# Find all carbon atom lines
atom_indices = [
    i for i, line in enumerate(lines)
    if line.strip().startswith("C ")
]

num_c = len(atom_indices)
print(f"Found {num_c} C atoms.")

# Shuffle carbon atom list once for cumulative selection
random.shuffle(atom_indices)

# Number of steps = 0% → 25% inclusive
num_steps = int(max_fraction / increment)

# Ensure output root directory exists
os.makedirs(output_root, exist_ok=True)

for step in range(0, num_steps + 1):     # include 0%
    fraction = step * increment          # 0.00 → 0.25
    pct = int(fraction * 100)            # 0 → 25

    num_to_convert = math.floor(fraction * num_c)
    selected = set(atom_indices[:num_to_convert])

    # Create directory
    subdir = os.path.join(output_root, f"{output_prefix}_{pct}pct")
    os.makedirs(subdir, exist_ok=True)

    # Output xyzf file
    out_xyzf = os.path.join(subdir, f"{output_prefix}_{pct}pct.xyzf")

    # Modify lines
    new_lines = lines.copy()
    for idx in selected:
        new_lines[idx] = new_lines[idx].replace("C ", "N ", 1)

    # Write xyzf file
    with open(out_xyzf, "w") as f:
        f.writelines(new_lines)

    print(f"Created: {out_xyzf}  ({num_to_convert}/{num_c} C atoms converted)")

    # Convert xyzf → data.in
    out_data = os.path.join(subdir, f"generic.data.in")

    cmd = ["python3", xyzf2data_script, out_xyzf, out_data]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)

    # Copy in.lammps to the percentage directory
    cp_cmd_in_lammps = ["cp", "in.lammps", subdir]
    print("Running:", " ".join(cp_cmd_in_lammps))
    subprocess.run(cp_cmd_in_lammps, check=True)

    # Special case: 0pct folder → remove N from dump_modify
    if pct == 0:
        in_lammps_path = os.path.join(subdir, "in.lammps")

        with open(in_lammps_path, "r") as f:
            lammps_lines = f.readlines()

        lammps_lines = [
            line.replace(
                "dump_modify     1 sort id element C N",
                "dump_modify     1 sort id element C"
            )
            for line in lammps_lines
        ]

        with open(in_lammps_path, "w") as f:
            f.writelines(lammps_lines)

        print("Updated dump_modify line for 0pct folder")

    print(f"Generated: {out_data}")

    # ================================
    # Create alpha subdirectories
    # ================================
    print(f"\nCreating alpha subdirectories in {subdir}...")

    for alpha_val in range(alpha_min, alpha_max + 1, alpha_step):
        # Format alpha value with leading zeros (e.g., 005, 010, 100)
        alpha_dir_name = f"alpha_{alpha_val:03d}"
        alpha_dir_path = os.path.join(subdir, alpha_dir_name)

        # Create alpha directory
        os.makedirs(alpha_dir_path, exist_ok=True)

        # Copy generic.data.in to alpha directory
        src_data = out_data
        dst_data = os.path.join(alpha_dir_path, "generic.data.in")
        shutil.copy2(src_data, dst_data)

        # Copy in.lammps from the percentage directory to alpha directory
        src_lammps = os.path.join(subdir, "in.lammps")
        dst_lammps = os.path.join(alpha_dir_path, "in.lammps")
        shutil.copy2(src_lammps, dst_lammps)

        # Copy any additional files specified
        for file_to_copy in files_to_copy:
            if file_to_copy != "in.lammps":  # Already copied above
                if os.path.exists(file_to_copy):
                    dst_file = os.path.join(alpha_dir_path, os.path.basename(file_to_copy))
                    shutil.copy2(file_to_copy, dst_file)

        print(f"  Created {alpha_dir_name}")

    print(f"Finished creating alpha directories for {pct}pct\n")

print("\n" + "="*60)
print("All percentage directories and alpha subdirectories created successfully!")
print("="*60)
