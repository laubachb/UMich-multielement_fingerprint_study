#!/usr/bin/env bash
# Reorganize multielement_study for git without deleting data.
#   bash scripts/reorganize_repo.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "Reorganizing under $ROOT"

mkdir -p data/archives external \
         models/workflows/fingerprints \
         models/workflows/full_model \
         hea_study/workflows

# ── Move root archives ───────────────────────────────────────────────────────
shopt -s nullglob
for f in *.tar.gz *.zip; do
    echo "  archive: $f -> data/archives/"
    mv -n "$f" data/archives/
done
if [[ -f full_dft.xyzf ]]; then
    echo "  move: full_dft.xyzf -> data/"
    mv -n full_dft.xyzf data/
fi

# ── UMAP analysis scripts ────────────────────────────────────────────────────
UMAP_SRC="models/fingerprints/umap"
UMAP_DST="models/workflows/fingerprints/umap"
if [[ -d "$UMAP_SRC" && ! -L "$UMAP_SRC" ]]; then
    echo "  move: $UMAP_SRC -> $UMAP_DST"
    mkdir -p "$(dirname "$UMAP_DST")"
    mv "$UMAP_SRC" "$UMAP_DST"
    ln -s ../../workflows/fingerprints/umap "$UMAP_SRC"
elif [[ -L "$UMAP_SRC" ]]; then
    echo "  umap already symlinked"
else
    echo "  WARNING: $UMAP_SRC not found"
fi

# ── Relocate batch gen scripts; symlink back; keep .bak ───────────────────────
relocate_script() {
    local src="$1" dst_name="$2"
    [[ -f "$src" ]] || return 0
    if [[ -L "$src" ]]; then
        echo "  skip (already symlink): $src"
        return 0
    fi
    local dst="models/workflows/fingerprints/$dst_name"
    echo "  relocate: $src -> $dst"
    cp -a "$src" "$dst"
    mv "$src" "${src}.bak"
    ln -s "../workflows/fingerprints/$dst_name" "$src"
}

relocate_script models/fingerprints/a000_fingerprints/gen_hists.sh gen_hists_a000.sh
relocate_script models/fingerprints/a025_fingerprints/gen_hists.sh gen_hists_a025.sh
relocate_script models/fingerprints/a050_fingerprints/gen_hists.sh gen_hists_a050.sh
relocate_script models/fingerprints/a075_fingerprints/gen_hists.sh gen_hists_a075.sh
relocate_script models/fingerprints/a100_fingerprints/gen_hists.sh gen_hists_a100.sh
relocate_script models/fingerprints/a025_fingerprints/gen_missing_hists.sh gen_missing_hists_a025.sh
relocate_script models/fingerprints/a025_fingerprints/gen_missing_hists_debug.sh gen_missing_hists_debug_a025.sh
relocate_script models/fingerprints/debug-a000_fingerprints/gen_hists.sh gen_hists_debug_a000.sh
relocate_script models/fingerprints/debug-a100_fingerprints/gen_hists.sh gen_hists_debug_a100.sh

# ── Full-model scripts ─────────────────────────────────────────────────────────
for f in models/full_model/*.sh models/full_model/*.py; do
    [[ -f "$f" ]] || continue
    bn="$(basename "$f")"
    dst="models/workflows/full_model/$bn"
    if [[ ! -f "$dst" ]]; then
        echo "  copy: $f -> $dst"
        cp -a "$f" "$dst"
    fi
done

# ── HEA top-level workflow scripts ───────────────────────────────────────────
for d in hea_study/alpha_*-histograms; do
    [[ -d "$d" ]] || continue
    bn="$(basename "$d")"
    for s in gen_hist_all_frames.sh submit_lammps_jobs.sh convert_xyzf_to_data.sh \
             split_and_convert_xyzf.sh run_post_processclusters_each_directory.sh \
             copy_lammps_input.sh xyzf2data.py post_process_lammpsin_files.py; do
        [[ -f "$d/$s" ]] || continue
        dst="hea_study/workflows/${bn}_${s}"
        if [[ ! -f "$dst" ]]; then
            echo "  copy: $d/$s -> $dst"
            cp -a "$d/$s" "$dst"
        fi
    done
done

# ── HEA shared workflow scripts ──────────────────────────────────────────────
for d in hea_study/frame_clusters hea_study/lmp_setup; do
    [[ -d "$d" ]] || continue
    bn="$(basename "$d")"
    for s in *.sh *.py; do
        [[ -f "$d/$s" ]] || continue
        dst="hea_study/workflows/${bn}_${s}"
        if [[ ! -f "$dst" ]]; then
            echo "  copy: $d/$s -> $dst"
            cp -a "$d/$s" "$dst"
        fi
    done
done

# ── Fingerprint cluster helpers ──────────────────────────────────────────────
for s in models/fingerprints/clusters/*.sh models/fingerprints/clusters/*.py; do
    [[ -f "$s" ]] || continue
    bn="$(basename "$s")"
    dst="models/workflows/fingerprints/clusters_${bn}"
    if [[ ! -f "$dst" ]]; then
        echo "  copy: $s -> $dst"
        cp -a "$s" "$dst"
    fi
done

# ── Patch shell scripts to source setup/env.sh ───────────────────────────────
echo ""
bash "$ROOT/scripts/patch_workflow_paths.sh"

echo ""
echo "Reorganization complete."
echo "  - Archives -> data/archives/"
echo "  - Workflows -> models/workflows/, hea_study/workflows/"
echo "  - Original gen_*.sh kept as *.bak with symlinks at old paths"
echo "  - Source ChIMES: bash setup/install_chimes.sh && source setup/env.sh"
