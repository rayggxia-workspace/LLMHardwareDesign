"""Generate only; never submit. Existing container runs entire RTL runner."""
import argparse
import re
import shlex
from pathlib import Path, PurePosixPath

PERSONAL = PurePosixPath('/public/home/yuzelu/Melodydt')
OPT = PurePosixPath('/public/home/yuzelu/opt')


def remote_path(value, allowed=PERSONAL):
    path = PurePosixPath(value)
    if '..' in path.parts or not (path == allowed or allowed in path.parents):
        raise argparse.ArgumentTypeError('path must stay within ' + str(allowed))
    if not re.fullmatch(r'/[A-Za-z0-9_./-]+', str(path)):
        raise argparse.ArgumentTypeError('use simple absolute POSIX path without shell/control characters')
    return str(path)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--script-out', type=Path, required=True)
    p.add_argument('--remote-root', required=True, type=remote_path)
    p.add_argument('--remote-output', required=True, type=remote_path)
    p.add_argument('--slurm-log-dir', required=True, type=remote_path)
    p.add_argument('--runner', required=True, type=remote_path)
    p.add_argument('--contract', required=True, type=remote_path)
    p.add_argument('--a8-contract', type=remote_path)
    p.add_argument('--name-initials', required=True)
    p.add_argument('--source-ref', required=True)
    p.add_argument('--partition', required=True)
    p.add_argument('--node-class', choices=['c64', 'c96', 'debug'], required=True)
    p.add_argument('--suite', choices=['n', 'f8', 'a8', 'regression', 'all'], required=True)
    p.add_argument('--cpus', type=int, default=4)
    p.add_argument('--minutes', type=int, default=25)
    p.add_argument('--container-runtime', default='/usr/bin/singularity')
    p.add_argument('--container-image', required=True)
    p.add_argument('--verilator', required=True)
    p.add_argument('--nonfatal-warnings', action='store_true')
    a = p.parse_args()
    if not re.fullmatch(r'[a-z][a-z0-9]{1,19}', a.name_initials):
        p.error('actual owner abbreviation required; no guessed default')
    if not re.fullmatch(r'[0-9a-fA-F]{40}', a.source_ref):
        p.error('source-ref must be actual full40-character base commit')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', a.partition):
        p.error('supply one actually verified partition name')
    if a.cpus < 1 or a.minutes < 1 or (a.node_class == 'debug' and a.minutes > 30):
        p.error('positive resources; debug time <=30min')
    if a.suite in ('a8', 'all') and not a.a8_contract:
        p.error('a8/all requires independent complete A8 contract')
    for value in [a.container_image, a.verilator]:
        remote_path(value, OPT)
    if not re.fullmatch(r'/[A-Za-z0-9_./-]+', a.container_runtime):
        p.error('container-runtime must be an explicit absolute path')
    if a.script_out.exists():
        p.error('new script filename required; preserve old job/config bytes')
    job_name = a.name_initials + '-a8-' + a.suite
    hours, remainder = divmod(a.minutes, 60)
    base = [
        'python3', a.runner, '--root', a.remote_root, '--output', a.remote_output,
        '--contract', a.contract, '--suite', a.suite, '--name-initials', a.name_initials,
        '--source-ref', a.source_ref, '--verilator', a.verilator,
        '--build-jobs', str(a.cpus), '--node-class', a.node_class,
        '--job-wall-minutes', str(a.minutes), '--container-image', a.container_image,
    ]
    if a.a8_contract:
        base += ['--a8-contract', a.a8_contract]
    if a.nonfatal_warnings:
        base += ['--nonfatal-warnings']
    command = ' '.join(shlex.quote(x) for x in base)
    prefix = [a.container_runtime, 'exec', '--cleanenv', '--no-home',
              '--bind', str(PERSONAL) + ':' + str(PERSONAL) + ':rw',
              '--bind', str(OPT) + ':' + str(OPT) + ':ro', '--pwd', a.remote_root]
    prefix_text = ' '.join(shlex.quote(x) for x in prefix)
    lines = [
        '#!/bin/bash', '# Generated only; no submission was performed.',
        '#SBATCH --job-name=' + job_name, '#SBATCH --partition=' + a.partition,
        '#SBATCH --nodes=1', '#SBATCH --ntasks=1', '#SBATCH --cpus-per-task=' + str(a.cpus),
        '#SBATCH --time={:02d}:{:02d}:00'.format(hours, remainder),
        '#SBATCH --output=' + a.slurm_log_dir + '/' + job_name + '-%j.out',
        '#SBATCH --error=' + a.slurm_log_dir + '/' + job_name + '-%j.err',
        'set -euo pipefail', 'umask 077',
        '# Slurm log directory/root/runner/contracts must already exist before sbatch.',
        'test -n "${SLURM_JOB_ID:?allocation required}"',
        'test "${SLURM_NTASKS:-1}" -eq 1',
        'test "${SLURM_CPUS_PER_TASK:?CPU allocation required}" -ge ' + str(a.cpus),
        'TASK_BOOTSTRAP_DIR="$(mktemp -d ' + shlex.quote(str(PurePosixPath(a.remote_output).parent) + '/.bootstrap-XXXXXX') + ')"',
        'mkdir -p "$TASK_BOOTSTRAP_DIR/home" "$TASK_BOOTSTRAP_DIR/tmp" "$TASK_BOOTSTRAP_DIR/cache"',
        'mkdir -p "$TASK_BOOTSTRAP_DIR/singularity-cache" "$TASK_BOOTSTRAP_DIR/singularity-tmp"',
        'export SINGULARITY_CACHEDIR="$TASK_BOOTSTRAP_DIR/singularity-cache"',
        'export SINGULARITY_TMPDIR="$TASK_BOOTSTRAP_DIR/singularity-tmp"',
        'export APPTAINER_CACHEDIR="$TASK_BOOTSTRAP_DIR/singularity-cache"',
        'export APPTAINER_TMPDIR="$TASK_BOOTSTRAP_DIR/singularity-tmp"',
        'export TMPDIR="$TASK_BOOTSTRAP_DIR/tmp"',
        'export XDG_CACHE_HOME="$TASK_BOOTSTRAP_DIR/cache"',
        shlex.quote(a.container_runtime) + ' --version',
        '# Hash1.5GB image only here in allocated job, never on login preflight.',
        'TASK_IMAGE_SHA="$(sha256sum ' + shlex.quote(a.container_image) + ' | cut -d\' \' -f1)"',
        'printf "job=%s node=%s image_sha=%s\\n" "$SLURM_JOB_ID" "${SLURMD_NODENAME:-unverified}" "$TASK_IMAGE_SHA"',
        prefix_text + ' \\',
        '  --home "$TASK_BOOTSTRAP_DIR/home" \\',
        '  --bind "$TASK_BOOTSTRAP_DIR/tmp:/tmp:rw" \\',
        '  --env "TMPDIR=$TASK_BOOTSTRAP_DIR/tmp,XDG_CACHE_HOME=$TASK_BOOTSTRAP_DIR/cache" \\',
        '  --env "OMP_NUM_THREADS=1" \\',
        '  --env "SLURM_JOB_ID=$SLURM_JOB_ID,SLURM_JOB_NAME=$SLURM_JOB_NAME,SLURM_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK,SLURM_NTASKS=${SLURM_NTASKS:-1}" \\',
        '  --env "SLURM_JOB_NODELIST=${SLURM_JOB_NODELIST:-},SLURM_JOB_PARTITION=${SLURM_JOB_PARTITION:-},SLURM_JOB_END_TIME=${SLURM_JOB_END_TIME:-}" \\',
        '  ' + shlex.quote(a.container_image) + ' ' + command + ' --container-sha256 "$TASK_IMAGE_SHA"',
        ''
    ]
    a.script_out.parent.mkdir(parents=True, exist_ok=True)
    a.script_out.write_bytes(('\n'.join(lines)).encode('utf8'))
    print('PREPARED_ONLY (not submitted): ' + str(a.script_out))
    print('job-name=' + job_name + '; expected ntasks1/cpus' + str(a.cpus))


if __name__ == '__main__':
    main()
