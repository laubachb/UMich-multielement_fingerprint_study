# Element switching (CN reference)

Workflows for C/N element-switching fingerprint tests on graphite and liquid
reference structures.

## Tracked in git

| Path | Contents |
|------|----------|
| `graphite/*.py`, `graphite/*.sh`, `graphite/in.lammps` | Graphite workflows |
| `liquid/*.py`, `liquid/*.sh`, `liquid/in.lammps` | Liquid workflows |
| `model/params.txt` | Shared ChIMES parameter file (used by CN fingerprints) |

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
