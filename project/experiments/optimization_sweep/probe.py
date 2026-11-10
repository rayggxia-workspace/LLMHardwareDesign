"""Reuse the independent payload oracle against the actual generated pool header."""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys

from generate import load, once, sha


def execute(cmd, log, env=None):
    with log.open('wb') as output:
        subprocess.run(list(map(str, cmd)), stdout=output, stderr=subprocess.STDOUT,
                       check=True, env=env)


def main():
    p = argparse.ArgumentParser()
    for name in ('repo', 'model', 'out'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args(); a.out.mkdir(exist_ok=False)
    frozen = a.repo/'project/experiments/shared_pool_study'
    sys.path.insert(0, str(frozen))
    old = load(frozen/'numeric_check.py', 'sweep_old_numeric')
    reference = load(frozen/'numeric_reference.py', 'sweep_reference')
    width_source = a.repo/'project/experiments/shared_width_study/check_probe.py'
    source = old.PROBE
    source = once(source, '#include "shared_pool.hpp"', '#include "optimization.hpp"\n#include "shared_pool.hpp"')
    source = once(source, 'e.bytes&&e.bytes<=32&&e.bytes%4==0',
                  'e.bytes&&e.bytes<=optimization::a_bytes&&e.bytes%4==0')
    source = once(source, 'require(argc==4,"probe arguments");',
                  'require(argc==4,"probe arguments");require(optimization::configure(),"case config");')
    (a.out/'probe.cpp').write_bytes(source.encode())
    prefix = Path('/public/home/yuzelu/opt/systemc-3.0.2-issue219')
    cmd = ['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',a.out/'probe.cpp',
           '-I'+str(a.model),'-I'+str(prefix/'include'),'-L'+str(prefix/'lib'),
           '-Wl,-rpath,'+str(prefix/'lib'),'-lsystemc','-o',a.out/'probe']
    execute(cmd, a.out/'build.log')
    values = reference.cases(); reference.write_input(a.out/'input.txt', values)
    report = dict(passed=False, scope='synthetic payload and actual pool events; no full-model numerical proof',
                  model_header_sha256=sha(a.model/'shared_pool.hpp'), cases=[],
                  source_sha256={str(x.relative_to(a.repo)):sha(x) for x in
                                 (frozen/'numeric_check.py', frozen/'numeric_reference.py', width_source)})
    for name,width in (('base',32),('feed2',64)):
        # Only the explicitly changed local suffix width differs from the
        # existing independent address/credit/physical-service audit.
        audit_source = once(width_source.read_text(encoding='utf8'),
                            'local_cycles = ((t[\'count\'] - shared_k) * 4 + 31) // 32',
                            f'local_cycles = ((t[\'count\'] - shared_k) * 4 + {width-1}) // {width}')
        audit_path = a.out/('audit-'+name+'.py'); audit_path.write_bytes(audit_source.encode())
        audit = load(audit_path, 'sweep_events_'+name)
        events_path, result_path = a.out/(name+'-events.jsonl'), a.out/(name+'-actual.json')
        execute([a.out/'probe',a.out/'input.txt',events_path,result_path], a.out/(name+'.log'),
                env=dict(os.environ,OPTIMIZATION_CASE=name))
        actual = json.loads(result_path.read_bytes())
        comparisons = reference.compare(actual['cases'], values)
        if comparisons != 725 or len(actual['negative_controls']) != 10:
            raise AssertionError('lost numeric/negative controls')
        events = [json.loads(line) for line in events_path.open()]
        checked = audit.audit_events(events, values, width, 1, 'single', True, False)
        negative = []
        for field in ('source','epoch','bytes'):
            bad = deepcopy(events)
            e = next(e for e in bad if e['kind']=='consume'); e[field] += 1
            try:
                audit.audit_events(bad, values, width, 1, 'single', True, False)
            except AssertionError:
                negative.append(field)
            else:
                raise AssertionError('event tamper escaped '+field)
        report['cases'].append(dict(name=name,width=width,outputs= comparisons,events=checked,
                                   lifecycle_negative=actual['negative_controls'],event_negative=negative,
                                   derived_audit_sha256=sha(audit_path)))
    report['passed']=True
    report['output_sha256']={p.name:sha(p) for p in a.out.iterdir() if p.is_file()}
    (a.out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':
    main()
