#!/usr/bin/env python3
"""This script generates the job submission script for a generic HTCondor cluster
with Singularity support (non-OSG).

Singularity is invoked explicitly via `singularity exec` inside run_singularity.sh
rather than through HTCondor's +SingularityImage / SINGULARITY_CAN_USE_SIF mechanism,
so no special ClassAd is required on the worker nodes."""


import re
import sys
from os import path, makedirs
import argparse
import random

FILENAME = "singularity.submit"


def detect_afterburner(param_file):
    """Return afterburner_type string read from the parameter file."""
    try:
        with open(param_file, 'r') as f:
            content = f.read()
        m = re.search(r"['\"]afterburner_type['\"]\s*:\s*['\"](\w+)['\"]", content)
        if m:
            return m.group(1)
    except Exception:
        pass
    return "UrQMD"


# ── UrQMD mode ────────────────────────────────────────────────────────────────

def write_submission_script_urqmd(para_dict_):
    jobName = "iEBEMUSIC_{}".format(para_dict_["job_name"])
    random_seed = random.SystemRandom().randint(0, 10000000)
    sif = para_dict_["singularity_image_path"]
    script = open(FILENAME, "w")

    if para_dict_["bayesFlag"]:
        script.write("""universe = vanilla
executable = run_singularity.sh
arguments = {0} $(Process) {1} {2} {3} {4} {5}
""".format(para_dict_["param_file"], para_dict_["n_events_per_job"],
           para_dict_["n_threads"], random_seed, para_dict_["bayes_file"], sif))
    else:
        script.write("""universe = vanilla
executable = run_singularity.sh
arguments = {0} $(Process) {1} {2} {3} {4}
""".format(para_dict_["param_file"], para_dict_["n_events_per_job"],
           para_dict_["n_threads"], random_seed, sif))

    script.write("""
JobBatchName = {0}

should_transfer_files = YES
WhenToTransferOutput = ON_EXIT
""".format(jobName))

    # The .sif is included in transfer_input_files so HTCondor copies it to
    # the worker scratch dir. In run_singularity.sh we use $(basename ...) to
    # reference it, since HTCondor strips the directory on the worker side.
    if para_dict_['bayesFlag']:
        script.write("\ntransfer_input_files = {}, {}, {}\n".format(
            para_dict_['param_file'], para_dict_['bayes_file'], sif))
    else:
        script.write("\ntransfer_input_files = {}, {}\n".format(
            para_dict_['param_file'], sif))

    script.write(
        "transfer_checkpoint_files = playground/event_0/EVENT_RESULTS_$(Process).tar.gz\n")

    script.write("""
transfer_output_files = playground/event_0/EVENT_RESULTS_$(Process)/spvn_results_$(Process).h5

error = log/job.$(Cluster).$(Process).error
output = log/job.$(Cluster).$(Process).output
log = log/job.$(Cluster).$(Process).log

max_idle = 1000

# remove the failed jobs
periodic_remove = (ExitCode == 73)

periodic_release = ((HoldReasonCode == 13 || HoldReasonCode == 26) && (time() - EnteredCurrentStatus) > 1200 )

checkpoint_exit_code = 85

# Send the job to Held state on failure.
on_exit_hold = (ExitBySignal == True) || (ExitCode != 0 && ExitCode != 73)

request_cpus = {0:d}
request_memory = {1:d} GB
request_disk = 2 GB

queue {2:d}""".format(para_dict_["n_threads"], para_dict_["memory_per_job"],
                      para_dict_["n_jobs"]))
    script.close()


def write_job_running_script_urqmd(para_dict_):
    # sif is the last positional arg: $6 (no bayes) or $7 (bayes)
    sif_pos = 7 if para_dict_["bayesFlag"] else 6

    script = open("run_singularity.sh", "w")
    script.write("""#!/usr/bin/env bash

parafile=$1
processId=$2
nHydroEvents=$3
nthreads=$4
seed=$5

export PYTHONIOENCODING=utf-8
export PATH="${PATH}:/usr/lib64/openmpi/bin:/usr/local/gsl/2.5/x86_64/bin"
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:/usr/local/lib:/usr/local/gsl/2.5/x86_64/lib64"

jobdir=$(pwd)
export JOBDIR="${jobdir}"
export TMPDIR="${jobdir}/tmp"
export XDG_DATA_HOME="${jobdir}/.local/share"
export XDG_CACHE_HOME="${jobdir}/.cache"
export TRENTO_CACHE="${jobdir}/.trento"

export SINGULARITYENV_TMPDIR="${TMPDIR}"
export SINGULARITYENV_XDG_DATA_HOME="${XDG_DATA_HOME}"
export SINGULARITYENV_XDG_CACHE_HOME="${XDG_CACHE_HOME}"
export SINGULARITYENV_TRENTO_CACHE="${TRENTO_CACHE}"

mkdir -p "${TMPDIR}"
mkdir -p "${XDG_DATA_HOME}"
mkdir -p "${XDG_CACHE_HOME}"
mkdir -p "${TRENTO_CACHE}"
mkdir -p "${XDG_DATA_HOME}/trento"

printf "Start time: `/bin/date`\\n"
printf "Job is running on node: `/bin/hostname`\\n"
printf "system kernel: `uname -r`\\n"
printf "Job running as user: `/usr/bin/id`\\n"

""")
    if para_dict_["bayesFlag"]:
        script.write("bayesFile=$6\n")

    script.write("SINGULARITY_IMAGE=${{{}}}\n\n".format(sif_pos))

    # HTCondor transfers the .sif as basename into the scratch dir.
    # Capture scratch dir and build absolute SIF path before any cd.
    script.write('SCRATCH_DIR="${PWD}"\n')
    script.write('SIF="${SCRATCH_DIR}/$(basename ${SINGULARITY_IMAGE})"\n\n')

    if para_dict_["bayesFlag"]:
        script.write(
            'singularity exec --bind "${SCRATCH_DIR}:${SCRATCH_DIR}" "${SIF}" '
            "/opt/iEBE-MUSIC/generate_jobs.py -w playground -c OSG "
            "-par ${parafile} -id ${processId} -n_th ${nthreads} "
            "-n_urqmd ${nthreads} -n_hydro ${nHydroEvents} -seed ${seed} "
            "-b ${bayesFile} --nocopy --continueFlag\n")
    else:
        script.write(
            'singularity exec --bind "${SCRATCH_DIR}:${SCRATCH_DIR}" "${SIF}" '
            "/opt/iEBE-MUSIC/generate_jobs.py -w playground -c OSG "
            "-par ${parafile} -id ${processId} -n_th ${nthreads} "
            "-n_urqmd ${nthreads} -n_hydro ${nHydroEvents} -seed ${seed} "
            "--nocopy --continueFlag\n")

    script.write("""
cd playground/event_0
mv EVENT_RESULTS_${processId}.tar.gz playground/event_0
singularity exec --bind "${SCRATCH_DIR}:${SCRATCH_DIR}" "${SIF}" bash submit_job.script
status=$?
if [ $status -ne 0 ]; then
    exit $status
fi
""")
    script.close()


# ── SMASH mode (TRENTo + isobar seeds) ───────────────────────────────────────

def write_submission_script_smash(para_dict_):
    jobName = "iEBEMUSIC_{}".format(para_dict_["job_name"])
    random_seed = random.SystemRandom().randint(0, 10000000)
    seed_file = para_dict_.get("seed_file", "")
    sif = para_dict_["singularity_image_path"]
    script = open(FILENAME, "w")

    # Argument order: param_file $(Process) n_events n_threads seed
    #                 [bayes_file] [seed_file] singularity_image
    if para_dict_["bayesFlag"]:
        args_str = "{0} $(Process) {1} {2} {3} {4}".format(
            para_dict_["param_file"], para_dict_["n_events_per_job"],
            para_dict_["n_threads"], random_seed, para_dict_["bayes_file"])
    else:
        args_str = "{0} $(Process) {1} {2} {3}".format(
            para_dict_["param_file"], para_dict_["n_events_per_job"],
            para_dict_["n_threads"], random_seed)
    if seed_file:
        args_str += " {}".format(seed_file)
    # singularity image is always last
    args_str += " {}".format(sif)

    script.write("""universe = vanilla
executable = run_singularity.sh
arguments = {}
""".format(args_str))

    script.write("""
JobBatchName = {0}

should_transfer_files = YES
WhenToTransferOutput = ON_EXIT
""".format(jobName))

    # The .sif is included so HTCondor copies it to the worker scratch dir.
    # In run_singularity.sh we reference it via $(basename ...).
    input_files = [para_dict_['param_file']]
    if para_dict_['bayesFlag']:
        input_files.append(para_dict_['bayes_file'])
    if seed_file:
        input_files.append(seed_file)
    input_files.append(sif)
    script.write("\ntransfer_input_files = {}\n".format(", ".join(input_files)))

    script.write("""
transfer_output_files = playground/event_0/EVENT_RESULTS_$(Process)

error = log/job.$(Cluster).$(Process).error
output = log/job.$(Cluster).$(Process).output
log = log/job.$(Cluster).$(Process).log

max_idle = 1000

# remove the failed jobs
periodic_remove = (ExitCode == 73)

periodic_release = ((HoldReasonCode == 13 || HoldReasonCode == 26) && (time() - EnteredCurrentStatus) > 1200 )

checkpoint_exit_code = 85

# Send the job to Held state on failure.
on_exit_hold = (ExitBySignal == True) || (ExitCode != 0 && ExitCode != 73)

request_cpus = {0:d}
request_memory = {1:d} GB
request_disk = 2 GB

queue {2:d}""".format(para_dict_["n_threads"], para_dict_["memory_per_job"],
                      para_dict_["n_jobs"]))
    script.close()


def write_job_running_script_smash(para_dict_):
    seed_file = para_dict_.get("seed_file", "")
    # seedfile position: $6 (no bayes) or $7 (bayes)
    seedfile_pos = 7 if para_dict_["bayesFlag"] else 6
    # singularity image is always the last arg, after optional seed_file
    sif_pos = seedfile_pos + (1 if seed_file else 0)

    script = open("run_singularity.sh", "w")
    script.write("""#!/usr/bin/env bash

parafile=$1
processId=$2
nHydroEvents=$3
nthreads=$4
seed=$5

export PYTHONIOENCODING=utf-8
export PATH="${PATH}:/usr/lib64/openmpi/bin:/usr/local/gsl/2.5/x86_64/bin"
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:/usr/local/lib:/usr/local/gsl/2.5/x86_64/lib64"

jobdir=$(pwd)
export JOBDIR="${jobdir}"
export TMPDIR="${jobdir}/tmp"
export HOME="${jobdir}"
export XDG_DATA_HOME="${jobdir}/.local/share"
export XDG_CACHE_HOME="${jobdir}/.cache"
export TRENTO_CACHE="${jobdir}/.trento"

export SINGULARITYENV_HOME="${HOME}"
export SINGULARITYENV_TMPDIR="${TMPDIR}"
export SINGULARITYENV_XDG_DATA_HOME="${XDG_DATA_HOME}"
export SINGULARITYENV_XDG_CACHE_HOME="${XDG_CACHE_HOME}"
export SINGULARITYENV_TRENTO_CACHE="${TRENTO_CACHE}"

mkdir -p "${TMPDIR}"
mkdir -p "${XDG_DATA_HOME}"
mkdir -p "${XDG_CACHE_HOME}"
mkdir -p "${TRENTO_CACHE}"
mkdir -p "${XDG_DATA_HOME}/trento"

touch "${TRENTO_CACHE}/write_test.txt" || { echo "Cannot write to TRENTO_CACHE"; exit 101; }
touch "${XDG_DATA_HOME}/write_test.txt" || { echo "Cannot write to XDG_DATA_HOME"; exit 102; }
touch "${TMPDIR}/write_test.txt" || { echo "Cannot write to TMPDIR"; exit 103; }

printf "Start time: `/bin/date`\\n"
printf "Job is running on node: `/bin/hostname`\\n"
printf "system kernel: `uname -r`\\n"
printf "Job running as user: `/usr/bin/id`\\n"

echo "==== Environment debug ===="
echo "PWD=${PWD}"
echo "HOME=${HOME}"
echo "TMPDIR=${TMPDIR}"
echo "XDG_DATA_HOME=${XDG_DATA_HOME}"
echo "XDG_CACHE_HOME=${XDG_CACHE_HOME}"
echo "TRENTO_CACHE=${TRENTO_CACHE}"
echo "==========================="

""")

    if para_dict_["bayesFlag"]:
        script.write("bayesFile=$6\n")

    if seed_file:
        script.write("seedfile=${{{}}}\n".format(seedfile_pos))
        script.write(
            "# Use basename: HTCondor transfers the file to the working directory\n"
            'SEED_ARG="--isobar_seed_file $(basename ${seedfile})"\n')
    else:
        script.write('SEED_ARG=""\n')

    script.write("SINGULARITY_IMAGE=${{{}}}\n".format(sif_pos))
    # HTCondor transfers the .sif as basename into the scratch dir.
    # Capture scratch dir and build absolute SIF path before any cd.
    script.write('SCRATCH_DIR="${PWD}"\n')
    script.write('SIF="${SCRATCH_DIR}/$(basename ${SINGULARITY_IMAGE})"\n\n')

    if para_dict_["bayesFlag"]:
        script.write(
            'singularity exec --bind "${SCRATCH_DIR}:${SCRATCH_DIR}" "${SIF}" '
            "/opt/iEBE-MUSIC/generate_jobs.py -w playground -c OSG "
            "-par ${parafile} ${SEED_ARG} -id ${processId} -n_th ${nthreads} "
            "-n_urqmd ${nthreads} -n_hydro ${nHydroEvents} -seed ${seed} "
            "-b ${bayesFile} --nocopy --continueFlag\n")
    else:
        script.write(
            'singularity exec --bind "${SCRATCH_DIR}:${SCRATCH_DIR}" "${SIF}" '
            "/opt/iEBE-MUSIC/generate_jobs.py -w playground -c OSG "
            "-par ${parafile} ${SEED_ARG} -id ${processId} -n_th ${nthreads} "
            "-n_urqmd ${nthreads} -n_hydro ${nHydroEvents} -seed ${seed} "
            "--nocopy --continueFlag\n")

    script.write("""
cd playground/event_0
singularity exec --bind "${SCRATCH_DIR}:${SCRATCH_DIR}" "${SIF}" bash submit_job.script
status=$?
if [ $status -ne 0 ]; then
    exit $status
fi
cp -r TRENTo EVENT_RESULTS_${processId}/
""")
    script.close()


# ── Entry point ───────────────────────────────────────────────────────────────

def main(para_dict_):
    afterburner = detect_afterburner(para_dict_["param_file"])
    print("Detected afterburner: {}".format(afterburner))

    if afterburner == "SMASH":
        write_submission_script_smash(para_dict_)
        write_job_running_script_smash(para_dict_)
    else:
        write_submission_script_urqmd(para_dict_)
        write_job_running_script_urqmd(para_dict_)

    logFolderName = "log"
    if not path.exists(logFolderName):
        makedirs(logFolderName)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='HTCondor + Singularity submission script for iEBE-MUSIC',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('-n', '--n_jobs', metavar='', type=int, default=1,
                        help='number of jobs')
    parser.add_argument('-nev', '--n_events_per_job', metavar='', type=int,
                        default=1, help='number of events per job')
    parser.add_argument('-nth', '--n_threads', metavar='', type=int, default=1,
                        help='number of threads per job')
    parser.add_argument('-singularity', '--singularity_image_path', metavar='',
                        type=str, default="",
                        help='absolute path to the .sif Singularity image '
                             '(must be accessible on all worker nodes)')
    parser.add_argument('-param', '--param_file', metavar='', type=str,
                        default="", help='parameter file')
    parser.add_argument('-jobid', '--job_name', metavar='', type=str,
                        default="test", help='job name')
    parser.add_argument('-bayes', '--bayes_file', metavar='', type=str,
                        default="", help='bayes file')
    parser.add_argument('-mem', '--memory_per_job', metavar='', type=int,
                        default=2, help='memory per job (GB)')
    parser.add_argument('-seed_file', '--seed_file', metavar='', type=str,
                        default="",
                        help='isobar nucleon seed HDF5 file (TRENTo/SMASH only)')

    if len(sys.argv) < 2:
        parser.print_help()
        exit(0)

    para_dict = vars(parser.parse_args())
    para_dict["bayesFlag"] = para_dict["bayes_file"] != ""

    main(para_dict)
