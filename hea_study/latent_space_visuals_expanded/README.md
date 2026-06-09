# HEA latent-space UMAP (expanded)

2×5 UMAP degeneracy figure for the HEA fingerprint α sweep (Y–Mg system).

## Generate

```bash
cd hea_study/latent_space_visuals_expanded
python make_umap_degeneracy_expanded.py
```

Requires histogram data under `../transfer_to_local-Apr2026/alpha_*-histograms/`
and cluster files under `../alpha_0-histograms/frame_*/` for composition labels.

## Output (tracked in git)

| File | Description |
|------|-------------|
| `umap_degeneracy_expanded.png` | 2×5 panels: all frames (row 0) and mixed only (row 1) |

Row 0 colors frames by composition (Y-only, Mg-only, Mixed). Row 1 shows mixed
frames with degeneracy annotations (gold cluster, ellipse at α=1, arrows at α=0).
