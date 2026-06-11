# HEA FPS α probe

Probe how ChIMES fingerprint α affects farthest-point sampling (FPS) on the
HEA corpus (~535 valid frames). Without thermodynamic statepoints, coverage is
measured in **fingerprint space**: hold-out similarity and neighborhood coverage
as a function of pruning (retention %).

## Quick start

```bash
module load python3
cd hea_study/fps_alpha_probe
python3 run_convergence_fps.py          # FPS grid + analysis + figures
python3 run_convergence_fps.py --skip-fps   # re-analyze existing FPS results
```

## Fingerprint coverage metrics

For each (FPS α, retention %, replicate), in the α-space used for sampling:

| Metric | Meaning |
|--------|---------|
| `mean_nn_cosine_sim` | Mean cosine similarity of each corpus frame to its nearest selected neighbor (higher = better representativeness) |
| `coverage_fraction` | Fraction of corpus within the 10th-percentile pairwise distance (local neighborhood radius) |
| `mean_nn_dist_norm` | Mean hold-out NN distance, normalized by corpus median pairwise distance |
| `max_nn_dist_norm` | Worst-case hold-out frame (farthest from any selected point) |
| `selected_spread_norm` | Internal diversity of the training subset |

Tables: `output/convergence/fingerprint_coverage_*.csv`

## Four macro figures

| Figure | Description |
|--------|-------------|
| `panel_convergence_summary.png` | 2×2: Jaccard(α=0 vs 1), neighborhood coverage, hold-out similarity, worst-case distance |
| `uniformity_coverage_heatmap.png` | FPS α × retention neighborhood coverage |
| `jaccard_heatmap_evolution.png` | Jaccard matrices at 10/20/30/50/70% |
| `coverage_fingerprint_x_retention.png` | Per-α heatmaps of similarity / coverage / distance vs pruning |

FPS selections: `../sampling/results_convergence_5pct/` (gitignored).

Composition-class analysis (`composition_coverage.py`) remains available for
supplementary checks but is not used in the macro figures.
