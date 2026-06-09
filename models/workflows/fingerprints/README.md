# CN fingerprint workflows

Batch scripts for generating ChIMES cluster histograms across the α sweep.

Run multi-frame jobs **from the corresponding data directory**, e.g.:

```bash
cd models/fingerprints/a025_fingerprints
sbatch gen_hists.sh          # symlink -> ../workflows/fingerprints/gen_hists_a025.sh
```

Requires `source setup/env.sh` (injected into scripts) and built ChIMES in `external/`.

| Script | α | Notes |
|--------|---|-------|
| `gen_hists_a000.sh` | 0.00 | composition only |
| `gen_hists_a025.sh` | 0.25 | |
| `gen_hists_a050.sh` | 0.50 | |
| `gen_hists_a075.sh` | 0.75 | |
| `gen_hists_a100.sh` | 1.00 | structure only |
| `gen_missing_hists_a025.sh` | 0.25 | incomplete frames only |
| `gen_missing_hists_debug_a025.sh` | 0.25 | skx-dev queue |

UMAP analysis: see `umap/`.
