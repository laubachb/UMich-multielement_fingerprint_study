#!/usr/bin/env bash
# Replace hardcoded Stampede paths; insert setup/env.sh after #SBATCH headers.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_SOURCE='source "${MULTIELEMENT_ROOT:-'"$ROOT"'}/setup/env.sh"'

patch_file() {
    local f="$1"
    [[ -f "$f" ]] || return 0
    grep -qE 'chimes_calculator|chimes_lsq|multielement_study' "$f" || return 0

    echo "  patch: $f"
    local tmp
    tmp="$(mktemp)"

    awk -v envsource="$ENV_SOURCE" '
        BEGIN { env_done=0; skip_old_env=0 }
        /^source .*setup\/env\.sh/ { next }
        /^LAMMPS_EXE=\/work/ { print "LAMMPS_EXE=\"${LAMMPS_EXE}\""; next }
        /^HISTOGRAM_EXE=\/work/ { print "HISTOGRAM_EXE=\"${HISTOGRAM_EXE}\""; next }
        /^POST_PROCESS_SH=\/work/ { print "POST_PROCESS_SH=\"${POST_PROCESS_SH}\""; next }
        /^PARAMS_FILE=.*element_switching/ { print "PARAMS_FILE=\"${CHIMES_PARAMS}\""; next }
        /\/work.*chimes_lsq/ { gsub(/\/work[^"]*chimes_lsq[^"]*/, "${CHIMES_LSQ_BIN}"); print; next }
        /\/work.*hea_study\/chimes_model\/params\.txt/ {
            gsub(/\/work[^"]*hea_study\/chimes_model\/params\.txt/, "${HEA_CHIMES_PARAMS}"); print; next
        }
        /^#SBATCH/ { print; next }
        /^#SBATCH/ || in_sbatch { print; if ($0 !~ /^#/) in_sbatch=0; next }
        {
            if (!env_done && $0 !~ /^#/ && $0 !~ /^$/) {
                print envsource
                env_done=1
            }
            print
        }
    ' "$f" > "$tmp"

    # Simpler pass: if no env line yet, insert after last #SBATCH line
    if ! grep -q 'setup/env.sh' "$tmp"; then
        awk -v envsource="$ENV_SOURCE" '
            /^#SBATCH/ { print; last_sbatch=NR; next }
            NR == last_sbatch + 1 && !done { print envsource; done=1 }
            { print }
        ' "$f" > "$tmp"
    fi

    chmod --reference="$f" "$tmp" 2>/dev/null || true
    mv "$tmp" "$f"
}

while IFS= read -r -d '' f; do
    patch_file "$f"
done < <(find "$ROOT/models/workflows" "$ROOT/hea_study/workflows" -type f -name '*.sh' -print0 2>/dev/null)

echo "Path patching complete."
