#!/usr/bin/env python3
"""Convert a single-frame .xyzf file to a LAMMPS data file (C/N, triclinic)."""

from __future__ import annotations

import sys
from pathlib import Path

ELEMENT_MASSES = {"C": 12.011, "N": 14.007}


def read_xyzf(filename: Path):
    lines = filename.read_text(encoding="utf-8").splitlines()
    cell_line = lines[1].strip().split()
    if cell_line[0] != "NON_ORTHO":
        raise ValueError("Expected 'NON_ORTHO' keyword in the second line.")

    a = list(map(float, cell_line[1:4]))
    b = list(map(float, cell_line[4:7]))
    c = list(map(float, cell_line[7:10]))
    num_atoms = int(lines[0].strip())

    atoms = []
    for line in lines[2 : 2 + num_atoms]:
        parts = line.split()
        element = parts[0]
        x, y, z = map(float, parts[1:4])
        atoms.append((element, x, y, z))

    return a, b, c, atoms


def write_lammps_data(filename: Path, a, b, c, atoms) -> None:
    unique_elements = sorted({atom[0] for atom in atoms})
    with filename.open("w", encoding="utf-8") as handle:
        handle.write("LAMMPS data file\n\n")
        handle.write(f"{len(atoms)} atoms\n")
        handle.write(f"{len(unique_elements)} atom types\n\n")
        handle.write(f"0.0 {a[0]} xlo xhi\n")
        handle.write(f"0.0 {b[1]} ylo yhi\n")
        handle.write(f"0.0 {c[2]} zlo zhi\n")
        handle.write(f"{b[0]} {c[0]} {c[1]} xy xz yz\n\n")
        handle.write("Masses\n\n")
        for i, element in enumerate(unique_elements, start=1):
            mass = ELEMENT_MASSES.get(element, 1.0)
            handle.write(f"{i} {mass} # {element}\n")
        handle.write("\nAtoms\n\n")
        for i, (element, x, y, z) in enumerate(atoms, start=1):
            atom_type = unique_elements.index(element) + 1
            handle.write(f"{i} {atom_type} {x} {y} {z}\n")


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(f"Usage: {sys.argv[0]} input.xyzf output.data.in")

    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])
    a, b, c, atoms = read_xyzf(input_file)
    write_lammps_data(output_file, a, b, c, atoms)


if __name__ == "__main__":
    main()
