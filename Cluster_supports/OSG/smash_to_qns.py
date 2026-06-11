#!/usr/bin/env python3
"""Convert per-event smash_analysis_*.npz files into Qns_0.npy + Nsamples_0.npy.

This script replaces combine_smash_results.py for the SMASH → notebook analysis
workflow.  The old script summed all events (destroying the per-event information
needed for centrality selection).  This one stacks them.

Usage:
    python3 smash_to_qns.py <run_folder> [output_folder]

    <run_folder>   — tree that contains smash_results_*/smash_analysis_*.npz
    [output_folder]— where to write outputs (default: .)

Output files
------------
Qns_0.npy      complex128  shape (1, N_events, 5, 4, 56)
                 axes: [delta_f=0, event, species, harmonic, pT_bin]
Nsamples_0.npy float64     shape (1, N_events)
                 number of SMASH oversampling events per hydro event (=1)
pt_bins.npy    float64     shape (56,)  left edge of each pT bin (GeV)

Harmonic axis (axis 3) — 4 entries:
    index 0 → Q_0 = particle multiplicity (real, reconstructed from counts)
    index 1 → Q_1 = Σ exp(i·1·φ)
    index 2 → Q_2 = Σ exp(i·2·φ)
    index 3 → Q_3 = Σ exp(i·3·φ)

    Note: analysis_cli_optimized.py stores harmonics [1,2,3].
    We prepend Q_0 (= counts) so that the advisor's notebook, which
    reads Q_0 at harmonic index 0, works correctly.

Species (axis 2) — particle + antiparticle summed:
    0 = pi    PDG  211, -211
    1 = K     PDG  321, -321
    2 = p     PDG 2212, -2212
    3 = Sigma PDG 3222, 3212, 3112, -3222, -3212, -3112
    4 = Xi    PDG 3312, 3322, -3312, -3322

pT bins (axis 4) — 56 bins:
    Bin i covers [pt_bins[i], pt_bins[i+1]).
    The raw npz has 57 slots; slot 56 is overflow (pT ≥ 10 GeV, always 0) and
    is dropped here to match the notebook's Npt = 56.

Notebook adapter
----------------
    Qn_all   = np.load('Qns_0.npy')        # shape (1, Nevt, 5, 4, 56)
    nsamples = np.load('Nsamples_0.npy')   # shape (1, Nevt)
    delta_f_models = 1
    n_harmonics    = 4   # indices 0..3 → Q_0, Q_1, Q_2, Q_3
    particle_names = ['pi', 'K', 'p', 'Sigma', 'Xi']
    # ptcuts (57 edges) and ptlist (56 midpoints) stay the same
    # for v_n{2}: use harmonic index n (1=v1, 2=v2, 3=v3)
    # for self-correlation: dQ0 = Qn_all[:,:,:,0,:].real  (unweighted ⇒ dQ0 = Q0)
"""

import sys
import re
from glob import glob
from os import path, makedirs
import numpy as np


# PDG codes included per species (particle + antiparticle summed)
SPECIES = [
    ('pi',    [ 211, -211]),
    ('K',     [ 321, -321]),
    ('p',     [2212, -2212]),
    ('Sigma', [3222, 3212, 3112, -3222, -3212, -3112]),
    ('Xi',    [3312, 3322, -3312, -3322]),
]

N_SPECIES = len(SPECIES)
N_PT_BINS = 56   # drop overflow slot (index 56, pT ≥ 10 GeV, always 0)
# Harmonics stored in the npz by analysis_cli_optimized.py
_STORED_HARMONICS = [1, 2, 3]
# Output harmonics axis: [Q_0, Q_1, Q_2, Q_3] — prepend Q_0 from counts
N_HARMONICS_OUT = 1 + len(_STORED_HARMONICS)   # = 4


def _sort_key(fpath):
    """Sort by trailing integer in 'smash_analysis_N.npz'."""
    m = re.search(r'(\d+)\.npz$', fpath)
    return int(m.group(1)) if m else -1


def is_valid(npz):
    required = {'q_vectors', 'counts', 'pids', 'pt_bins', 'num_events'}
    return required.issubset(set(npz.keys()))


def process_event(npz):
    """Return (event_qn, n_samples).

    event_qn: complex128 array  (N_SPECIES, N_HARMONICS_OUT, N_PT_BINS)
              harmonic 0 = Q_0 (counts, real)
              harmonic 1 = Q_1, harmonic 2 = Q_2, harmonic 3 = Q_3
    n_samples: int
    """
    pids   = npz['pids']                      # (28,)
    qvec   = npz['q_vectors']                 # (28, 3, 57) — harmonics n=1,2,3
    counts = npz['counts']                    # (28, 57)

    event_qn = np.zeros((N_SPECIES, N_HARMONICS_OUT, N_PT_BINS), dtype=complex)

    for isp, (_, pid_list) in enumerate(SPECIES):
        for pid in pid_list:
            hits = np.where(pids == pid)[0]
            if hits.size == 0:
                continue
            idx = hits[0]
            # harmonic 0 = Q_0 = multiplicity (real, from counts)
            event_qn[isp, 0] += counts[idx, :N_PT_BINS].astype(complex)
            # harmonics 1..3 = Q_1, Q_2, Q_3 from q_vectors
            event_qn[isp, 1:] += qvec[idx, :, :N_PT_BINS]

    return event_qn, int(npz['num_events'])


def main(run_folder, output_folder='.'):
    pattern = path.join(run_folder, '**', 'smash_analysis_*.npz')
    files = sorted(glob(pattern, recursive=True), key=_sort_key)

    if not files:
        print(f"No smash_analysis_*.npz files found under {run_folder}")
        sys.exit(1)

    print(f"Found {len(files)} file(s). Converting...")

    qns_list      = []
    nsamples_list = []
    pt_bins_ref   = None
    n_good = 0
    n_bad  = 0

    for fpath in files:
        try:
            npz = np.load(fpath)
        except Exception as e:
            print(f"  SKIP (cannot open): {path.basename(fpath)}  [{e}]")
            n_bad += 1
            continue

        if not is_valid(npz):
            print(f"  SKIP (missing keys): {path.basename(fpath)}")
            n_bad += 1
            continue

        event_qn, n_samples = process_event(npz)

        if pt_bins_ref is None:
            pt_bins_ref = npz['pt_bins'][:N_PT_BINS].copy()

        qns_list.append(event_qn)
        nsamples_list.append(float(n_samples))
        n_good += 1

    if n_good == 0:
        print("No valid events found. Aborting.")
        sys.exit(1)

    # Stack: (N_events, N_SPECIES, N_HARMONICS_OUT, N_PT_BINS)
    Qns      = np.stack(qns_list, axis=0)
    Nsamples = np.array(nsamples_list, dtype=float)

    # Add delta_f axis (one model point)
    Qns      = Qns[np.newaxis, :]       # (1, N_events, 5, 4, 56)
    Nsamples = Nsamples[np.newaxis, :]  # (1, N_events)

    makedirs(output_folder, exist_ok=True)
    np.save(path.join(output_folder, 'Qns_0.npy'),      Qns)
    np.save(path.join(output_folder, 'Nsamples_0.npy'), Nsamples)
    np.save(path.join(output_folder, 'pt_bins.npy'),    pt_bins_ref)

    sp_names = [s[0] for s in SPECIES]
    print()
    print("Done.")
    print(f"  Good events    : {n_good}")
    print(f"  Skipped        : {n_bad}")
    print(f"  Qns_0.npy      : {Qns.shape}  (delta_f, events, species, harmonics, pT)")
    print(f"  Nsamples_0.npy : {Nsamples.shape}")
    print(f"  Species        : {sp_names}")
    print(f"  Harmonics      : Q_0 (counts), Q_1, Q_2, Q_3  [indices 0-3]")
    print(f"  pT bins        : {N_PT_BINS}  ({pt_bins_ref[0]:.2f}–{pt_bins_ref[-1]:.2f} GeV)")
    print(f"  Output folder  : {path.abspath(output_folder)}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    run_folder    = sys.argv[1]
    output_folder = sys.argv[2] if len(sys.argv) > 2 else '.'
    main(run_folder, output_folder)
