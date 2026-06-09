#!/usr/bin/env bash
# Tidy element_switching, models, and hea_study for git (no deletions).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "Cleaning layout under $ROOT"

mkdir -p element_switching/data/archives \
         element_switching/data/graphite \
         element_switching/data/liquid \
         models/data/archives \
         hea_study/data/archives

# ── element_switching/model ──────────────────────────────────────────────────
if [[ -f element_switching/model.tar.gz ]]; then
    echo "  move: element_switching/model.tar.gz -> element_switching/data/archives/"
    mv -n element_switching/model.tar.gz element_switching/data/archives/
fi

# ── element_switching/graphite ───────────────────────────────────────────────
for f in element_switching/graphite/*; do
    [[ -e "$f" ]] || continue
    bn="$(basename "$f")"
    case "$bn" in
        *.py|*.sh|in.lammps) continue ;;
        *)
            echo "  move: $f -> element_switching/data/graphite/"
            mv -n "$f" element_switching/data/graphite/
            ;;
    esac
done

# ── element_switching/liquid ─────────────────────────────────────────────────
for f in element_switching/liquid/*; do
    [[ -e "$f" ]] || continue
    bn="$(basename "$f")"
    case "$bn" in
        *.py|*.sh|in.lammps) continue ;;
        *)
            echo "  move: $f -> element_switching/data/liquid/"
            mv -n "$f" element_switching/data/liquid/
            ;;
    esac
done

# ── models: archive loose tarballs at fingerprints level ──────────────────────
for f in models/fingerprints/*.tar.gz models/*.tar.gz; do
    [[ -f "$f" ]] || continue
    echo "  move: $f -> models/data/archives/"
    mv -n "$f" models/data/archives/
done

# ── hea_study: archive root tarballs and non-alpha clutter ───────────────────
for f in hea_study/*.tar.gz; do
    [[ -f "$f" ]] || continue
    echo "  move: $f -> hea_study/data/archives/"
    mv -n "$f" hea_study/data/archives/
done
if [[ -f hea_study/hea_chimes_format.xyzf ]]; then
    echo "  move: hea_study/hea_chimes_format.xyzf -> hea_study/data/archives/"
    mv -n hea_study/hea_chimes_format.xyzf hea_study/data/archives/
fi

echo ""
echo "Cleanup complete. Generator scripts remain in place; outputs moved to data/ subdirs."
