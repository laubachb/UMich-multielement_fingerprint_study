#!/bin/bash

# Loop through all frame directories
for dir in frame_*/; do
    # Remove trailing slash
    dir=${dir%/}

    # Extract frame number from directory name
    frame_num=${dir#frame_}

    # Define the output file
    output_file="$dir/lammps.in"

    echo "Creating LAMMPS input for $dir..."

    # Create the LAMMPS input file with the correct read_data line
    cat > "$output_file" << 'EOF'
########################################
########################################
# Water at 300 K - Example for fingerprint generation (using a very bad model!)
########################################
########################################


##########################################
# USER-SPECIFIED VARIABLES
##########################################

variable temp    equal 300    # Temperature (K)
variable seed       equal 1111    # Random seed
variable iofrq   equal 1    # Output frequency: thermo and trajectory MUST use same value if using Active learning driver
variable delt    equal 0.2    # Timestep (fs)
variable nstep   equal 0    # Number of steps for simulation


########################################
# GENERAL CONTROLS
########################################

units           real                          # Required for CHIMES pair style
newton          on                            # Required for CHIMES pair style
atom_style      atomic                        # Required for CHIMES pair style
atom_modify     sort 0 0.0                    # Required for CHIMES pair style
atom_modify     map array                     # Required for CHIMES pair style

neighbor        1.0 bin
neigh_modify    delay 0 every 1 check yes     # Required for CHIMES pair style


########################################
# INITIALIZATION CONTROLS
########################################

read_data       "PLACEHOLDER_DATAFILE"
velocity        all create ${temp} ${seed} loop all mom yes rot yes dist gaussian


########################################
# FORCE FIELD CONTROLS
########################################

pair_style    chimesFF fingerprint 1
pair_coeff    * * /p/lustre1/laubach2/multielement_fingerprint_tests/graphite_chimes_model_baseline/params.txt.reduced

########################################
# RUN, DUMP, AND THERMO CONTROLS
########################################

thermo_style    custom step time ke pe etotal temp press pxx pyy pzz pxy pxz pyz vol
thermo_modify   line one format float %20.5f flush yes
thermo          ${iofrq}

dump            1 all custom ${iofrq} traj.lammpstrj element xu yu zu fx fy fz
dump_modify     1 sort id element Y Mg

timestep        ${delt}
run             ${nstep}

EOF

    # Replace the placeholder with the correct data file name
    sed -i '' "s/PLACEHOLDER_DATAFILE/frame_${frame_num}.data.in/" "$output_file"

done

echo ""
echo "Completed! Created lammps.in files in all frame directories."
