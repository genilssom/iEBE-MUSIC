#!/usr/bin/env bash
# Collect SMASH analysis results from an OSG run into $DATA.
#
# Usage (from $DATA):
#   ./collect_smash_results.sh ~/iEBEMUSICTestRun
#
# Moves every smash_results_N/ directory from $HOME into $DATA,
# freeing space in $HOME. Skips directories already collected.
# Safe to run repeatedly while jobs are still running.
#
# To convert to notebook-compatible format afterwards:
#   python3 smash_to_qns.py <run_folder_here> <output_folder>
# Produces Qns_0.npy and Nsamples_0.npy for use with the advisor's notebooks.

run=${1%/}
runfoldername=$(echo "$run" | rev | cut -d "/" -f 1 | rev)

mkdir -p "$runfoldername"

echo "Collecting SMASH results from: $run"

n_moved=0
n_skip=0
for src in "$run"/smash_results_*/; do
    [ -d "$src" ] || continue
    subdir=$(basename "$src")
    dst="$runfoldername/$subdir"
    if [ -d "$dst" ]; then
        n_skip=$((n_skip + 1))
        continue
    fi
    mv "$src" "$dst"
    n_moved=$((n_moved + 1))
done

echo "Done.  Moved: $n_moved   Already collected: $n_skip"
