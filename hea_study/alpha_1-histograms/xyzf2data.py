import sys

def read_xyzf(filename):
    with open(filename, 'r') as file:
        lines = file.readlines()

    # Read the unit cell vectors from the second line
    cell_line = lines[1].strip().split()
    
    # Ensure it's in the format starting with NON_ORTHO
    if cell_line[0] != "NON_ORTHO":
        raise ValueError("Expected 'NON_ORTHO' keyword in the second line.")

    # Extract the lattice vectors A, B, C
    A = list(map(float, cell_line[1:4]))  # A vector
    B = list(map(float, cell_line[4:7]))  # B vector
    C = list(map(float, cell_line[7:10])) # C vector

    # Get number of atoms from the first line
    num_atoms = int(lines[0].strip())

    # Read the atomic positions from the next lines
    atom_lines = lines[2:2 + num_atoms]
    
    atoms = []
    for line in atom_lines:
        data = line.strip().split()
        element = data[0]  # Element name (e.g., Si)
        x, y, z = map(float, data[1:4])  # Positions (x, y, z)
        atoms.append((element, x, y, z))

    return A, B, C, atoms

def write_lammps_data(filename, A, B, C, atoms):
    with open(filename, 'w') as file:
        # Header section
        file.write("LAMMPS data file\n\n")
        file.write(f"{len(atoms)} atoms\n")
        file.write(f"{len(set(atom[0] for atom in atoms))} atom types\n\n")
        
        # Box dimensions based on the cell vectors
        file.write(f"0.0 {A[0]} xlo xhi\n")
        file.write(f"0.0 {B[1]} ylo yhi\n")
        file.write(f"0.0 {C[2]} zlo zhi\n")
        file.write(f"{A[1]} {A[2]} {B[2]} xy xz yz\n\n")
        
        # Masses (assuming atomic masses, can be customized)
        file.write("Masses\n\n")
        unique_elements = sorted(set(atom[0] for atom in atoms))
        element_masses = {"Mg": 24.305, "Y": 88.906}  # Example: add more if needed
        for i, element in enumerate(unique_elements, start=1):
            file.write(f"{i} {element_masses.get(element, 1.0)} # {element}\n")
        
        # Atoms section
        file.write("\nAtoms\n\n")
        for i, (element, x, y, z) in enumerate(atoms, start=1):
            atom_type = unique_elements.index(element) + 1
            file.write(f"{i} {atom_type} {x} {y} {z}\n")

if __name__ == "__main__":
    input_file = sys.argv[1]
    output_file = sys.argv[2]

    # Read xyzf file
    A, B, C, atoms = read_xyzf(input_file)
    
    # Write LAMMPS data file
    write_lammps_data(output_file, A, B, C, atoms)