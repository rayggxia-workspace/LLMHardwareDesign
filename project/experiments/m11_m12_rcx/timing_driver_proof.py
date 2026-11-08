"""Prove which real leaf driver carries each macro-to-macro timing net.

Hierarchical interface pins are not timing graph vertices in OpenDB. The
verified exclusive leaf output is the proper vertex for propagated slack.
"""
import argparse
import json
import os
from pathlib import Path
import re

from timing_native import sha
from timing_prepare import records

DRIVERS = Path('/public/home/yuzelu/PingyangHuang/issue-222-analyze-wowCTbae/job-100177/result/drivers.json')


def clean(name): return re.sub(r'\\(.)', r'\1', name)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepared', type=Path, required=True)
    p.add_argument('--out', type=Path, default=Path(os.environ.get('TIMING_OUT', '.')) / 'result')
    a = p.parse_args(); a.out.mkdir()
    prep = json.loads((a.prepared / 'prepare.json').read_text())
    drivers = {r['net']: r for r in json.loads(DRIVERS.read_text())}; assert len(drivers) == 2491
    expected = {}
    for net, d in drivers.items(): expected.setdefault(d['macro_instance'][0] + '0', {}).setdefault(d['macro_output'], []).append(net)
    domains = {}; failures = []
    for kind, ports in expected.items():
        source = Path(prep['audits'][kind]['native']).with_suffix('.spef')
        found = set()
        for aliases, header, alias, rows in records(source):
            terms = []; outputs = []; section = None
            for line in rows:
                w = line.split()
                if not w: continue
                if w[0] in ('*CONN', '*CAP', '*RES', '*END'): section = w[0]
                if section != '*CONN': continue
                if w[0] == '*P' and w[2] == 'O': outputs.append(clean(aliases.get(w[1], w[1])))
                elif w[0] == '*I':
                    inst, pin = w[1].rsplit(':', 1)
                    terms.append(dict(instance=aliases.get(inst, inst), pin=pin, direction=w[2], master=w[w.index('*D') + 1]))
            wanted = [name for name in outputs if name in ports]
            if not wanted: continue
            for name in wanted:
                assert name not in found; found.add(name)
                drive = [t for t in terms if t['direction'] == 'O']
                timed_sinks = [t for t in terms if t['direction'] == 'I' and t['master'] != 'ANTENNA_X1']
                exclusive = len(drive) == 1 and len(outputs) == 1 and not timed_sinks
                for net in ports[name]:
                    d = drivers[net]
                    assert len(drive) == 1
                    assert all(drive[0][k] == d[k] for k in ('master', 'pin', 'instance')), (net, d, drive)
                    row = dict(net=net, macro_instance=d['macro_instance'], macro_output=name,
                               leaf_driver=d['macro_instance'] + '/' + d['instance'] + '/' + d['pin'],
                               exclusive_to_top_word=exclusive, source_native_spef=str(source),
                               output_ports=outputs, internal_timed_sinks=timed_sinks)
                    domains[net] = row
                    if not exclusive: failures.append(row)
        assert found == set(ports), (kind, sorted(set(ports) - found))
    assert len(domains) == 2491
    result = dict(nets=2491, exclusive_boundary_drivers=sum(r['exclusive_to_top_word'] for r in domains.values()),
                  nonexclusive=failures, drivers_json=str(DRIVERS), drivers_sha256=sha(DRIVERS),
                  prepared=str(a.prepared), prepared_sha256=sha(a.prepared / 'prepare.json'), rows=domains)
    (a.out / 'driver-proof.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('rows', 'nonexclusive')}), flush=True)


if __name__ == '__main__': main()
