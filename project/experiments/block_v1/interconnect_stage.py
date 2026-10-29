"""Write immutable finite-link manifests; submit only with the shared dispatcher."""
import argparse
import json
from pathlib import Path, PurePosixPath

BASE = PurePosixPath('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121')


def generate(destination, run_id, probe_only=False, profiles=False):
    run = BASE / run_id
    source = run / 'src'
    tasks = []

    def task(name, report, after=(), memory=16):
        tasks.append(dict(id=name, mode=name, cpus=16, memory_gib=memory,
                          memory_basis='Native measured S STA4.523GiB and T1.973GiB;16GiB forecast per combined process includes Python graph audit and conservative headroom. Live RSS plus1.2 reserve and16GiB node guard remain mandatory.',
                          source=str(source), cwd=str(run / 'tasks' / name), report=report,
                          after=list(after)))
    task('interconnect-probe', 'interconnect-probe.json', memory=4)
    if not probe_only:
        for pair in ('mt', 'ts'):
            task('interconnect-prepare-' + pair, 'interconnect-prepare.json', ['interconnect-probe'])
            if not profiles:
                task('interconnect-case-'+pair+'-direct-568-base','interconnect-result.json',
                     ['interconnect-prepare-'+pair])
        for topology in (() if profiles else ('direct', 'endpoints', 'relay')):
            for length in (250, 568, 1200):
                for variant in ('base', 'high'):
                    if (topology,length,variant)==('direct',568,'base'):continue
                    for pair in ('mt','ts'):
                        task(f'interconnect-case-{pair}-{topology}-{length}-{variant}',
                             'interconnect-result.json', ['interconnect-case-'+pair+'-direct-568-base'])
        if profiles:
            for topology in ('direct','endpoints','relay'):
                for variant in ('high','section'):
                    for pair in ('mt','ts'):
                        dependencies=['interconnect-prepare-'+pair] if topology=='direct' and variant=='high' else ['interconnect-profile-'+pair+'-direct-high']
                        task(f'interconnect-profile-{pair}-{topology}-{variant}',
                             'interconnect-result.json',dependencies)
    queue = dict(schema='block-v1-node-queue/1', node_cpus=96, default_task_cpus=16,
                 memory_guard_gib=16, state_path=str(run / 'node-queue-state.json'), tasks=tasks)
    manifest = dict(run_id=run_id, base_nodes=6, max_nodes=8, elastic=True,
                    tasks=[dict(id='native-node-queue', partition='c96', cpus=96,
                                memory='0', minutes=0,
                                argv=['bash', str(source / 'project/experiments/block_v1/worker.sh'),
                                      str(source), 'native-node-queue'])])
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'node-queue.json').write_text(json.dumps(queue, indent=2) + '\n')
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--probe-only', action='store_true')
    parser.add_argument('--profiles', action='store_true')
    args = parser.parse_args()
    generate(args.destination, args.run_id, args.probe_only,args.profiles)
