# CN element-switching figure (graphite)

Stacked fingerprint plot for progressive C→N substitution in graphite at 1500 K,
across the ChIMES α sweep.

## Generate

```bash
cd element_switching/cn_switching_image
python make_cn_switching_figure.py
```

Requires histogram data under `../data/graphite/fingerprints/graphite_1500K_0262_*pct/alpha_*/`.

## Output (tracked in git)

| File | Description |
|------|-------------|
| `cn_switching_fingerprints.png` | 5 composition panels × 5 α curves (viridis colorbar) |
