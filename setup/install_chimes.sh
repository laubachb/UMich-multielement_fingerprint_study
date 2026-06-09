#!/usr/bin/env bash
# Clone Lindsey Lab ChIMES forks into external/ and build.
#
#   bash setup/install_chimes.sh
#
# https://github.com/LindseyLab-umich/chimes_calculator-LLfork
# https://github.com/LindseyLab-umich/chimes_lsq-LLfork

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXT="$ROOT/external"
CALC_REPO="https://github.com/LindseyLab-umich/chimes_calculator-LLfork.git"
LSQ_REPO="https://github.com/LindseyLab-umich/chimes_lsq-LLfork.git"

mkdir -p "$EXT"

clone_or_update() {
    local url="$1" dest="$2"
    if [[ -d "$dest/.git" ]]; then
        echo "Updating $(basename "$dest")..."
        git -C "$dest" pull --ff-only
    else
        echo "Cloning $(basename "$dest")..."
        git clone "$url" "$dest"
    fi
}

clone_or_update "$CALC_REPO" "$EXT/chimes_calculator"
clone_or_update "$LSQ_REPO" "$EXT/chimes_lsq"

echo ""
echo "Building chimes_calculator (LAMMPS + histogram)..."
if [[ -f "$EXT/chimes_calculator/etc/lmp/install.sh" ]]; then
    (cd "$EXT/chimes_calculator/etc/lmp" && bash install.sh)
else
    echo "  WARNING: etc/lmp/install.sh not found; build manually."
fi

echo ""
echo "Building chimes_lsq..."
if [[ -f "$EXT/chimes_lsq/install.sh" ]]; then
    (cd "$EXT/chimes_lsq" && bash install.sh)
else
    echo "  WARNING: install.sh not found; build manually."
fi

echo ""
echo "Done. Source environment with:"
echo "  source $ROOT/setup/env.sh"
