# Element switching (CN reference)

Workflows for C/N element-switching fingerprint tests on graphite and liquid
reference structures.

## Tracked in git

| Path | Contents |
|------|----------|
| `graphite/*.py`, `graphite/*.sh`, `graphite/in.lammps` | Graphite workflows |
| `liquid/*.py`, `liquid/*.sh`, `liquid/in.lammps` | Liquid workflows |
| `model/params.txt` | Shared ChIMES parameter file (used by CN fingerprints) |
| `cn_switching_image/` | Element-switching fingerprint figure + generation script |

## CN switching figure

```bash
cd cn_switching_image
python make_cn_switching_figure.py
```

Produces `cn_switching_fingerprints.png` — stacked panels for 0–100% N substitution
in graphite, with α-colored fingerprint curves (viridis). Data:
`data/graphite/fingerprints/`.

## Local data (gitignored)

Generated outputs and structures live under `data/`:

```
data/
  graphite/     # xyzf, csv, logs, plots moved from graphite/
  liquid/       # xyzf, csv, logs, fingerprints/ moved from liquid/
  archives/     # model.tar.gz
```

Run fingerprint jobs from `graphite/` or `liquid/`; outputs land in `fingerprints/`
subdirs (also gitignored).
