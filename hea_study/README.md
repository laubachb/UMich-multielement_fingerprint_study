# HEA study

High-entropy alloy fingerprint workflows across ChIMES α values.

## Tracked in git

| Path | Contents |
|------|----------|
| `alpha_*-histograms/*.sh`, `*.py` | Top-level workflow scripts only |
| `chimes_model/fm_setup.in` | Fitting setup |
| `chimes_model/run*.cmd` | ChIMES LSQ launch commands |
| `latent_space_visuals_expanded/` | HEA UMAP degeneracy figure + generation script |

CN shared parameters: `element_switching/model/params.txt` (not `chimes_model/params.txt`).

## Latent-space visualization

```bash
cd latent_space_visuals_expanded
python make_umap_degeneracy_expanded.py
```

Produces `umap_degeneracy_expanded.png` — a 2×5 UMAP panel (all frames + mixed-only
rows) across α = 0, 0.25, 0.50, 0.75, 1. Histograms are read from
`transfer_to_local-Apr2026/`; composition labels from `alpha_0-histograms/` cluster
files.

## Local data (gitignored)

- `alpha_*-histograms/frame_*/` — per-frame LAMMPS / histogram outputs
- `chimes_model/` — all fitting outputs except files above
- `frame_clusters/`, `lmp_setup/`, `transfer_to_local-Apr2026/`, `data/archives/`
