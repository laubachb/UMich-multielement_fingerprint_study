#!/usr/bin/env python3
"""
Rotate .xyzf frames to standard upper-triangular box format.
Transforms box from arbitrary (Ax,Ay,Az, Bx,By,Bz, Cx,Cy,Cz) to (Ax',0,0, Bx',By',0, Cx',Cy',Cz')
"""

import numpy as np
import sys

def gram_schmidt_qr(box_vectors):
    """
    Compute rotation matrix to transform box to upper triangular form.
    Uses QR decomposition where Q is the rotation matrix.

    Args:
        box_vectors: 3x3 matrix where rows are A, B, C vectors

    Returns:
        R: Upper triangular box matrix
        Q: Rotation matrix (Q.T is what we apply to coordinates)
    """
    # QR decomposition: box_vectors = Q @ R
    # We want R to be upper triangular with positive diagonal
    Q, R = np.linalg.qr(box_vectors.T)

    # Ensure positive diagonal elements in R
    signs = np.sign(np.diag(R))
    signs[signs == 0] = 1
    Q = Q @ np.diag(signs)
    R = np.diag(signs) @ R

    return R.T, Q.T

def validate_rotation(old_box, new_box, old_positions, new_positions, tolerance=1e-6):
    """
    Validate that rotation preserves distances and volume.

    Returns:
        dict with validation results
    """
    results = {}

    # Check volume preservation
    old_volume = np.abs(np.linalg.det(old_box))
    new_volume = np.abs(np.linalg.det(new_box))
    volume_error = abs(old_volume - new_volume) / old_volume
    results['volume_preserved'] = volume_error < tolerance
    results['volume_error'] = volume_error
    results['old_volume'] = old_volume
    results['new_volume'] = new_volume

    # Check that new box is upper triangular
    results['is_upper_triangular'] = (
        abs(new_box[0, 1]) < tolerance and
        abs(new_box[0, 2]) < tolerance and
        abs(new_box[1, 2]) < tolerance
    )

    # Check interatomic distances (sample a few pairs)
    n_atoms = len(old_positions)
    if n_atoms > 10:
        # Sample 10 pairs
        indices = np.random.choice(n_atoms, min(10, n_atoms), replace=False)
        max_dist_error = 0.0

        for i in range(len(indices) - 1):
            idx1, idx2 = indices[i], indices[i + 1]

            # Distance in old coordinates
            old_dist = np.linalg.norm(old_positions[idx1] - old_positions[idx2])

            # Distance in new coordinates
            new_dist = np.linalg.norm(new_positions[idx1] - new_positions[idx2])

            dist_error = abs(old_dist - new_dist) / (old_dist + 1e-10)
            max_dist_error = max(max_dist_error, dist_error)

        results['distances_preserved'] = max_dist_error < tolerance
        results['max_distance_error'] = max_dist_error
    else:
        results['distances_preserved'] = True
        results['max_distance_error'] = 0.0

    return results

def process_xyzf_file(input_file, output_file, validate=True):
    """
    Process .xyzf file and rotate all frames to upper triangular box format.
    """
    with open(input_file, 'r') as fin, open(output_file, 'w') as fout:
        frame_num = 0
        validation_failures = []

        while True:
            # Read number of atoms
            line = fin.readline()
            if not line:
                break

            n_atoms = int(line.strip())
            fout.write(line)

            # Read box line
            box_line = fin.readline()
            parts = box_line.split()

            if parts[0] != "NON_ORTHO":
                raise ValueError(f"Frame {frame_num}: Expected NON_ORTHO, got {parts[0]}")

            # Parse box vectors
            box_values = [float(x) for x in parts[1:10]]
            old_box = np.array([
                [box_values[0], box_values[1], box_values[2]],  # A vector
                [box_values[3], box_values[4], box_values[5]],  # B vector
                [box_values[6], box_values[7], box_values[8]]   # C vector
            ])

            # Read atom data
            atom_lines = []
            old_positions = []
            elements = []
            forces = []

            for i in range(n_atoms):
                atom_line = fin.readline()
                atom_parts = atom_line.split()
                elements.append(atom_parts[0])
                old_positions.append([float(atom_parts[1]), float(atom_parts[2]), float(atom_parts[3])])
                forces.append([float(atom_parts[4]), float(atom_parts[5]), float(atom_parts[6])])
                atom_lines.append(atom_line)

            old_positions = np.array(old_positions)
            forces = np.array(forces)

            # Compute rotation
            new_box, rotation_matrix = gram_schmidt_qr(old_box)

            # Apply rotation to atomic positions
            new_positions = old_positions @ rotation_matrix.T

            # Validate if requested
            if validate:
                validation = validate_rotation(old_box, new_box, old_positions, new_positions)
                if not (validation['volume_preserved'] and
                        validation['is_upper_triangular'] and
                        validation['distances_preserved']):
                    validation_failures.append((frame_num, validation))

            # Write new box line
            fout.write(f"NON_ORTHO {new_box[0,0]:.10f} {new_box[0,1]:.10f} {new_box[0,2]:.10f} ")
            fout.write(f"{new_box[1,0]:.10f} {new_box[1,1]:.10f} {new_box[1,2]:.10f} ")
            fout.write(f"{new_box[2,0]:.10f} {new_box[2,1]:.10f} {new_box[2,2]:.10f}\n")

            # Write atom lines with rotated positions (forces stay the same for now)
            for i in range(n_atoms):
                fout.write(f"{elements[i]:8s} {new_positions[i,0]:15.8f} {new_positions[i,1]:15.8f} {new_positions[i,2]:15.8f} ")
                fout.write(f"{forces[i,0]:15.8f} {forces[i,1]:15.8f} {forces[i,2]:15.8f}\n")

            frame_num += 1
            if frame_num % 100 == 0:
                print(f"Processed {frame_num} frames...")

        print(f"\nTotal frames processed: {frame_num}")

        if validation_failures:
            print(f"\nWARNING: {len(validation_failures)} frames failed validation:")
            for frame_idx, validation in validation_failures[:5]:  # Show first 5
                print(f"  Frame {frame_idx}:")
                print(f"    Volume preserved: {validation['volume_preserved']}")
                print(f"    Upper triangular: {validation['is_upper_triangular']}")
                print(f"    Distances preserved: {validation['distances_preserved']}")
        else:
            print("\nAll validations passed!")

if __name__ == "__main__":
    input_file = "full_dft.xyzf"
    output_file = "rotated_full_dft.xyzf"

    print(f"Rotating frames in {input_file}...")
    print(f"Output will be written to {output_file}")
    print()

    process_xyzf_file(input_file, output_file, validate=True)
    print(f"\nDone! Rotated file saved as {output_file}")
