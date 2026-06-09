# Data layout

Large simulation outputs are **not tracked in git**. Place (or generate) datasets under the
repository root using the paths below.

## Carbon–nitrogen (CN) fingerprints — `models/fingerprints/`

```
models/fingerprints/
  a000_fingerprints/frame_*/
  a025_fingerprints/frame_*/
  a050_fingerprints/frame_*/
  a075_fingerprints/frame_*/
  a100_fingerprints/frame_*/
```

Each `frame_N/` directory should contain LAMMPS inputs, cluster files, and `*.hist`
fingerprints after running workflows in `models/workflows/fingerprints/`.

## HEA study — `hea_study/`

```
hea_study/
  alpha_0-histograms/frame_*/
  alpha_025-histograms/frame_*/
  ...
  chimes_model/params.txt
  data/
```

## Element-switching reference structures — `element_switching/`

```
element_switching/
  model/params.txt
  graphite/fingerprints/
  liquid/fingerprints/
```

## Archives

Loose `.tar.gz` / `.zip` bundles are stored in `data/archives/` (gitignored).
