# Source from workflow scripts:
#   source "${MULTIELEMENT_ROOT}/setup/env.sh"
#
# Or set MULTIELEMENT_ROOT before sourcing:
#   export MULTIELEMENT_ROOT=/path/to/multielement_study

if [[ -z "${MULTIELEMENT_ROOT:-}" ]]; then
    _env_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    export MULTIELEMENT_ROOT="$(cd "$_env_dir/.." && pwd)"
    unset _env_dir
fi

export CHIMES_CALCULATOR="${CHIMES_CALCULATOR:-$MULTIELEMENT_ROOT/external/chimes_calculator}"
export CHIMES_LSQ="${CHIMES_LSQ:-$MULTIELEMENT_ROOT/external/chimes_lsq}"

export LAMMPS_EXE="${LAMMPS_EXE:-$CHIMES_CALCULATOR/etc/lmp/exe/lmp_mpi_chimes}"
export HISTOGRAM_EXE="${HISTOGRAM_EXE:-$CHIMES_CALCULATOR/chimesFF/src/FP/histogram}"
export POST_PROCESS_SH="${POST_PROCESS_SH:-$CHIMES_CALCULATOR/chimesFF/src/FP/post_process.sh}"
export CHIMES_LSQ_BIN="${CHIMES_LSQ_BIN:-$CHIMES_LSQ/build/chimes_lsq}"

export CHIMES_PARAMS="${CHIMES_PARAMS:-$MULTIELEMENT_ROOT/element_switching/model/params.txt}"
export HEA_CHIMES_PARAMS="${HEA_CHIMES_PARAMS:-$MULTIELEMENT_ROOT/hea_study/chimes_model/params.txt}"
