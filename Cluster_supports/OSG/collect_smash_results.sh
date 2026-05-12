#!/usr/bin/env bash
# Collect SMASH analysis results from an OSG run into $DATA.
#
# Usage (from $DATA):
#   ./collect_smash_results.sh ~/iEBEMUSICTestRun
#
# Finds every smash_analysis_*.npz under the run folder,
# combines them into a single combined_results.npz, and saves
# a copy of the submission scripts alongside it.

run=${1%/}
runfoldername=$(echo "$run" | rev | cut -d "/" -f 1 | rev)

mkdir -p "$runfoldername"
(
    cd "$runfoldername"

    # copy submission scripts for reference
    cp "$run"/*.py  ./ 2>/dev/null
    cp "$run"/*.sh  ./ 2>/dev/null
    cp "$run"/*.submit ./ 2>/dev/null

    echo "Combining SMASH results from: $run"
    ../combine_smash_results.py "$run"
)
