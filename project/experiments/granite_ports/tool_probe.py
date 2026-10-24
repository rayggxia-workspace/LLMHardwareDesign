"""Read-only probe of existing authorized server tools, executed through Slurm."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import time


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda: stream.read(8 << 20), b''):
            h.update(data)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--binding', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if not str(a.out.resolve()).startswith('/public/home/yuzelu/RuizhiLiang/issue76-granite-ports-20261024/'):
        raise ValueError('own task root only')
    a.out.mkdir(parents=True, exist_ok=False)
    b = json.loads(a.binding.read_text())
    if b['tool_probe_sha256'] != digest(__file__):
        raise ValueError('source binding')
    runtime = '/public/software/singularity-ce-4.3.4/bin/singularity'
    eda = '/public/home/yuzelu/opt/eda'
    container = eda+'/containers/orfs-26Q1-repacked.sif'
    prefix = [runtime, 'exec', '--cleanenv', '--contain', '--bind', eda+':/eda:ro', container]
    commands = [[runtime, '--version'], prefix+['/eda/verilator-5.042/bin/verilator', '--version'],
                prefix+['g++', '--version'], prefix+['python3', '--version'], prefix+['yosys', '-V']]
    results = []
    for i, command in enumerate(commands):
        start = time.monotonic()
        try:
            r = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
            data = r.stdout
            code = r.returncode
        except Exception as exc:
            data = (type(exc).__name__+': '+str(exc)).encode()
            code = -1
        name = 'command%d.log' % i
        (a.out/name).write_bytes(data)
        results.append({'command': command, 'exit_code': code, 'log': name,
                        'sha256': hashlib.sha256(data).hexdigest(), 'elapsed': time.monotonic()-start})
    files = []
    for path in (runtime, container, eda+'/verilator-5.042/bin/verilator_bin'):
        q = Path(path)
        files.append({'path': path, 'exists': q.is_file(), 'bytes': q.stat().st_size if q.is_file() else None,
                      'sha256': digest(q) if q.is_file() else None})
    report = {'schema': 'issue76-tool-probe-v1', 'source': b, 'commands': results, 'files': files,
              'python_host': platform.python_version(),
              'status': 'PASS_EXISTING_TOOL_PROBE' if all(x['exit_code'] == 0 for x in results[:4]) else 'BLOCKED_EXISTING_TOOL',
              'limits': ['Read-only tool probe on CPU Slurm, not a model experiment or RTL/math qualification.',
                         'No installation; existing shared tools mounted read-only.']}
    (a.out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(report['status'], flush=True)


if __name__ == '__main__':
    main()
