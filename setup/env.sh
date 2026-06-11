# Source from repo root (interactive or BATCH):
#   source setup/env.sh
#   source ~/multielement_study/setup/env.sh
#   source /work/09982/blaubach/stampede3/multielement_study/setup/env.sh
#
# Workflow scripts use:
#   source "${MULTIELEMENT_ROOT}/setup/env.sh"

# Always resolve from this file (works via ~/multielement_study symlink or explicit path).
_env_file="$(readlink -f "${BASH_SOURCE[0]}")"
_env_dir="$(cd "$(dirname "$_env_file")" && pwd)"
export MULTIELEMENT_ROOT="$(cd "$_env_dir/.." && pwd)"
unset _env_file _env_dir

if [[ -x "$MULTIELEMENT_ROOT/external/chimes_calculator/etc/lmp/exe/lmp_mpi_chimes" ]]; then
    export CHIMES_CALCULATOR="$MULTIELEMENT_ROOT/external/chimes_calculator"
elif [[ -x "$MULTIELEMENT_ROOT/chimes_calculator-myLLfork/etc/lmp/exe/lmp_mpi_chimes" ]]; then
    export CHIMES_CALCULATOR="$MULTIELEMENT_ROOT/chimes_calculator-myLLfork"
else
    export CHIMES_CALCULATOR="$MULTIELEMENT_ROOT/external/chimes_calculator"
fi
export LAMMPS_EXE="$CHIMES_CALCULATOR/etc/lmp/exe/lmp_mpi_chimes"
export HISTOGRAM_EXE="$CHIMES_CALCULATOR/chimesFF/src/FP/histogram"
export POST_PROCESS_SH="$CHIMES_CALCULATOR/chimesFF/src/FP/post_process.sh"

if [[ -x "$MULTIELEMENT_ROOT/external/chimes_lsq/build/chimes_lsq" ]]; then
    export CHIMES_LSQ="$MULTIELEMENT_ROOT/external/chimes_lsq"
elif [[ -x "$MULTIELEMENT_ROOT/chimes_lsq-LLfork/build/chimes_lsq" ]]; then
    export CHIMES_LSQ="$MULTIELEMENT_ROOT/chimes_lsq-LLfork"
else
    export CHIMES_LSQ="$MULTIELEMENT_ROOT/external/chimes_lsq"
fi
export CHIMES_LSQ_BIN="$CHIMES_LSQ/build/chimes_lsq"
export CHIMES_PARAMS="$MULTIELEMENT_ROOT/element_switching/model/params.txt"
export HEA_CHIMES_PARAMS="$MULTIELEMENT_ROOT/hea_study/chimes_model/params.txt"

# UMich-research_notes clone (NOT in this git repo). Used by Proj_C compute logging.
# Override in ~/.bashrc if your clone lives elsewhere.
export RESEARCH_NOTES_ROOT="${RESEARCH_NOTES_ROOT:-/work2/09982/blaubach/stampede3/multielement_study/UMich-research_notes}"
# Auto-commit/push Proj_C logs in research notes after sync (not multielement_study).
export RESEARCH_NOTES_AUTO_PUSH="${RESEARCH_NOTES_AUTO_PUSH:-1}"
