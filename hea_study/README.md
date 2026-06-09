# HEA study

High-entropy alloy fingerprint workflows across ChIMES α values.

## Tracked in git

| Path | Contents |
|------|----------|
| `alpha_*-histograms/*.sh`, `*.py` | Top-level workflow scripts only |
| `chimes_model/fm_setup.in` | Fitting setup |
| `chimes_model/run*.cmd` | ChIMES LSQ launch commands |

CN shared parameters: `element_switching/model/params.txt` (not `chimes_model/params.txt`).

## Local data (gitignored)

- `alpha_*-histograms/frame_*/` — per-frame LAMMPS / histogram outputs
- `chimes_model/` — all fitting outputs except files above
- `frame_clusters/`, `lmp_setup/`, `transfer_to_local-Apr2026/`, `data/archives/`
