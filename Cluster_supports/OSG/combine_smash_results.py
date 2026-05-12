#!/usr/bin/env python3
"""Combine multiple smash_analysis_*.npz files from an OSG run into one.

Usage:
    ./combine_smash_results.py <run_folder>

Searches recursively for smash_analysis_*.npz under <run_folder>,
checks each file for validity, and produces combined_results.npz.

Output arrays (same layout as a single smash_analysis file):
    counts      — summed over all events
    q_vectors   — summed over all events (complex, additive)
    mean_pt     — recomputed from the summed counts and sum_pt
    pids, pt_bins — taken from the first valid file (identical across events)
    num_events  — total number of events combined
"""

import sys
from glob import glob
from os import path
import numpy as np


def is_valid(npz):
    """Return True if the npz has the expected keys and at least one particle."""
    required = {'counts', 'q_vectors', 'mean_pt', 'pids', 'pt_bins', 'num_events'}
    if not required.issubset(set(npz.keys())):
        return False
    if npz['counts'].sum() == 0:
        return False
    return True


def main(run_folder):
    pattern = path.join(run_folder, '**', 'smash_analysis_*.npz')
    files = sorted(glob(pattern, recursive=True))

    if not files:
        print(f"No smash_analysis_*.npz files found under {run_folder}")
        sys.exit(1)

    print(f"Found {len(files)} file(s). Combining...")

    combined_counts   = None
    combined_sum_pt   = None
    combined_qvec     = None
    combined_nevents  = 0
    pids     = None
    pt_bins  = None
    n_good   = 0
    n_bad    = 0

    for fpath in files:
        try:
            npz = np.load(fpath)
        except Exception as e:
            print(f"  SKIP (cannot open): {fpath}  [{e}]")
            n_bad += 1
            continue

        if not is_valid(npz):
            print(f"  SKIP (invalid/empty): {fpath}")
            n_bad += 1
            continue

        counts  = npz['counts']        # shape (n_pids, n_pt_bins)
        mean_pt = npz['mean_pt']       # shape (n_pids, n_pt_bins)
        qvec    = npz['q_vectors']     # shape (n_pids, n_harmonics, n_pt_bins)
        nevents = int(npz['num_events'])

        # reconstruct sum_pt from mean_pt * counts
        sum_pt = mean_pt * counts

        if combined_counts is None:
            combined_counts  = counts.copy()
            combined_sum_pt  = sum_pt.copy()
            combined_qvec    = qvec.copy()
            pids    = npz['pids']
            pt_bins = npz['pt_bins']
        else:
            combined_counts += counts
            combined_sum_pt += sum_pt
            combined_qvec   += qvec

        combined_nevents += nevents
        n_good += 1

    if n_good == 0:
        print("No valid events found. Aborting.")
        sys.exit(1)

    combined_mean_pt = np.divide(
        combined_sum_pt, combined_counts,
        out=np.zeros_like(combined_sum_pt),
        where=combined_counts > 0
    )

    out_file = 'combined_results.npz'
    np.savez(out_file,
             counts=combined_counts,
             q_vectors=combined_qvec,
             mean_pt=combined_mean_pt,
             pids=pids,
             pt_bins=pt_bins,
             num_events=combined_nevents)

    print(f"\nDone.")
    print(f"  Good events : {n_good}")
    print(f"  Skipped     : {n_bad}")
    print(f"  num_events  : {combined_nevents}")
    print(f"  Output      : {path.abspath(out_file)}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
