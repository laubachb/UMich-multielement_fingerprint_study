#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt
import glob
import os
import csv

# Base directory where fingerprints are stored
BASE_DIR = "./fingerprints"
PCT_DIRS = ["graphite_1500K_0262_0pct",
            "graphite_1500K_0262_25pct",
            "graphite_1500K_0262_50pct",
            "graphite_1500K_0262_75pct",
            "graphite_1500K_0262_100pct"]

# Prepare figure
fig, axes = plt.subplots(nrows=5, ncols=1, figsize=(8, 12))
viridis = plt.cm.viridis

csv_out = "graphite_1500K_0262-fingerprints_combined.csv"
with open(csv_out, "w", newline="") as f:
    writer = csv.writer(f)

    for i, pct_dir in enumerate(PCT_DIRS):
        full_pct_dir = os.path.join(BASE_DIR, pct_dir)
        ax = axes[i]
        ax.set_title(pct_dir)

        # Find all alpha directories
        alpha_dirs = sorted(
            glob.glob(os.path.join(full_pct_dir, "alpha_*")),
            key=lambda x: int(os.path.basename(x).split("_")[1])
        )

        for j, alpha_dir in enumerate(alpha_dirs):
            alpha_name = os.path.basename(alpha_dir)

            hist_files = sorted(
                glob.glob(os.path.join(alpha_dir, "*-0.*b_clu-s.hist"))
            )

            combined_vector = []

            for hf in hist_files:
                data = np.loadtxt(hf, usecols=1)
                combined_vector.extend(data.tolist())

            # Write ONE row per pct + alpha
            writer.writerow([pct_dir, alpha_name] + combined_vector)

            # Plot
            color = viridis(j / max(len(alpha_dirs) - 1, 1))
            ax.plot(combined_vector, label=alpha_name, color=color)

        ax.set_xlabel("Index")
        ax.set_ylabel("Counts")
        ax.legend(fontsize=8)

plt.tight_layout()
plt.savefig("test.png")

print(f"Saved CSV data to: {csv_out}")
