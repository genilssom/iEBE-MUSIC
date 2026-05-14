#!/usr/bin/env bash
# Collect SMASH analysis results from an OSG run into $DATA.
#
# Usage (from $DATA):
#   ./collect_smash_results.sh ~/iEBEMUSICTestRun
#
# Finds every smash_results_*/smash_analysis_*.npz under the run folder
# and copies them here, preserving the smash_results_N/ structure.
# Can be run repeatedly while jobs are still running.
#
# To combine afterwards:
#   python3 combine_smash_results.py <run_folder_here>

run=${1%/}
runfoldername=$(echo "$run" | rev | cut -d "/" -f 1 | rev)

mkdir -p "$runfoldername"

echo "Collecting SMASH results from: $run"

n=0
for npz in "$run"/smash_results_*/smash_analysis_*.npz; do
    [ -f "$npz" ] || continue
    subdir=$(basename "$(dirname "$npz")")
    mkdir -p "$runfoldername/$subdir"
    cp "$npz" "$runfoldername/$subdir/"
    n=$((n + 1))
done

echo "Done. Collected $n file(s) into $runfoldername/"
