"""Make explicit zero-R parent connections for the declared timing stimulus.

The harness already assumes ideal unrouted system ports/clock. Their parent
pin-to-hierarchical-pin connections must exist in the shared parasitic network
so the real native input/output/clock wires are retained. This is no physical
clock/control route, and adds exactly zero R and zero C.
"""
import argparse
import json
import os
from pathlib import Path

from timing_native import sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepared', type=Path, required=True)
    p.add_argument('--out', type=Path, default=Path(os.environ.get('TIMING_OUT', '.')) / 'result')
    a = p.parse_args(); a.out.mkdir()
    d = json.loads((a.prepared / 'prepare.json').read_text())
    bind = json.loads(Path(d['binding']).read_text())['endpoints']
    bound = {tuple(t) for ends in bind.values() for t in ends}
    networks = {'clk': dict(direction='input', terminals=[])}
    for inst in d['instances']:
        portfile = Path(d['audits'][inst[0] + '0']['ports'])
        for line in portfile.read_text().splitlines():
            name, direction = line.split(); name = bytes.fromhex(name).decode()
            if name in ('VDD', 'VSS') or (inst, name) in bound: continue
            if name == 'clk': networks['clk']['terminals'].append((inst, name, direction))
            else:
                external = 'ext_' + inst + '_' + name
                external = d.get('external_port_aliases', {}).get(external, external)
                assert d['external'][external] == direction and external not in networks
                networks[external] = dict(direction=direction, terminals=[(inst, name, direction)])
    assert set(networks) == set(d['external']) | {'clk'}
    assert len(networks['clk']['terminals']) == len(d['instances']) == 10
    aliases = {name: i for i, name in enumerate(networks, 1)}
    instaliases = {inst: len(aliases) + i for i, inst in enumerate(d['instances'], 1)}
    f = a.out / 'ideal-parent.spef'
    with f.open('x') as out:
        out.write('''*SPEF "IEEE 1481-1998"
*DESIGN "qwen_timing_harness"
*DATE "2026-11-08"
*VENDOR "explicit ideal timing stimulus"
*PROGRAM "zero RC connectivity adapter"
*VERSION "1"
*DESIGN_FLOW "NAME_SCOPE LOCAL" "PIN_CAP NONE"
*DIVIDER /
*DELIMITER :
*BUS_DELIMITER []
*T_UNIT 1 NS
*C_UNIT 1 PF
*R_UNIT 1 OHM
*L_UNIT 1 HENRY
*NAME_MAP
''')
        for name, i in {**aliases, **instaliases}.items():
            # These harness bit names are literal escaped scalar identifiers,
            # unlike the real vector pins on native instances.
            escaped = name.replace('[', '\\[').replace(']', '\\]')
            out.write(f'*{i} {escaped}\n')
        for name, row in networks.items():
            alias = '*' + str(aliases[name]); direction = 'I' if row['direction'] == 'input' else 'O'
            out.write(f'*D_NET {alias} 0\n*CONN\n*P {name} {direction}\n')
            for inst, pin, direct in row['terminals']:
                out.write(f'*I *{instaliases[inst]}:{pin} {"I" if direct == "input" else "O"}\n')
            out.write(f'*CAP\n1 {alias} 0\n*RES\n')
            for i, (inst, pin, _) in enumerate(row['terminals'], 1): out.write(f'{i} {alias} *{instaliases[inst]}:{pin} 0\n')
            out.write('*END\n\n')
    result = dict(prepared=str(a.prepared), prepared_sha256=sha(a.prepared / 'prepare.json'),
                  path=str(f.resolve()), sha256=sha(f), networks=len(networks),
                  parent_clock_receivers=10, added_resistance_ohm=0, added_capacitance_ff=0,
                  scope='Exact implementation of the predeclared ideal parent-clock/system-port timing stimulus. Not a physical routed network.')
    (a.out / 'ideal-parent.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__': main()
