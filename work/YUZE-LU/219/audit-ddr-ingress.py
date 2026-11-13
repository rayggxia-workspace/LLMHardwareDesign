"""Account for physical inbound data ports and sealed dynamic Gather sources."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re


def read(path):
    return json.loads(path.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('base', 'contract', 'request', 'out'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    base = read(args.base)
    contract = read(args.contract)
    groups = {item['id']: item for item in base['assemblies']}
    routes = Counter((e['source'], e['sink'], e['kind']) for e in contract['edges']
                     if 'dma' in (e['source'], e['sink']))
    stage = {}
    expected = {
        'C0': ('rx_valid', 'rx_data', 'rx_addr', 'rx_ready', 'rx_stored', 'rx_reserved'),
        'U0': ('incoming_valid', 'incoming_data', 'incoming_addr', 'incoming_ready', 'incoming_ack',
               'link_rx_reserved'),
    }
    for group, ports in expected.items():
        view = base['views'][groups[group]['views']['netlist']]
        path = Path(view['path'])
        raw = path.read_bytes()
        assert sha256(raw).hexdigest() == view['sha256'], group
        head = raw.split(b');', 1)[0].decode()
        names = set(re.findall(r'[A-Za-z_][A-Za-z0-9_]*', head))
        assert set(ports) <= names, (group, set(ports) - names)
        declared = sorted(name for name in names if re.search(r'(dma|ddr|indexed|gather)', name, re.I))
        direct = sorted(f'{src}->{dst}:{kind}={count}' for (src, dst, kind), count in routes.items()
                        if group in (src, dst))
        stage[group] = {'port_contract': list(ports), 'netlist_sha256': view['sha256'],
                        'named_direct_memory_ports': declared, 'bound_dma_edges': direct}
    seal = args.request / 'proof.sha256'
    proof = {path: digest for digest, path in (line.split() for line in seal.read_text().splitlines())}
    table = (args.request / 'input-index.tsv').read_bytes()
    assert sha256(table).hexdigest() == proof['input-index.tsv']
    rows = [line.split() for line in table.decode().splitlines()]
    count, = rows.pop(0)
    assert len(rows) == int(count)
    modes = Counter()
    for step, page, position, source, address, dst, offset in rows:
        step, position, address, dst, offset = (int(v, 16) for v in (step, position, address, dst, offset))
        if source == '1':
            assert step == 0 and address % 64 == 0 and offset < 64 and offset % 4 == 0
            modes['prompt_ddr'] += 1
        elif source == '2':
            assert step > 0 and address == 0 and offset == 8
            modes['previous_retired_token'] += 1
        else:
            raise ValueError('unknown sealed index source')
        assert 0 <= dst <= 1020
    report = {'scope': 'source-bound static data ingress inventory', 'groups': stage,
              'required_index_origins': dict(modes), 'ddr_bound_groups': sorted(
                  {group for src, dst, _ in routes for group in (src, dst) if group != 'dma'}),
              'input_index_sha256': proof['input-index.tsv']}
    args.out.write_text(json.dumps(report, sort_keys=True, indent=2)+'\n')
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
