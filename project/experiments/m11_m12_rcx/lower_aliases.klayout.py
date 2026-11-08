"""Recover original SPEF fragments for previously excluded physical aliases.

Only probe names skipped by an existing probe; never re-export geometry or
repeat field extraction. This prevents dropping child SPEF port fragments.
"""
import gzip
import hashlib
import json
import os
from pathlib import Path
import pya


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    config = json.loads(Path(os.environ['LOWER_CONFIG']).read_text())
    case = config['cases'][int(os.environ['LOWER_INDEX'])]
    prior = Path(case['completed_probe'])
    proof = json.loads((prior / 'probe.json').read_text())
    assert proof['inventory_kind'] == case['label']
    inventory = Path(case['inventory'])
    imeta = json.loads((inventory / 'inventory.json').read_text())
    assert sha(inventory / 'net-inventory.jsonl.gz') == imeta['inventory_sha256']
    excluded = json.loads((prior / 'excluded.json').read_text())
    wanted = {r['name']: r for r in excluded}
    assert len(wanted) == len(excluded)
    manifest = Path(proof['source_topology'])
    assert sha(manifest) == proof['source_topology_sha256']
    topology = json.loads(manifest.read_text())
    database = manifest.with_name('native.l2n')
    assert sha(database) == topology['database_sha256']
    l2n = pya.LayoutToNetlist()
    l2n.read(str(database))
    aliases = []
    with gzip.open(inventory / 'net-inventory.jsonl.gz', 'rt') as f:
        for line in f:
            row = json.loads(line)
            if row['name'] not in wanted:
                continue
            t = case['transform']
            point = [t['offset_um'][d] + sum(t['matrix'][d][k] * row['probe'][k] for k in range(2)) for d in range(2)]
            hierarchy = []
            net = l2n.probe_net(l2n.layer_by_name(row['probe_layer']), pya.DPoint(*point), hierarchy)
            assert net is not None, (row['name'], point)
            path = [(s.circuit_ref().name, str(s.trans)) for s in hierarchy]
            row['relative_instance_path'] = case['instance_path']
            aliases.append(dict(physical_token=(net.circuit().name, int(net.cluster_id), path),
                                alias=row, exclusion=wanted[row['name']]))
    assert len(aliases) == len(wanted)
    out = Path(os.environ['LOWER_OUT'])
    out.mkdir()
    (out / 'aliases.json').write_text(json.dumps(aliases, indent=2) + '\n')
    result = dict(kind=case['root_kind'], inventory_kind=case['label'],
                  prior_probe=str(prior), prior_probe_sha256=sha(prior / 'probe.json'),
                  excluded_sha256=sha(prior / 'excluded.json'), aliases=len(aliases),
                  aliases_sha256=sha(out / 'aliases.json'),
                  scope='Name identity and original SPEF fragments only; no geometry export or field solve.')
    (out / 'aliases-report.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)


main()
