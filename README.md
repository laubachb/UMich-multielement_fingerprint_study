# Multielement ChIMES study

Workflows for carbon–nitrogen (CN) and high-entropy alloy (HEA) ChIMES fingerprint
generation, UMAP analysis, farthest-point sampling, and model fitting.

**This repository tracks scripts only.** Large simulation outputs (fingerprints,
trajectories, fitted models) live at the paths in [`data/README.md`](data/README.md)
and are gitignored.

## Repository layout

```
multielement_study/
├── setup/                   environment + ChIMES install
├── data/                    repo-root archives + layout docs
├── scripts/                 reorganize / cleanup helpers
├── element_switching/       CN params + graphite/liquid scripts (tracked)
│   └── data/                local outputs (gitignored)
├── models/
│   ├── workflows/           ONLY tracked part of models/
│   └── fingerprints/        a*_fingerprints/ data (gitignored)
├── hea_study/
│   ├── alpha_*-histograms/  top-level *.sh / *.py only (tracked)
│   ├── chimes_model/        fm_setup.in + run*.cmd only (tracked)
│   └── data/                archives + frame outputs (gitignored)
└── external/                cloned ChIMES forks (gitignored)
```

Shared ChIMES parameters for CN: `element_switching/model/params.txt`.

Legacy `chimes_calculator-myLLfork/` and `chimes_lsq-LLfork/` may exist locally;
they are gitignored. Fresh installs use `external/` via `setup/install_chimes.sh`.

## Quick start

```bash
bash setup/install_chimes.sh
source setup/env.sh

cd models/fingerprints/a025_fingerprints
sbatch gen_hists.sh

cd models/workflows/fingerprints/umap
python analyze_alpha_umap.py
```

## One-time reorganization

```bash
bash scripts/reorganize_repo.sh
```

## Initialize git

```bash
git init
git add README.md .gitignore setup/ data/ scripts/ element_switching/ models/ hea_study/
git status
git commit -m "Initial commit: multielement ChIMES workflows"
```

## Dependencies

- [chimes_calculator-LLfork](https://github.com/LindseyLab-umich/chimes_calculator-LLfork)
- [chimes_lsq-LLfork](https://github.com/LindseyLab-umich/chimes_lsq-LLfork)
